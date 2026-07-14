"""Setup for pure_pursuit package."""
import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'pure_pursuit'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'data'), glob('data/*.csv') + glob('data/*.sdf')),
    ],
    install_requires=['setuptools'],
    zip_safe=False,
    maintainer='baja',
    maintainer_email='baja@todo.todo',
    description='Standard Pure Pursuit controller for Ackermann vehicles',
    license='BSD 3-Clause License',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'csv_path_publisher = pure_pursuit.csv_path_publisher:main',
            'pure_pursuit_node = pure_pursuit.node:main',
            'ackermann_bridge = pure_pursuit.test.ackermann_bridge:main',
            'steering_bridge = pure_pursuit.test.steering_bridge:main',
            'odom_relay = pure_pursuit.test.odom_relay:main',
            'path_visualizer = pure_pursuit.test.path_visualizer:main',
            'w_to_delta = pure_pursuit.test.w_to_delta:main',
            'cmdvel2gazebo = pure_pursuit.test.cmdvel2gazebo:main',
            'bridge_node = pure_pursuit.test.bridge_node:main',
            'gazebo_path_visualizer = pure_pursuit.test.gazebo_path_visualizer:main',
            'compare_steering = pure_pursuit.test.compare_steering:main',
        ],
    },
)
