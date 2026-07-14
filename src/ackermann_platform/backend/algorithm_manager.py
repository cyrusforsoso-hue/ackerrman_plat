"""Algorithm lifecycle management: topic bridge (Mode A) and script runner (Mode B)."""
import importlib.util
import os
import sys
import tempfile
import threading
import time
import traceback
from typing import Optional

from .ros_bridge import ROS2Bridge


class AlgorithmManager:
    def __init__(self, ros_bridge: ROS2Bridge):
        self._bridge = ros_bridge
        self._mode: Optional[str] = None       # 'A', 'B', or None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._script_content: Optional[str] = None
        self._error: Optional[str] = None
        self._params: dict = {}
        self._topic_name: Optional[str] = None
        self._planner = None

    def start_mode_a(self, topic_name: str):
        """Mode A: bridge an external ROS topic to /ackermann_cmd."""
        self.stop()
        self._mode = 'A'
        self._topic_name = topic_name
        self._running = True
        self._bridge.set_topic_bridge(topic_name)

    def start_mode_b(self, script_content: str, params: dict):
        """Mode B: load and run a user Python script implementing PlannerBase."""
        self.stop()
        self._mode = 'B'
        self._running = True
        self._params = params
        self._script_content = script_content
        self._error = None

        self._thread = threading.Thread(target=self._run_mode_b, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop running algorithm."""
        self._running = False
        if self._mode == 'A':
            self._bridge.set_topic_bridge(None)
        if self._thread:
            self._thread.join(timeout=2.0)
        self._thread = None
        self._mode = None
        self._topic_name = None
        self._planner = None

    def get_status(self) -> dict:
        return {
            'mode': self._mode,
            'running': self._running,
            'topic_name': self._topic_name,
            'error': self._error,
            'params': self._params if self._mode == 'B' else {},
        }

    def set_params(self, params: dict):
        """Update algorithm parameters at runtime (mutates dict so running planner sees changes)."""
        self._params.clear()
        self._params.update(params)

    def _run_mode_b(self):
        """Load user script and run compute() loop."""
        try:
            # Write script to temp file and import
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.py', delete=False, prefix='user_planner_'
            ) as f:
                f.write(self._script_content)
                tmp_path = f.name

            spec = importlib.util.spec_from_file_location('user_planner', tmp_path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules['user_planner'] = mod
            try:
                spec.loader.exec_module(mod)
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

            # Find PlannerBase subclass
            from .planner_base import PlannerBase
            planner_cls = None
            for name in dir(mod):
                obj = getattr(mod, name)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, PlannerBase)
                    and obj is not PlannerBase
                ):
                    planner_cls = obj
                    break

            if planner_cls is None:
                self._error = 'No PlannerBase subclass found in script'
                self._running = False
                return

            self._planner = planner_cls(self._params)
            hz = self._params.get('hz', 20)
            dt = 1.0 / hz

            while self._running:
                state = self._bridge.get_state()
                pose = state['pose']
                speed = state['speed']
                path = state['path']

                try:
                    v, delta = self._planner.compute(pose, speed, path)
                    self._bridge.publish_ackermann(v, delta)
                except Exception as e:
                    self._error = f'Planner compute error: {e}\n{traceback.format_exc()}'

                time.sleep(dt)

        except Exception as e:
            self._error = f'Script load error: {e}\n{traceback.format_exc()}'
            self._running = False
