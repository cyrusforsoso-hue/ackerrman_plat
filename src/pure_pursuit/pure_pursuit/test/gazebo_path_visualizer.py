#!/usr/bin/env python3
"""
gazebo_path_visualizer: spawns reference path as visual model in Gazebo.
  Subscribes to /global/reference_path (Path)
  Spawns a single SDF model with sphere geometry at each waypoint + connecting lines.
  Re-spawns on path update (deletes old model first).
"""
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from nav_msgs.msg import Path
from gazebo_msgs.srv import DeleteEntity, SpawnEntity


class GazeboPathVisualizer(Node):
    MODEL_NAME = 'reference_path_visual'

    def __init__(self):
        super().__init__('gazebo_path_visualizer')

        latched_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=1,
        )
        self.path_sub = self.create_subscription(
            Path, '/global/reference_path', self.path_cb, latched_qos)

        self.delete_client = self.create_client(DeleteEntity, '/gazebo/delete_entity')
        self.spawn_client = self.create_client(SpawnEntity, '/gazebo/spawn_entity')

        for client, name in [(self.delete_client, 'delete_entity'),
                             (self.spawn_client, 'spawn_entity')]:
            if not client.wait_for_service(timeout_sec=10.0):
                self.get_logger().warn(f'Service /gazebo/{name} not available')

        self.has_old_model = False
        self.get_logger().info('gazebo_path_visualizer ready')

    def path_cb(self, msg):
        # Delete old model
        if self.has_old_model:
            self._delete_model()
            self.has_old_model = False

        # Build SDF with spheres + line
        sdf = self._build_sdf(msg)
        if sdf is None:
            return

        # Spawn new model
        req = SpawnEntity.Request()
        req.name = self.MODEL_NAME
        req.xml = sdf
        req.robot_namespace = ''
        req.initial_pose.position.z = 0.02  # slightly above ground

        future = self.spawn_client.call_async(req)
        future.add_done_callback(lambda f: self._spawn_done(f, len(msg.poses)))

    def _delete_model(self):
        req = DeleteEntity.Request()
        req.name = self.MODEL_NAME
        self.delete_client.call_async(req)

    def _build_sdf(self, msg):
        if len(msg.poses) < 2:
            return None

        radius = 0.02

        # Build visual elements
        visuals_xml = ''
        for i, ps in enumerate(msg.poses):
            x, y, z = ps.pose.position.x, ps.pose.position.y, ps.pose.position.z
            # sphere at each waypoint
            visuals_xml += f'''
            <visual name="pt_{i}">
              <pose>{x} {y} {z} 0 0 0</pose>
              <geometry><sphere><radius>{radius}</radius></sphere></geometry>
              <material><ambient>0 1 0 1</ambient></material>
            </visual>'''

        # Polyline connecting all waypoints (as a series of small cylinders or use a polyline)
        # Gazebo doesn't have native polyline, so use thin boxes between consecutive points
        for i in range(len(msg.poses) - 1):
            p1 = msg.poses[i].pose.position
            p2 = msg.poses[i + 1].pose.position
            cx = (p1.x + p2.x) / 2.0
            cy = (p1.y + p2.y) / 2.0
            cz = (p1.z + p2.z) / 2.0
            dx = p2.x - p1.x
            dy = p2.y - p1.y
            dz = p2.z - p1.z
            length = (dx * dx + dy * dy + dz * dz) ** 0.5
            if length < 1e-6:
                continue
            yaw = __import__('math').atan2(dy, dx)
            pitch = __import__('math').atan2(-dz, (dx * dx + dy * dy) ** 0.5) if (dx * dx + dy * dy) > 1e-12 else 0.0
            visuals_xml += f'''
            <visual name="line_{i}">
              <pose>{cx} {cy} {cz} 0 {pitch} {yaw}</pose>
              <geometry><box><size>{length} 0.01 0.005</size></box></geometry>
              <material><ambient>0 0.8 0 1</ambient></material>
            </visual>'''

        sdf = f'''<?xml version="1.0"?>
<sdf version="1.6">
  <model name="{self.MODEL_NAME}">
    <static>true</static>
    <link name="path_link">
      {visuals_xml}
    </link>
  </model>
</sdf>'''
        return sdf

    def _spawn_done(self, future, count):
        try:
            result = future.result()
            if result.success:
                self.has_old_model = True
                self.get_logger().info(f'Path model spawned: {count} waypoints')
            else:
                self.get_logger().error(f'Spawn failed: {result.status_message}')
        except Exception as e:
            self.get_logger().error(f'Spawn error: {e}')


def main():
    rclpy.init()
    node = GazeboPathVisualizer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
