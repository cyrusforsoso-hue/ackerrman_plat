#!/usr/bin/env python3
"""
gazebo_odometry: computes odometry from /joint_states (wheel velocities + steering angle)
  Ackermann model:
    v  = (w_lr + w_rr) / 2 * wheel_radius
    w  = v * tan(steering) / wheelbase
  Publishes /odom and odom->base_footprint TF at 50Hz.
"""
import math
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from geometry_msgs.msg import TransformStamped, Quaternion
import tf2_ros


class OdometryNode(Node):
    def __init__(self):
        super().__init__('gazebo_odometry_node')

        self.pub_odom = self.create_publisher(Odometry, '/odom', 1)
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        self.sub = self.create_subscription(
            JointState, '/joint_states', self.js_cb, 1)

        # Robot geometry
        self.wheel_radius = 0.032   # from URDF
        self.wheelbase = 0.26       # front hinge(0.13) to rear wheel(-0.13)

        # State
        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.last_time = self.get_clock().now()

        # Joint indices
        self.lr_idx = None  # left rear wheel velocity
        self.rr_idx = None  # right rear wheel velocity
        self.ls_idx = None  # left steering position

        self.get_logger().info('gazebo_odometry ready (joint_states-based, 50Hz)')

    def js_cb(self, msg):
        # Find indices on first message
        if self.lr_idx is None:
            try:
                self.lr_idx = msg.name.index('left_rear_wheel_joint')
                self.rr_idx = msg.name.index('right_rear_wheel_joint')
                self.ls_idx = msg.name.index('left_steering_hinge_joint')
            except ValueError:
                return

        if self.lr_idx is None:
            return

        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds * 1e-9
        if dt <= 0 or dt > 0.1:
            self.last_time = now
            return
        self.last_time = now

        # Get wheel velocities (rad/s) and steering angle (rad)
        v_lr = msg.velocity[self.lr_idx]   # left rear wheel velocity
        v_rr = msg.velocity[self.rr_idx]   # right rear wheel velocity
        steer = msg.position[self.ls_idx]  # steering angle

        # Ackermann odometry
        # Forward speed from average of rear wheels
        v = (v_lr + v_rr) / 2.0 * self.wheel_radius

        # Angular velocity from steering angle
        w = v * math.tan(steer) / self.wheelbase if abs(self.wheelbase) > 1e-6 else 0.0

        # Integrate pose
        self.x += v * math.cos(self.yaw) * dt
        self.y += v * math.sin(self.yaw) * dt
        self.yaw += w * dt

        # Build odometry message
        odom = Odometry()
        odom.header.stamp = now.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_footprint'
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0
        # yaw to quaternion
        odom.pose.pose.orientation = self._yaw_to_quat(self.yaw)
        odom.twist.twist.linear.x = v
        odom.twist.twist.angular.z = w
        odom.pose.covariance = [
            1e-3, 0.0,  0.0, 0.0, 0.0, 0.0,
            0.0,  1e-3, 0.0, 0.0, 0.0, 0.0,
            0.0,  0.0,  1e6, 0.0, 0.0, 0.0,
            0.0,  0.0,  0.0, 1e6, 0.0, 0.0,
            0.0,  0.0,  0.0, 0.0, 1e6, 0.0,
            0.0,  0.0,  0.0, 0.0, 0.0, 1e3,
        ]
        odom.twist.covariance = [
            1e-9, 0.0,  0.0, 0.0, 0.0, 0.0,
            0.0,  1e-3, 1e-9,0.0, 0.0, 0.0,
            0.0,  0.0,  1e6, 0.0, 0.0, 0.0,
            0.0,  0.0,  0.0, 1e6, 0.0, 0.0,
            0.0,  0.0,  0.0, 0.0, 1e6, 0.0,
            0.0,  0.0,  0.0, 0.0, 0.0, 1e-9,
        ]
        self.pub_odom.publish(odom)

        # Broadcast TF
        tf_msg = TransformStamped()
        tf_msg.header.stamp = now.to_msg()
        tf_msg.header.frame_id = 'odom'
        tf_msg.child_frame_id = 'base_footprint'
        tf_msg.transform.translation.x = self.x
        tf_msg.transform.translation.y = self.y
        tf_msg.transform.translation.z = 0.0
        tf_msg.transform.rotation = self._yaw_to_quat(self.yaw)
        self.tf_broadcaster.sendTransform(tf_msg)

    @staticmethod
    def _yaw_to_quat(yaw):
        q = Quaternion()
        q.z = math.sin(yaw * 0.5)
        q.w = math.cos(yaw * 0.5)
        return q


def main():
    rclpy.init()
    node = OdometryNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
