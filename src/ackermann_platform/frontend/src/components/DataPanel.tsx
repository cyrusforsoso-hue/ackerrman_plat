import type { VehicleState } from '../types';

interface Props {
  state: VehicleState;
}

export default function DataPanel({ state }: Props) {
  const [x, y, yaw] = state.pose;
  const yawDeg = ((yaw * 180) / Math.PI).toFixed(1);

  // Cross-track error: distance from vehicle to closest path point
  let crossTrack = NaN;
  if (state.path.length > 0) {
    let minDist = Infinity;
    for (const [px, py] of state.path) {
      const d = Math.hypot(px - x, py - y);
      if (d < minDist) minDist = d;
    }
    crossTrack = minDist;
  }

  return (
    <div className="panel">
      <h2>Real-Time Data</h2>

      <div className="data-grid">
        <div className="data-item">
          <span className="label">Speed</span>
          <span className="value">{state.speed.toFixed(2)} m/s</span>
        </div>
        <div className="data-item">
          <span className="label">X</span>
          <span className="value">{x.toFixed(2)} m</span>
        </div>
        <div className="data-item">
          <span className="label">Y</span>
          <span className="value">{y.toFixed(2)} m</span>
        </div>
        <div className="data-item">
          <span className="label">Yaw</span>
          <span className="value">{yawDeg} deg</span>
        </div>
        <div className="data-item">
          <span className="label">Cross-Track Error</span>
          <span className="value">{isNaN(crossTrack) ? '--' : crossTrack.toFixed(3)} m</span>
        </div>
        <div className="data-item">
          <span className="label">Path Waypoints</span>
          <span className="value">{state.path.length}</span>
        </div>
        <div className="data-item">
          <span className="label">Sim Connected</span>
          <span className={`value ${state.connected ? 'green' : 'red'}`}>
            {state.connected ? 'Yes' : 'No'}
          </span>
        </div>
      </div>
    </div>
  );
}
