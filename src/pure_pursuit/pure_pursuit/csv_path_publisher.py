"""CSV waypoint publisher: reads CSV -> publishes nav_msgs/Path (latched)."""

import csv
import os
import sys

from ament_index_python.packages import get_package_share_directory
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped


class CSVPathPublisher(Node):
    """Read a CSV file of waypoints and publish as nav_msgs/Path (latched)."""

    def __init__(self):
        super().__init__('csv_path_publisher')

        pkg_share = get_package_share_directory('pure_pursuit')
        default_csv = os.path.join(pkg_share, 'data', 'path.csv')
        self.declare_parameter('csv_path', default_csv)
        csv_path = self.get_parameter('csv_path').get_parameter_value().string_value

        if not csv_path:
            self.get_logger().error('csv_path parameter is empty. Cannot publish path.')
            return

        # Latched QoS: reliable + transient_local
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=1,
        )
        self.pub = self.create_publisher(Path, '/global/reference_path', qos)

        path_msg = self._load_csv(csv_path)
        if path_msg is not None:
            self.pub.publish(path_msg)
            self.get_logger().info(
                f'Published {len(path_msg.poses)} waypoints from {csv_path}'
            )
        else:
            self.get_logger().error(f'Failed to load CSV: {csv_path}')

    def _load_csv(self, csv_path: str):
        """Parse CSV file into nav_msgs/Path message."""
        if not os.path.exists(csv_path):
            self.get_logger().error(f'CSV file not found: {csv_path}')
            return None

        path = Path()
        path.header.frame_id = 'map'
        path.header.stamp = self.get_clock().now().to_msg()

        try:
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row or row[0].startswith('#'):
                        continue
                    if len(row) < 7:
                        self.get_logger().warn(f'Skipping short row: {row}')
                        continue

                    x, y, z = float(row[0]), float(row[1]), float(row[2])
                    qx, qy, qz, qw = (
                        float(row[3]), float(row[4]), float(row[5]), float(row[6])
                    )

                    pose = PoseStamped()
                    pose.header = path.header
                    pose.pose.position.x = x
                    pose.pose.position.y = y
                    pose.pose.position.z = z
                    pose.pose.orientation.x = qx
                    pose.pose.orientation.y = qy
                    pose.pose.orientation.z = qz
                    pose.pose.orientation.w = qw

                    path.poses.append(pose)

        except Exception as e:
            self.get_logger().error(f'Error reading CSV: {e}')
            return None

        return path


def main(args=None):
    rclpy.init(args=args)
    node = CSVPathPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
