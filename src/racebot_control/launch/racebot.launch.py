"""
racebot.launch.py -- Main entry point.
Starts: Gazebo -> robot_state_publisher -> spawn robot ->
        spawn controllers -> control scripts

Controller config is embedded in the URDF via <parameters> tag.

Keyboard teleop runs separately:
  source install/setup.bash
  ros2 run racebot_control keyboard_teleop.py
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_share = get_package_share_directory('racebot_description')
    pp_share = get_package_share_directory('pure_pursuit')

    path_csv = os.path.join(pp_share, 'data', 'path.csv')
    path_sdf = '/tmp/path_model.sdf'

    robot_description_content = Command(['xacro ', os.path.join(pkg_share, 'urdf', 'racebot.xacro')])
    robot_description = {
        'robot_description': ParameterValue(robot_description_content, value_type=str)
    }

    # 1. Gazebo with empty world
    gazebo = ExecuteProcess(
        cmd=['gazebo', '--verbose', '-s', 'libgazebo_ros_init.so',
             '-s', 'libgazebo_ros_factory.so'],
        output='screen'
    )

    # 2. Robot State Publisher
    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        parameters=[robot_description, {'use_sim_time': True}],
        output='screen'
    )

    # 3. Spawn robot model
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-entity', 'racebot', '-topic', 'robot_description',
                   '-x', '0', '-y', '0', '-z', '0.05'],
        output='screen'
    )
    spawn_delayed = TimerAction(period=2.0, actions=[spawn_entity])

    # 4. Spawn controllers (after robot is spawned and gazebo_ros2_control initializes)
    spawn_controllers = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', 'wheel_velocity_controller',
                   'steering_position_controller', '-c', '/controller_manager'],
        output='screen'
    )
    controllers_delayed = TimerAction(period=6.0, actions=[spawn_controllers])

    # 5. Control scripts
    servo = Node(package='racebot_control', executable='servo_commands.py',
                 name='servo_commands', output='screen')
    transform_node = Node(package='racebot_control', executable='transform.py',
                          name='transform', output='screen')
    odom = Node(package='racebot_control', executable='gazebo_odometry.py',
                name='gazebo_odometry_node', output='screen')
    bridge = Node(package='pure_pursuit', executable='bridge_node',
                  name='bridge_node', output='screen')

    # 6. Generate path SDF from CSV and spawn in Gazebo
    gen_path_sdf = ExecuteProcess(
        cmd=['python3', os.path.join(pkg_share, 'scripts', 'generate_path_sdf.py'),
             '--input', path_csv, '--output', path_sdf],
        name='generate_path_sdf',
        output='screen'
    )

    spawn_path = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-entity', 'reference_path', '-file', path_sdf,
                   '-x', '0', '-y', '0', '-z', '0'],
        name='spawn_path_model',
        output='screen',
    )
    spawn_path_delayed = TimerAction(period=8.0, actions=[spawn_path])

    return LaunchDescription([
        gazebo, rsp, spawn_delayed, controllers_delayed,
        servo, transform_node, odom, bridge,
        gen_path_sdf, spawn_path_delayed,
    ])
