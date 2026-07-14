"""FastAPI application: REST endpoints and WebSocket for the Ackermann test platform."""
import asyncio
import json
import os
import subprocess

from typing import Optional

from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from .ros_bridge import ROS2Bridge
from .path_manager import PathManager
from .algorithm_manager import AlgorithmManager

app = FastAPI(title='Ackermann Test Platform')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

# --- Global state ---
ros_bridge = ROS2Bridge()
path_manager = PathManager()
algo_manager = AlgorithmManager(ros_bridge)

# Store active path filename so we can publish it on start
_active_path: Optional[str] = 'default'

# Track path publisher subprocess
_path_publisher_proc: Optional[subprocess.Popen] = None


# --- Request/Response models ---

class StartRequest(BaseModel):
    mode: str  # 'A' or 'B'
    topic_name: Optional[str] = None
    script_content: Optional[str] = None
    params: dict = {}


class ParamsRequest(BaseModel):
    params: dict


class PathActivateRequest(BaseModel):
    filename: str


# --- Lifecycle ---

@app.on_event('startup')
async def startup():
    ros_bridge.start()


@app.on_event('shutdown')
async def shutdown():
    algo_manager.stop()
    ros_bridge.stop()
    _stop_path_publisher()


# --- Path management ---

def _start_path_publisher(csv_path: str):
    """Launch csv_path_publisher with given CSV file."""
    global _path_publisher_proc
    _stop_path_publisher()
    env = os.environ.copy()
    _path_publisher_proc = subprocess.Popen(
        ['ros2', 'run', 'pure_pursuit', 'csv_path_publisher',
         '--ros-args', '-p', f'csv_path:={csv_path}'],
        env=env,
    )


def _stop_path_publisher():
    global _path_publisher_proc
    if _path_publisher_proc:
        _path_publisher_proc.terminate()
        try:
            _path_publisher_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            _path_publisher_proc.kill()
        _path_publisher_proc = None


@app.get('/api/paths')
def list_paths():
    return {'paths': path_manager.list_paths(), 'active': _active_path}


@app.post('/api/paths/upload')
async def upload_path(file: UploadFile = File(...)):
    content = await file.read()
    result = path_manager.add_path(file.filename, content)
    return {'path': result}


@app.delete('/api/paths/{filename}')
def delete_path(filename: str):
    ok = path_manager.delete_path(filename)
    return {'deleted': ok}


@app.post('/api/paths/activate')
def activate_path(req: PathActivateRequest):
    global _active_path
    fpath = path_manager.get_path_filepath(req.filename)
    if not fpath:
        return {'error': f'Path not found: {req.filename}'}
    _active_path = req.filename
    _start_path_publisher(fpath)
    return {'active': _active_path}


@app.get('/api/status')
def get_status():
    state = ros_bridge.get_state()
    algo_status = algo_manager.get_status()
    return {
        'simulation': {
            'connected': state['connected'],
            'pose': list(state['pose']),
            'speed': state['speed'],
        },
        'algorithm': algo_status,
        'active_path': _active_path,
    }


@app.post('/api/algorithm/start')
def start_algorithm(req: StartRequest):
    if req.mode == 'A':
        if not req.topic_name:
            return {'error': 'topic_name required for mode A'}
        algo_manager.start_mode_a(req.topic_name)
    elif req.mode == 'B':
        if not req.script_content:
            return {'error': 'script_content required for mode B'}
        algo_manager.start_mode_b(req.script_content, req.params)
    else:
        return {'error': f'Unknown mode: {req.mode}'}
    return {'status': 'started', **algo_manager.get_status()}


@app.post('/api/algorithm/stop')
def stop_algorithm():
    algo_manager.stop()
    return {'status': 'stopped'}


@app.post('/api/algorithm/params')
def update_params(req: ParamsRequest):
    algo_manager.set_params(req.params)
    return {'params': req.params}


# --- WebSocket ---

@app.websocket('/ws')
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    hz = 10
    dt = 1.0 / hz
    try:
        while True:
            state = ros_bridge.get_state()
            algo_status = algo_manager.get_status()

            payload = {
                'pose': list(state['pose']),
                'speed': state['speed'],
                'path': state['path'],
                'connected': state['connected'],
                'algo_mode': algo_status['mode'],
                'algo_running': algo_status['running'],
                'algo_error': algo_status['error'],
                'active_path': _active_path,
            }

            await ws.send_json(payload)

            # Check for incoming control messages (non-blocking)
            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=0.01)
                msg = json.loads(raw)
                if msg.get('action') == 'stop':
                    algo_manager.stop()
                elif msg.get('action') == 'start' and msg.get('mode') == 'A':
                    algo_manager.start_mode_a(msg.get('topic_name', ''))
            except asyncio.TimeoutError:
                pass

            await asyncio.sleep(dt)

    except WebSocketDisconnect:
        pass
