cmake_minimum_required(VERSION 3.8)
project(racebot_control)

find_package(ament_cmake REQUIRED)

install(PROGRAMS
  script/keyboard_teleop.py
  script/servo_commands.py
  script/transform.py
  script/gazebo_odometry.py
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
