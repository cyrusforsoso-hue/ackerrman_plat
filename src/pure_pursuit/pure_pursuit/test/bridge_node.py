#!/usr/bin/env python3
"""
bridge_node: connects pure_pursuit outputs to Gazebo simulation.
  /target_speed_vdelta [v, δ]  →  /ackermann_cmd (AckermannDriveStamped)
  /odom                         →  /chcn_vehicle_state (Odometry)
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray
from ackermann_msgs.msg import AckermannDriveStamped
from nav_msgs.msg import Odometry


class BridgeNode(Node):
    def __init__(self):
        super().__init__('bridge_node')

        # --- Pure Pursuit → Gazebo: [v, δ] → AckermannDriveStamped ---
        self.ack_pub = self.create_publisher(AckermannDriveStamped, '/ackermann_cmd', 1)
        self.vdelta_sub = self.create_subscription(
            Float64MultiArray, '/target_speed_vdelta', self.vdelta_cb, 1)

        # --- Gazebo → Pure Pursuit: /odom → /chcn_vehicle_state ---
        self.odom_pub = self.create_publisher(Odometry, '/chcn_vehicle_state', 1)
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self.odom_cb, 1)

        self.get_logger().info('bridge_node ready: vdelta→ackermann_cmd, odom→chcn_vehicle_state')

    def vdelta_cb(self, msg):
        if len(msg.data) < 2:
            return
        ack = AckermannDriveStamped()
        ack.header.stamp = self.get_clock().now().to_msg()
        ack.header.frame_id = 'base_link'
        ack.drive.speed = msg.data[0]
        ack.drive.steering_angle = msg.data[1]
        self.ack_pub.publish(ack)

    def odom_cb(self, msg):
        self.odom_pub.publish(msg)


def main():
    rclpy.init()
    node = BridgeNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
