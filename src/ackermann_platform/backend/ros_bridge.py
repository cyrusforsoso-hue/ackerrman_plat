"""ROS2 bridge: subscribes to /odom and /global/reference_path, publishes /ackermann_cmd."""
import math
import threading
import time
from typing import List, Optional, Tuple

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from ackermann_msgs.msg import AckermannDriveStamped
from nav_msgs.msg import Odometry, Path


class _BridgeNode(Node):
    """Internal ROS2 node that runs in a background thread."""

    def __init__(self):
        super().__init__('platform_ros_bridge')

        # State with thread safety
        self._lock = threading.Lock()
        self._pose: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._speed: float = 0.0
        self._path: List[Tuple[float, float, float]] = []
        self._odom_received: bool = False

        # QoS
        best_effort = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            depth=1,
        )
        reliable_transient = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=1,
        )

        self._odom_sub = self.create_subscription(
            Odometry, '/odom', self._odom_cb, best_effort,
        )
        self._path_sub = self.create_subscription(
            Path, '/global/reference_path', self._path_cb, reliable_transient,
        )

        # Ackermann publisher
        self._ack_pub = self.create_publisher(AckermannDriveStamped, '/ackermann_cmd', 1)

        # Optional: topic bridge subscription (Mode A)
        self._bridge_sub = None

        self.get_logger().info('Platform ROS bridge started')

    def _odom_cb(self, msg: Odometry):
        q = msg.pose.pose.orientation
        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        )
        v_east = msg.twist.twist.linear.x
        v_north = msg.twist.twist.linear.y
        v = v_east * math.cos(yaw) + v_north * math.sin(yaw)

        with self._lock:
            self._pose = (msg.pose.pose.position.x, msg.pose.pose.position.y, yaw)
            self._speed = v
            self._odom_received = True

    def _path_cb(self, msg: Path):
        waypoints = []
        for ps in msg.poses:
            q = ps.pose.orientation
            yaw = math.atan2(
                2.0 * (q.w * q.z + q.x * q.y),
                1.0 - 2.0 * (q.y * q.y + q.z * q.z)
            )
            waypoints.append((ps.pose.position.x, ps.pose.position.y, yaw))

        with self._lock:
            self._path = waypoints

    def _bridge_cb(self, msg: AckermannDriveStamped):
        """Mode A: forward external topic's AckermannDriveStamped to /ackermann_cmd."""
        self._ack_pub.publish(msg)

    def get_state(self) -> dict:
        """Thread-safe state snapshot for the web layer."""
        with self._lock:
            return {
                'pose': self._pose,
                'speed': self._speed,
                'path': self._path[:],
                'connected': self._odom_received,
            }

    def publish_ackermann(self, speed: float, steering_angle: float):
        """Publish control command (Mode B — Python script output)."""
        msg = AckermannDriveStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        msg.drive.speed = float(speed)
        msg.drive.steering_angle = float(steering_angle)
        self._ack_pub.publish(msg)

    def set_topic_bridge(self, topic_name: Optional[str]):
        """Set up Mode A: subscribe to an external AckermannDriveStamped topic."""
        if self._bridge_sub is not None:
            self.destroy_subscription(self._bridge_sub)
            self._bridge_sub = None

        if topic_name:
            self._bridge_sub = self.create_subscription(
                AckermannDriveStamped, topic_name, self._bridge_cb, 1,
            )
            self.get_logger().info(f'Bridge subscribed to {topic_name}')
        else:
            self.get_logger().info('Topic bridge disabled')


class ROS2Bridge:
    """Manages the ROS2 node lifecycle in a background thread."""

    def __init__(self):
        self._node: Optional[_BridgeNode] = None
        self._thread: Optional[threading.Thread] = None
        self._executor: Optional[rclpy.executors.SingleThreadedExecutor] = None
        self._running = False

    def start(self):
        """Start ROS2 in background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        # Wait for node to initialize
        for _ in range(50):
            if self._node is not None:
                return
            time.sleep(0.1)
        raise RuntimeError('ROS2 bridge failed to start within 5 seconds')

    def _spin(self):
        rclpy.init()
        self._node = _BridgeNode()
        self._executor = rclpy.executors.SingleThreadedExecutor()
        self._executor.add_node(self._node)
        try:
            while self._running and rclpy.ok():
                self._executor.spin_once(timeout_sec=0.1)
        finally:
            self._executor.remove_node(self._node)
            self._node.destroy_node()
            rclpy.shutdown()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)

    def get_state(self) -> dict:
        if self._node is None:
            return {'pose': (0, 0, 0), 'speed': 0, 'path': [], 'connected': False}
        return self._node.get_state()

    def publish_ackermann(self, speed: float, steering_angle: float):
        if self._node:
            self._node.publish_ackermann(speed, steering_angle)

    def set_topic_bridge(self, topic_name: Optional[str]):
        if self._node:
            self._node.set_topic_bridge(topic_name)
