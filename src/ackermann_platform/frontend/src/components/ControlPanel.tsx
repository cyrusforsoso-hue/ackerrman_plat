import { useState } from 'react';
import type { VehicleState } from '../types';

interface Props {
  state: VehicleState;
  send: (msg: object) => void;
}

export default function ControlPanel({ state, send }: Props) {
  const [mode, setMode] = useState<'A' | 'B'>('A');
  const [topicName, setTopicName] = useState('/my_planner/ackermann_cmd');
  const [scriptContent, setScriptContent] = useState(`from ackermann_platform.backend.planner_base import PlannerBase

class MyPlanner(PlannerBase):
    def compute(self, pose, current_v, path):
        # pose: (x, y, yaw), return (speed, steer_angle)
        return (1.0, 0.0)
`);
  const [paramsText, setParamsText] = useState('{"hz": 20}');
  const [uploadError, setUploadError] = useState('');

  const isRunning = state.algo_running;

  const handleStart = () => {
    if (mode === 'A') {
      send({ action: 'start', mode: 'A', topic_name: topicName });
    } else {
      let params: Record<string, unknown> = {};
      try {
        params = JSON.parse(paramsText);
      } catch {
        setUploadError('Invalid JSON params');
        return;
      }
      fetch('/api/algorithm/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'B', script_content: scriptContent, params }),
      });
    }
  };

  const handleStop = () => {
    fetch('/api/algorithm/stop', { method: 'POST' });
    send({ action: 'stop' });
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    setScriptContent(text);
  };

  return (
    <div className="panel">
      <h2>Algorithm Control</h2>

      <div className="mode-select">
        <label>
          <input type="radio" value="A" checked={mode === 'A'} onChange={() => setMode('A')} />
          Mode A: ROS Topic
        </label>
        <label>
          <input type="radio" value="B" checked={mode === 'B'} onChange={() => setMode('B')} />
          Mode B: Python Script
        </label>
      </div>

      {mode === 'A' && (
        <div className="field">
          <label>Topic Name:</label>
          <input
            type="text"
            value={topicName}
            onChange={(e) => setTopicName(e.target.value)}
            disabled={isRunning}
          />
        </div>
      )}

      {mode === 'B' && (
        <>
          <div className="field">
            <label>Upload Script:</label>
            <input type="file" accept=".py" onChange={handleFileUpload} disabled={isRunning} />
          </div>
          <div className="field">
            <label>Or paste code:</label>
            <textarea
              rows={8}
              value={scriptContent}
              onChange={(e) => setScriptContent(e.target.value)}
              disabled={isRunning}
              style={{ fontFamily: 'monospace', fontSize: '12px' }}
            />
          </div>
          <div className="field">
            <label>Parameters (JSON):</label>
            <input
              type="text"
              value={paramsText}
              onChange={(e) => setParamsText(e.target.value)}
              disabled={isRunning}
            />
          </div>
        </>
      )}

      <div className="button-row">
        <button onClick={handleStart} disabled={isRunning} className="btn-start">
          Start
        </button>
        <button onClick={handleStop} disabled={!isRunning} className="btn-stop">
          Stop
        </button>
      </div>

      {state.algo_mode && (
        <div className="status-text">
          Mode: {state.algo_mode} | Running: {state.algo_running ? 'Yes' : 'No'}
        </div>
      )}
      {state.algo_error && (
        <div className="error-text">{state.algo_error}</div>
      )}
      {uploadError && <div className="error-text">{uploadError}</div>}
    </div>
  );
}
