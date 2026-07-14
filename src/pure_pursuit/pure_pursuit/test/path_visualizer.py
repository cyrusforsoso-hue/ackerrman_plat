#!/usr/bin/env python3
"""
path_visualizer: subscribes to /global/reference_path (Path)
  publishes Marker LINE_STRIP for RViz/Gazebo visualization.
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from nav_msgs.msg import Path
from visualization_msgs.msg import Marker


class PathVisualizer(Node):
    def __init__(self):
        super().__init__('path_visualizer')

        latched_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=1,
        )
        self.path_sub = self.create_subscription(
            Path, '/global/reference_path', self.path_cb, latched_qos)
        self.marker_pub = self.create_publisher(Marker, '/reference_path_marker', 10)

        self.get_logger().info('path_visualizer ready')

    def path_cb(self, msg):
        marker = Marker()
        marker.header = msg.header
        marker.ns = 'reference_path'
        marker.id = 0
        marker.type = Marker.LINE_STRIP
        marker.action = Marker.ADD
        marker.scale.x = 0.05   # line width
        marker.color.r = 0.0
        marker.color.g = 1.0
        marker.color.b = 0.0
        marker.color.a = 0.8
        marker.pose.orientation.w = 1.0

        for ps in msg.poses:
            marker.points.append(ps.pose.position)

        self.marker_pub.publish(marker)
        self.get_logger().info(f'Path visualized: {len(marker.points)} points')


def main():
    rclpy.init()
    node = PathVisualizer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
