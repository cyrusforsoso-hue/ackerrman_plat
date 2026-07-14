"""Standard Pure Pursuit algorithm — ROS-free, pure Python."""

import math
from typing import List, Tuple

import numpy as np


"角度归一化"
def angle_normalize(a: float) -> float:
    """Normalize angle to [-pi, pi]."""
    while a > math.pi:
        a -= 2.0 * math.pi
    while a < -math.pi:
        a += 2.0 * math.pi
    return a

"欧式距离"
def distance(ax: float, ay: float, bx: float, by: float) -> float:
    """Euclidean distance between two points."""
    return math.hypot(bx - ax, by - ay)


"路径裁剪，预处理：已走过的点删除"
"**多圈计时的时候需要改动"
def prune_path(
    pose: Tuple[float, float, float],
    path: List[Tuple[float, float, float]],
) -> List[Tuple[float, float, float]]:
    
    rx, ry, ryaw = pose
    if len(path) < 2:
        return path

    heading_x = math.cos(ryaw)
    heading_y = math.sin(ryaw)

    closest_idx = 0
    closest_dist = float('inf')
    for i, (px, py, _) in enumerate(path):
        d = distance(rx, ry, px, py)
        if d < closest_dist:
            closest_dist = d
            closest_idx = i

    px, py, _ = path[closest_idx]
    dot = (px - rx) * heading_x + (py - ry) * heading_y

    if dot >= 0.0:
        return path[closest_idx:]

    for i in range(closest_idx + 1, len(path)):
        px, py, _ = path[i]
        dot = (px - rx) * heading_x + (py - ry) * heading_y
        if dot >= 0.0:
            return path[i:]

    return path[-2:]

"截取局部路径"
def _extract_arc_segment(
    pruned_path: List[Tuple[float, float, float]],
    start_idx: int,
    arc_length: float,
) -> List[Tuple[float, float]]:
    
    """Extract consecutive points from start_idx covering arc_length distance."""
    if not pruned_path or start_idx >= len(pruned_path):
        return []

    points = [(pruned_path[start_idx][0], pruned_path[start_idx][1])]

    if len(pruned_path) - start_idx < 2:
        return points

    accumulated = 0.0
    for i in range(start_idx, len(pruned_path) - 1):
        x1, y1, _ = pruned_path[i]
        x2, y2, _ = pruned_path[i + 1]
        seg_len = distance(x1, y1, x2, y2)
        accumulated += seg_len
        points.append((x2, y2))
        if accumulated >= arc_length:
            break

    return points


def find_lookahead_point(
    Ld: float,
    pose: Tuple[float, float, float],
    pruned_path: List[Tuple[float, float, float]],
    cur_windows: float,
) -> Tuple[Tuple[float, float], float]:
    """Find lookahead point at distance Ld along path. Returns ((lx,ly), curvature)."""
    rx, ry, _ = pose

    if not pruned_path:
        return ((rx, ry), 0.0)

    min_dist = float('inf')
    start_idx = 0

    for i, (px, py, _) in enumerate(pruned_path):
        d = distance(rx, ry, px, py)
        if d < min_dist:
            min_dist = d
            start_idx = i

    accumulated = min_dist

    for i in range(start_idx, len(pruned_path) - 1):
        x1, y1, _ = pruned_path[i]
        x2, y2, _ = pruned_path[i + 1]
        seg_len = distance(x1, y1, x2, y2)
        if seg_len < 1e-12:
            continue

        if accumulated + seg_len >= Ld:
            lx, ly = x2, y2
            lookahead_idx = i + 1
            arc_pts = _extract_arc_segment(pruned_path, lookahead_idx, cur_windows)
            kappa = compute_curvature(arc_pts)
            return ((lx, ly), kappa)

        accumulated += seg_len

    last_pt = pruned_path[-1]
    return ((last_pt[0], last_pt[1]), 0.0)

