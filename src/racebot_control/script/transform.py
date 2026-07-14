#!/usr/bin/env python3
"""
transform: cmd_vel (Twist) -> AckermannDriveStamped
  linear.x  -> speed
  angular.z -> steering_angle
"""
import rclpy
from rclpy.node import Node
from ackermann_msgs.msg import AckermannDriveStamped
from geometry_msgs.msg import Twist


class Transform(Node):
    def __init__(self):
        super().__init__('transform')
        self.pub = self.create_publisher(AckermannDriveStamped, '/ackermann_cmd', 1)
        self.sub = self.create_subscription(Twist, '/cmd_vel', self.callback, 1)
        self.get_logger().info('transform ready: /cmd_vel -> /ackermann_cmd')

    def callback(self, msg):
        ack = AckermannDriveStamped()
        ack.header.stamp = self.get_clock().now().to_msg()
        ack.header.frame_id = 'base_link'
        ack.drive.speed = msg.linear.x
        ack.drive.acceleration = 1.0
        ack.drive.jerk = 1.0
        ack.drive.steering_angle = msg.angular.z
        ack.drive.steering_angle_velocity = 1.0
        self.pub.publish(ack)


def main():
    rclpy.init()
    node = Transform()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
