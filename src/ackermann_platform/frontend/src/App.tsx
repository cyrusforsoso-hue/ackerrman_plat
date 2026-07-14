import { useWebSocket } from './hooks/useWebSocket';
import ControlPanel from './components/ControlPanel';
import DataPanel from './components/DataPanel';
import TrajectoryView from './components/TrajectoryView';
import PathManager from './components/PathManager';
import './App.css';

const WS_URL = 'ws://localhost:8000/ws';

export default function App() {
  const { state, send, connected } = useWebSocket(WS_URL);

  return (
    <div className="app">
      <header>
        <h1>Ackermann Algorithm Test Platform</h1>
        <span className={`ws-status ${connected ? 'green' : 'red'}`}>
          {connected ? 'Connected' : 'Disconnected'}
        </span>
      </header>

      <main>
        <div className="left-column">
          <ControlPanel state={state} send={send} />
          <DataPanel state={state} />
        </div>
        <div className="center-column">
          <TrajectoryView state={state} />
        </div>
        <div className="right-column">
          <PathManager activePath={state.active_path} />
        </div>
      </main>
    </div>
  );
}