"计算曲率"
def compute_curvature(points: List[Tuple[float, float]]) -> float:
    """Least-squares circle fit curvature. Left positive, right negative."""
    if len(points) < 3:
        return 0.0

    n = len(points)
    xs = np.array([p[0] for p in points])
    ys = np.array([p[1] for p in points])

    A = np.column_stack([xs, ys, np.ones(n)])
    d = -(xs ** 2 + ys ** 2)

    try:
        sol, _residuals, _rank, _singular = np.linalg.lstsq(A, d, rcond=None)
    except np.linalg.LinAlgError:
        return 0.0

    x0, y0 = points[0]
    x1_, y1_ = points[n // 2]
    x2_, y2_ = points[-1]
    area = abs((x1_ - x0) * (y2_ - y0) - (x2_ - x0) * (y1_ - y0))
    if area < 1e-12:
        return 0.0

    a, b, c = sol
    cx = -a / 2.0
    cy = -b / 2.0
    r_squared = cx ** 2 + cy ** 2 - c

    if r_squared <= 0.0:
        return 0.0

    radius = math.sqrt(r_squared)
    curvature = 1.0 / radius

    x0_c, y0_c = points[0][0] - cx, points[0][1] - cy
    xn_c, yn_c = points[-1][0] - cx, points[-1][1] - cy
    sign = 1.0 if x0_c * yn_c - y0_c * xn_c >= 0 else -1.0
    return sign * curvature


def smooth_speed(
    v_target: float,
    prev_v: float,
    accel: float,
    decel: float,
    dt: float,
    v_base: float,
) -> float:
    """Clamp speed change within accel/decel limits."""
    dv = v_target - prev_v
    max_dv_a = accel * dt
    max_dv_d = decel * dt
    if dv > max_dv_a:
        v = prev_v + max_dv_a
    elif dv < -max_dv_d:
        v = prev_v - max_dv_d
    else:
        v = v_target
    return max(0.0, min(v, v_base))


def compute_start_end_speed(
    v: float,
    pose: Tuple[float, float, float],
    pruned_path: List[Tuple[float, float, float]],
    decel: float,
) -> float:
    """Decelerate based on remaining path distance: need_dist = v^2/(2*decel)."""
    if not pruned_path or len(pruned_path) < 2:
        return 0.0

    rx, ry, _ = pose

    # Find closest path index to the vehicle
    closest_idx = 0
    closest_dist = float('inf')
    for i, (px, py, _) in enumerate(pruned_path):
        d = distance(rx, ry, px, py)
        if d < closest_dist:
            closest_dist = d
            closest_idx = i

    # Remaining distance = dist from vehicle to closest point + segments from closest to end
    remain_dist = distance(rx, ry,
                           pruned_path[closest_idx][0],
                           pruned_path[closest_idx][1])
    remain_dist += sum(
        distance(pruned_path[i][0], pruned_path[i][1],
                 pruned_path[i + 1][0], pruned_path[i + 1][1])
        for i in range(closest_idx, len(pruned_path) - 1)
    )

    if remain_dist <= 0.0:
        return 0.0

    need_dist = v * v / (2.0 * decel)

    if remain_dist <= need_dist:
        v_safe = math.sqrt(2.0 * decel * remain_dist)
        v = min(v, v_safe)

    return 0.0 if v < 0.01 else v


class PurePursuitPlanner:
    """Standard Pure Pursuit planner with curvature speed limit and start/end smoothing."""

    def __init__(self, params: dict):
        self._wheelbase = params['wheelbase']
        self._v_base = params['v_base']
        self._R0 = params['R0']
        self._Ld_min = params['Ld_min']
        self._Ld_max = params['Ld_max']
        self._accel = params['accel']
        self._decel = params['decel']
        self._cur_windows = params['cur_windows']
        self._hz = params['hz']
        self._dt = 1.0 / self._hz
        self._prev_v = 0.0

    def compute(
        self,
        pose: Tuple[float, float, float],
        current_v: float,
        path: List[Tuple[float, float, float]],
    ) -> Tuple[float, float, Tuple[float, float]]:
        """Compute control command.

        Args:
            pose: (x, y, yaw) in world frame.
            current_v: current longitudinal velocity [m/s].
            path: list of (x, y, yaw) waypoints.

        Returns:
            (v, delta, (lx, ly)) — target speed [m/s], steering angle [rad],
            and lookahead point coordinates.
        """
        rx, ry, ryaw = pose

        if len(path) < 2:
            self._prev_v = 0.0
            return (0.0, 0.0, (rx, ry))

        pruned = prune_path(pose, path)

        # Lookahead distance: linear speed mapping
        Ld = self._Ld_min + (abs(current_v) / self._v_base) * (self._Ld_max - self._Ld_min)
        Ld = max(self._Ld_min, min(Ld, self._Ld_max))

        (lx, ly), curvature = find_lookahead_point(Ld, pose, pruned, self._cur_windows)

        # Curvature speed limit: v = v_base * R / (R + R0)
        if abs(curvature) > 1e-9:
            R = abs(1.0 / curvature)
            v_curve = self._v_base * R / (R + self._R0)
        else:
            v_curve = self._v_base

        v_target = min(v_curve, self._v_base)

        # End-point deceleration
        v_target = compute_start_end_speed(v_target, pose, pruned, self._decel)

        # Smooth with accel/decel limits
        v_smooth = smooth_speed(v_target, self._prev_v, self._accel, self._decel,
                                self._dt, self._v_base)
        self._prev_v = v_smooth

        # Pure pursuit steering angle
        dphi = angle_normalize(math.atan2(ly - ry, lx - rx) - ryaw)
        kappa_pp = 2.0 * math.sin(dphi) / Ld
        delta = math.atan(self._wheelbase * kappa_pp)

        return (v_smooth, delta, (lx, ly))
