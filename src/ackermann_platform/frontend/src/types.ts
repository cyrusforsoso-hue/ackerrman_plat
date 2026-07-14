export interface VehicleState {
  pose: [number, number, number];
  speed: number;
  path: [number, number, number][];
  connected: boolean;
  algo_mode: string | null;
  algo_running: boolean;
  algo_error: string | null;
  active_path: string;
}

export interface PathInfo {
  name: string;
  filename: string;
  source: string;
  waypoints: number;
}

export interface AlgoStatus {
  mode: string | null;
  running: boolean;
  topic_name: string | null;
  error: string | null;
  params: Record<string, unknown>;
}
