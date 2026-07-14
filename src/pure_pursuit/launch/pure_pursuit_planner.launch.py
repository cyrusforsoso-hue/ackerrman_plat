import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import TimerAction
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('pure_pursuit')
    params_file = os.path.join(pkg_share, 'config', 'pp_params.yaml')
    path_sdf = os.path.join(pkg_share, 'data', 'path_model.sdf')

    csv_path_publisher = Node(
        package='pure_pursuit',
        executable='csv_path_publisher',
        name='csv_path_publisher',
        output='screen',
        emulate_tty=True,
    )

    pure_pursuit_node = Node(
        package='pure_pursuit',
        executable='pure_pursuit_node',
        name='pure_pursuit_node',
        parameters=[params_file],
        output='screen',
        emulate_tty=True,
    )

    path_visualizer = Node(
        package='pure_pursuit',
        executable='path_visualizer',
        name='path_visualizer',
        output='screen',
    )

    # Spawn reference path model in Gazebo (delayed, waits for /spawn_entity service)
    spawn_path = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-entity', 'reference_path', '-file', path_sdf,
                   '-x', '0', '-y', '0', '-z', '0'],
        name='spawn_path_model',
        output='screen',
    )
    spawn_path_delayed = TimerAction(period=4.0, actions=[spawn_path])

    return LaunchDescription([
        csv_path_publisher,
        pure_pursuit_node,
        path_visualizer,
        spawn_path_delayed,
    ])
