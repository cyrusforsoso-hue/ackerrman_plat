"""Abstract base class for user planning algorithms (Mode B — Python script upload)."""
from abc import ABC, abstractmethod
from typing import List, Tuple


class PlannerBase(ABC):
    """Users inherit this class and implement compute().

    The platform calls:
      1. __init__(params) — once, with algorithm parameters from the UI
      2. compute(pose, current_v, path) — at control frequency (e.g. 20 Hz)

    compute() must return (speed_m_s: float, steering_angle_rad: float).
    """

    def __init__(self, params: dict):
        """Initialize planner with parameters dict from frontend config."""
        self._params = params

    @abstractmethod
    def compute(
        self,
        pose: Tuple[float, float, float],
        current_v: float,
        path: List[Tuple[float, float, float]],
    ) -> Tuple[float, float]:
        """Compute control command.

        Args:
            pose: (x, y, yaw) in world frame.
            current_v: current longitudinal velocity [m/s].
            path: list of (x, y, yaw) waypoints.

        Returns:
            (speed_m_s, steering_angle_rad)
        """
        ...
