"""Pure Pursuit Planner ROS2 Node — subscribers, planner, publishers."""

import math
from typing import List, Tuple, Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from std_msgs.msg import Float64, Float64MultiArray, ColorRGBA
from nav_msgs.msg import Odometry, Path
from visualization_msgs.msg import Marker

from .pp_planner import PurePursuitPlanner
 

class PurePursuitNode(Node):
    """Standard Pure Pursuit controller node for Ackermann vehicles."""

    def __init__(self):
        super().__init__('pure_pursuit_node')

        self.declare_parameter('wheelbase', 1.5)
        self.declare_parameter('v_base', 5.0)
        self.declare_parameter('R0', 2.0)
        self.declare_parameter('Ld_min', 1.0)
        self.declare_parameter('Ld_max', 5.0)
        self.declare_parameter('accel', 1.0)
        self.declare_parameter('decel', 2.0)
        self.declare_parameter('cur_windows', 8.0)
        self.declare_parameter('odom_timeout', 20)
        self.declare_parameter('hz', 20)

        param_names = [
            'wheelbase', 'v_base', 'R0', 'Ld_min', 'Ld_max',
            'accel', 'decel', 'cur_windows', 'odom_timeout', 'hz',
        ]
        params = {key: self.get_parameter(key).value for key in param_names}

        self.planner = PurePursuitPlanner(params)
        self.hz = params['hz']
        self.odom_timeout = params['odom_timeout']

        # State
        self.reference_path: Optional[Path] = None
        self.path_xyy: List[Tuple[float, float, float]] = []
        self.robot_pose: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.current_body_v: float = 0.0
        self.odom_miss_count: int = 0
        self.goal_reached: bool = False
        self.path_frame_id: str = "map"

        # QoS
        best_effort_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            depth=1,
        )
        reliable_transient_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=1,
        )

        # Subscribers
        self.path_sub = self.create_subscription(
            Path, '/global/reference_path', self.path_callback, reliable_transient_qos
        )
        self.odom_sub = self.create_subscription(
            Odometry, '/chcn_vehicle_state', self.odom_callback, best_effort_qos
        )

        # Publishers
        self.target_speed_pub = self.create_publisher(Float64, '/target_speed', 1)
        self.target_vdelta_pub = self.create_publisher(
            Float64MultiArray, '/target_speed_vdelta', 1
        )
        self.lookahead_marker_pub = self.create_publisher(Marker, '/target_point', 1)

        # Control timer
        self.control_timer = self.create_timer(1.0 / self.hz, self.control_loop)

        self.get_logger().info('Pure Pursuit Node started')

    def path_callback(self, msg: Path):
        self.reference_path = msg
        self.path_frame_id = msg.header.frame_id
        self.path_xyy.clear()

        for pose_stamped in msg.poses:
            q = pose_stamped.pose.orientation
            yaw = math.atan2(
                2.0 * (q.w * q.z + q.x * q.y),
                1.0 - 2.0 * (q.y * q.y + q.z * q.z)
            )
            x = pose_stamped.pose.position.x
            y = pose_stamped.pose.position.y
            self.path_xyy.append((x, y, yaw))

        self.goal_reached = False
        self.get_logger().info(
            f'Reference path received: {len(msg.poses)} waypoints'
        )

    def odom_callback(self, msg: Odometry):
        q = msg.pose.pose.orientation
        yaw = math.atan2(
            2.0 * (q.w * q.z + q.x * q.y),
            1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        )
        v_east = msg.twist.twist.linear.x
        v_north = msg.twist.twist.linear.y
        self.current_body_v = v_east * math.cos(yaw) + v_north * math.sin(yaw)
        px = msg.pose.pose.position.x
        py = msg.pose.pose.position.y
        self.robot_pose = (px, py, yaw)
        self.odom_miss_count = 0

    def control_loop(self):
        if self.reference_path is None or len(self.path_xyy) < 2:
            self.publish_zero_command()
            return

        if self.odom_miss_count > self.odom_timeout:
            self.publish_zero_command()
            return

        if self.goal_reached:
            self.publish_zero_command()
            return

        self.odom_miss_count += 1

        v, delta, (lx, ly) = self.planner.compute(
            self.robot_pose, self.current_body_v, self.path_xyy
        )

        # Publish /target_speed
        self.target_speed_pub.publish(Float64(data=v))

        # Publish /target_speed_vdelta: data[0]=v, data[1]=delta
        self.target_vdelta_pub.publish(Float64MultiArray(data=[v, delta]))

        # Publish /target_point Marker
        stamp = self.get_clock().now().to_msg()
        marker = Marker()
        marker.header.frame_id = self.path_frame_id
        marker.header.stamp = stamp
        marker.ns = "lookahead_point"
        marker.id = 0
        marker.type = Marker.SPHERE
        marker.action = Marker.ADD
        marker.pose.position.x = lx
        marker.pose.position.y = ly
        marker.scale.x = marker.scale.y = marker.scale.z = 0.3
        marker.color = ColorRGBA(r=1.0, g=0.0, b=0.0, a=1.0)
        self.lookahead_marker_pub.publish(marker)

        # Check goal reached
        if v < 0.001 and len(self.path_xyy) > 0:
            gx, gy, _ = self.path_xyy[-1]
            rx, ry, _ = self.robot_pose
            if math.hypot(gx - rx, gy - ry) < 0.15:
                self.goal_reached = True
                self.get_logger().info('Navigation goal reached!')

    def publish_zero_command(self):
        self.target_speed_pub.publish(Float64(data=0.0))
        self.target_vdelta_pub.publish(Float64MultiArray(data=[0.0, 0.0]))


def main(args=None):
    rclpy.init(args=args)
    node = PurePursuitNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
