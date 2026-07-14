#!/usr/bin/env python3
"""
servo_commands: /ackermann_cmd → ros2_control command topics
  Converts speed (m/s) to wheel velocity (rad/s) via ×31.25
  Passes steering angle through directly
"""
import rclpy
from rclpy.node import Node
from ackermann_msgs.msg import AckermannDriveStamped
from std_msgs.msg import Float64MultiArray


class ServoCommands(Node):
    def __init__(self):
        super().__init__('servo_commands')
        self.wheel_pub = self.create_publisher(
            Float64MultiArray, '/wheel_velocity_controller/commands', 1)
        self.steer_pub = self.create_publisher(
            Float64MultiArray, '/steering_position_controller/commands', 1)
        self.sub = self.create_subscription(
            AckermannDriveStamped, '/ackermann_cmd', self.callback, 1)
        self.get_logger().info('servo_commands ready (×31.25 conversion)')

    def callback(self, msg):
        wheel_vel = msg.drive.speed * 31.25
        steer_pos = msg.drive.steering_angle

        wheel_cmd = Float64MultiArray()
        wheel_cmd.data = [wheel_vel, wheel_vel, wheel_vel, wheel_vel]
        self.wheel_pub.publish(wheel_cmd)

        steer_cmd = Float64MultiArray()
        steer_cmd.data = [steer_pos, steer_pos]
        self.steer_pub.publish(steer_cmd)


def main():
    rclpy.init()
    node = ServoCommands()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
