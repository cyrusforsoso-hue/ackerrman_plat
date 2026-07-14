#!/usr/bin/env python3
"""
Compare actual vs target steering angle and speed, output comparison curves.

Subscribes:
  /target_speed         (Float64)          →  target longitudinal speed v
  /target_speed_vdelta  (Float64MultiArray) →  [v, delta]
  /odom                 (Odometry)         →  actual speed (body-frame)
  /joint_states         (JointState)       →  actual steering joint position

Ctrl+C ends recording and generates two matplotlib subplots:
  top:    steering angle — actual vs target
  bottom: speed — actual vs target
"""
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64, Float64MultiArray

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt


def compute_body_speed(msg: Odometry) -> float:
    """Extract body-frame longitudinal speed from odometry.

    gazebo_odometry writes body-frame forward speed directly into
    twist.twist.linear.x (child_frame_id = base_footprint), so no
    projection is needed.
    """
    return msg.twist.twist.linear.x


class ComparisonNode(Node):
    def __init__(self):
        super().__init__('compare_steering')

        self.t_target_speed = []
        self.v_target = []
        self.t_target_delta = []
        self.d_target = []
        self.t_actual_speed = []
        self.v_actual = []
        self.t_actual_delta = []
        self.d_actual = []

        self.create_subscription(Float64, '/target_speed', self.speed_cb, 1)
        self.create_subscription(Float64MultiArray, '/target_speed_vdelta',
                                 self.vdelta_cb, 1)
        self.create_subscription(Odometry, '/odom', self.odom_cb, 1)
        self.create_subscription(JointState, '/joint_states', self.joint_cb, 1)

        self.get_logger().info(
            'compare_steering ready — recording data. Press Ctrl+C to plot.'
        )

    # --- callbacks ---

    def speed_cb(self, msg: Float64):
        self.t_target_speed.append(self.get_clock().now().nanoseconds * 1e-9)
        self.v_target.append(abs(msg.data))

    def vdelta_cb(self, msg: Float64MultiArray):
        if len(msg.data) < 2:
            return
        self.t_target_delta.append(self.get_clock().now().nanoseconds * 1e-9)
        self.d_target.append(msg.data[1])

    def odom_cb(self, msg: Odometry):
        self.t_actual_speed.append(self.get_clock().now().nanoseconds * 1e-9)
        self.v_actual.append(abs(compute_body_speed(msg)))

    def joint_cb(self, msg: JointState):
        try:
            idx = msg.name.index('left_steering_hinge_joint')
        except ValueError:
            return
        self.t_actual_delta.append(self.get_clock().now().nanoseconds * 1e-9)
        self.d_actual.append(msg.position[idx])

    # --- shutdown ---

    def destroy_node(self):
        self._plot()
        super().destroy_node()

    def _plot(self):
        if not any([self.t_target_speed, self.t_target_delta,
                    self.t_actual_speed, self.t_actual_delta]):
            self.get_logger().warn('No data recorded — nothing to plot.')
            return

        # Normalise timestamps so 0 = first recorded point
        all_t = []
        for series in [self.t_target_speed, self.t_target_delta,
                       self.t_actual_speed, self.t_actual_delta]:
            if series:
                all_t.append(series[0])
        t0 = min(all_t) if all_t else 0.0

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

        # --- top: steering angle ---
        if self.t_target_delta and self.t_actual_delta:
            ax1.plot([t - t0 for t in self.t_target_delta], self.d_target,
                     'r-', linewidth=1.2, label='target delta')
            ax1.plot([t - t0 for t in self.t_actual_delta], self.d_actual,
                     'b--', linewidth=1.2, label='actual steering (left_hinge)')
        elif self.t_target_delta:
            ax1.plot([t - t0 for t in self.t_target_delta], self.d_target,
                     'r-', linewidth=1.2, label='target delta')
        elif self.t_actual_delta:
            ax1.plot([t - t0 for t in self.t_actual_delta], self.d_actual,
                     'b--', linewidth=1.2, label='actual steering (left_hinge)')

        ax1.set_ylabel('Steering Angle [rad]')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # --- bottom: speed ---
        if self.t_target_speed and self.t_actual_speed:
            ax2.plot([t - t0 for t in self.t_target_speed], self.v_target,
                     'r-', linewidth=1.2, label='target speed')
            ax2.plot([t - t0 for t in self.t_actual_speed], self.v_actual,
                     'b--', linewidth=1.2, label='actual speed (odom)')
        elif self.t_target_speed:
            ax2.plot([t - t0 for t in self.t_target_speed], self.v_target,
                     'r-', linewidth=1.2, label='target speed')
        elif self.t_actual_speed:
            ax2.plot([t - t0 for t in self.t_actual_speed], self.v_actual,
                     'b--', linewidth=1.2, label='actual speed (odom)')

        ax2.set_xlabel('Time [s]')
        ax2.set_ylabel('Speed [m/s]')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        fig.suptitle('Pure Pursuit: Target vs Actual')
        plt.tight_layout()
        plt.show()


def main():
    rclpy.init()
    node = ComparisonNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
