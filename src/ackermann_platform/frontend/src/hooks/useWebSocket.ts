import { useEffect, useRef, useState, useCallback } from 'react';
import type { VehicleState } from '../types';

const RECONNECT_DELAY = 2000;

export function useWebSocket(url: string) {
  const [state, setState] = useState<VehicleState>({
    pose: [0, 0, 0],
    speed: 0,
    path: [],
    connected: false,
    algo_mode: null,
    algo_running: false,
    algo_error: null,
    active_path: 'default',
  });
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => {
      setWsConnected(false);
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as VehicleState;
        setState(data);
      } catch { /* ignore parse errors */ }
    };
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((msg: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  return { state, send, connected: wsConnected };
}
