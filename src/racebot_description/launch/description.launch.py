from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import Command, PathJoinSubstitution


def generate_launch_description():
    robot_description = Command([
        'xacro ',
        PathJoinSubstitution([
            FindPackageShare('racebot_description'),
            'urdf', 'racebot.xacro'
        ])
    ])

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True
        }],
        output='screen'
    )

    return LaunchDescription([robot_state_publisher])
