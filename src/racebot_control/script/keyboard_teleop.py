#!/usr/bin/env python3
"""
Keyboard teleop: WASD → /ackermann_cmd
  w: forward  (speed=+1.0)
  s: backward (speed=-1.0)
  a: left     (steer=+0.6)
  d: right    (steer=-0.6)
  any other:  stop
  CTRL-C:     quit
"""
import rclpy
from rclpy.node import Node
from ackermann_msgs.msg import AckermannDriveStamped
import sys
import select
import termios
import tty


class KeyboardTeleop(Node):
    def __init__(self):
        super().__init__('keyboard_teleop')
        self.pub = self.create_publisher(AckermannDriveStamped, '/ackermann_cmd', 1)
        self.speed = 1.0
        self.turn = 0.6
        self.settings = termios.tcgetattr(sys.stdin)
        self.get_logger().info('Keyboard teleop ready. WASD to drive, CTRL-C to quit.')

        self.key_map = {
            'w': (1, 0),
            'd': (1, -1),
            'a': (1, 1),
            's': (-1, 0),
        }

    def get_key(self):
        tty.setraw(sys.stdin.fileno())
        select.select([sys.stdin], [], [], 0)
        key = sys.stdin.read(1)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        return key

    def run(self):
        try:
            while rclpy.ok():
                key = self.get_key()
                if key in self.key_map:
                    x, th = self.key_map[key]
                elif key == '\x03':
                    break
                else:
                    x, th = 0, 0

                msg = AckermannDriveStamped()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.header.frame_id = 'base_link'
                msg.drive.speed = float(x * self.speed)
                msg.drive.acceleration = 1.0
                msg.drive.jerk = 1.0
                msg.drive.steering_angle = float(th * self.turn)
                msg.drive.steering_angle_velocity = 1.0
                self.pub.publish(msg)
        except Exception as e:
            self.get_logger().error(str(e))
        finally:
            msg = AckermannDriveStamped()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'base_link'
            msg.drive.speed = 0.0
            msg.drive.acceleration = 1.0
            msg.drive.jerk = 1.0
            msg.drive.steering_angle = 0.0
            msg.drive.steering_angle_velocity = 1.0
            self.pub.publish(msg)
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)


def main():
    rclpy.init()
    node = KeyboardTeleop()
    node.run()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
