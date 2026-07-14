"""Example user planner — inherits PlannerBase, implements pure pursuit."""
import math
import sys
import os

# Allow importing from the platform package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from planner_base import PlannerBase


class ExamplePurePursuit(PlannerBase):
    """Simple pure pursuit: steer toward lookahead point, constant speed."""

    def __init__(self, params: dict):
        super().__init__(params)
        self.wheelbase = params.get('wheelbase', 1.5)
        self.speed = params.get('speed', 2.0)
        self.lookahead = params.get('lookahead', 3.0)

    def compute(self, pose, current_v, path):
        x, y, yaw = pose

        if len(path) < 2:
            return (0.0, 0.0)

        # Find lookahead point on path
        lookahead_pt = None
        for px, py, _ in path:
            if math.hypot(px - x, py - y) >= self.lookahead:
                lookahead_pt = (px, py)
                break

        if lookahead_pt is None:
            lookahead_pt = (path[-1][0], path[-1][1])

        # Pure pursuit steering
        lx, ly = lookahead_pt
        alpha = math.atan2(ly - y, lx - x) - yaw
        # Normalize to [-pi, pi]
        while alpha > math.pi: alpha -= 2 * math.pi
        while alpha < -math.pi: alpha += 2 * math.pi

        delta = math.atan2(2.0 * self.wheelbase * math.sin(alpha), self.lookahead)

        # Decelerate near end
        dist_to_end = math.hypot(path[-1][0] - x, path[-1][1] - y)
        v = self.speed
        if dist_to_end < self.lookahead:
            v = self.speed * (dist_to_end / self.lookahead)

        return (v, delta)
