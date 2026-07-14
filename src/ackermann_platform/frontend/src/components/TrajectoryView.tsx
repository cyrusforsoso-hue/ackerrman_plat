import { useRef, useEffect } from 'react';
import type { VehicleState } from '../types';

interface Props {
  state: VehicleState;
}

const CANVAS_W = 600;
const CANVAS_H = 500;
const PADDING = 40;
const CAR_LENGTH = 12; // pixels

export default function TrajectoryView({ state }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const trailRef = useRef<[number, number][]>([]);

  // Accumulate trail
  const [x, y] = state.pose;
  if (x !== 0 || y !== 0) {
    const last = trailRef.current[trailRef.current.length - 1];
    if (!last || Math.hypot(x - last[0], y - last[1]) > 0.05) {
      trailRef.current.push([x, y]);
    }
  }
  // Keep last 5000 points
  if (trailRef.current.length > 5000) {
    trailRef.current = trailRef.current.slice(-5000);
  }

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const w = CANVAS_W;
    const h = CANVAS_H;

    // Compute bounds from path + trail + current pose
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

    state.path.forEach(([px, py]) => {
      if (px < minX) minX = px; if (px > maxX) maxX = px;
      if (py < minY) minY = py; if (py > maxY) maxY = py;
    });
    trailRef.current.forEach(([tx, ty]) => {
      if (tx < minX) minX = tx; if (tx > maxX) maxX = tx;
      if (ty < minY) minY = ty; if (ty > maxY) maxY = ty;
    });
    if (x < minX) minX = x; if (x > maxX) maxX = x;
    if (y < minY) minY = y; if (y > maxY) maxY = y;

    // Ensure minimum span
    const spanX = maxX - minX || 10;
    const spanY = maxY - minY || 10;
    minX -= spanX * 0.1; maxX += spanX * 0.1;
    minY -= spanY * 0.1; maxY += spanY * 0.1;

    const scaleX = (w - 2 * PADDING) / (maxX - minX || 1);
    const scaleY = (h - 2 * PADDING) / (maxY - minY || 1);
    const scale = Math.min(scaleX, scaleY);

    const toScreenX = (wx: number) => PADDING + (wx - minX) * scale;
    const toScreenY = (wy: number) => h - PADDING - (wy - minY) * scale;

    // Clear
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, w, h);

    // Grid
    ctx.strokeStyle = '#2a2a4e';
    ctx.lineWidth = 0.5;
    const gridStep = scale > 20 ? 1 : scale > 5 ? 2 : 5;
    for (let gx = Math.floor(minX / gridStep) * gridStep; gx <= maxX; gx += gridStep) {
      ctx.beginPath();
      ctx.moveTo(toScreenX(gx), PADDING);
      ctx.lineTo(toScreenX(gx), h - PADDING);
      ctx.stroke();
    }
    for (let gy = Math.floor(minY / gridStep) * gridStep; gy <= maxY; gy += gridStep) {
      ctx.beginPath();
      ctx.moveTo(PADDING, toScreenY(gy));
      ctx.lineTo(w - PADDING, toScreenY(gy));
      ctx.stroke();
    }

    // Reference path (grey)
    if (state.path.length > 1) {
      ctx.strokeStyle = '#888';
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      ctx.moveTo(toScreenX(state.path[0][0]), toScreenY(state.path[0][1]));
      for (let i = 1; i < state.path.length; i++) {
        ctx.lineTo(toScreenX(state.path[i][0]), toScreenY(state.path[i][1]));
      }
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Trail (blue)
    if (trailRef.current.length > 1) {
      ctx.strokeStyle = '#4488ff';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(toScreenX(trailRef.current[0][0]), toScreenY(trailRef.current[0][1]));
      for (let i = 1; i < trailRef.current.length; i++) {
        ctx.lineTo(toScreenX(trailRef.current[i][0]), toScreenY(trailRef.current[i][1]));
      }
      ctx.stroke();
    }

    // Vehicle (triangle arrow)
    const sx = toScreenX(x);
    const sy = toScreenY(y);
    const [, , yaw] = state.pose;

    ctx.save();
    ctx.translate(sx, sy);
    ctx.rotate(-yaw); // canvas Y is flipped
    ctx.fillStyle = state.connected ? '#00ff88' : '#ff4444';
    ctx.beginPath();
    ctx.moveTo(CAR_LENGTH, 0);
    ctx.lineTo(-CAR_LENGTH * 0.6, -CAR_LENGTH * 0.5);
    ctx.lineTo(-CAR_LENGTH * 0.6, CAR_LENGTH * 0.5);
    ctx.closePath();
    ctx.fill();
    ctx.restore();

    // Legend
    ctx.fillStyle = '#888';
    ctx.font = '11px monospace';
    ctx.fillText('--- Reference Path', PADDING + 5, PADDING + 15);
    ctx.fillStyle = '#4488ff';
    ctx.fillText('--- Actual Trajectory', PADDING + 5, PADDING + 30);
  });

  return (
    <div className="panel">
      <h2>Trajectory View</h2>
      <canvas
        ref={canvasRef}
        width={CANVAS_W}
        height={CANVAS_H}
        style={{ width: '100%', maxWidth: CANVAS_W, border: '1px solid #333', borderRadius: 4 }}
      />
    </div>
  );
}
