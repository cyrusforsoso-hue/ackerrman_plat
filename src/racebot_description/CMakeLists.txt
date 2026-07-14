cmake_minimum_required(VERSION 3.8)
project(racebot_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf config launch meshes scripts
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
