import { useState, useEffect, useCallback } from 'react';
import type { PathInfo } from '../types';

interface Props {
  activePath: string;
}

export default function PathManager({ activePath }: Props) {
  const [paths, setPaths] = useState<PathInfo[]>([]);
  const [message, setMessage] = useState('');

  const fetchPaths = useCallback(async () => {
    try {
      const res = await fetch('/api/paths');
      const data = await res.json();
      setPaths(data.paths);
    } catch {
      setMessage('Failed to fetch paths');
    }
  }, []);

  useEffect(() => { fetchPaths(); }, [fetchPaths]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await fetch('/api/paths/upload', { method: 'POST', body: form });
      const data = await res.json();
      if (data.path) {
        setMessage(`Uploaded: ${data.path.name}`);
        fetchPaths();
      }
    } catch {
      setMessage('Upload failed');
    }
  };

  const handleActivate = async (filename: string) => {
    try {
      await fetch('/api/paths/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename }),
      });
      setMessage(`Activated: ${filename}`);
    } catch {
      setMessage('Activate failed');
    }
  };

  const handleDelete = async (filename: string) => {
    try {
      await fetch(`/api/paths/${filename}`, { method: 'DELETE' });
      fetchPaths();
      setMessage(`Deleted: ${filename}`);
    } catch {
      setMessage('Delete failed');
    }
  };

  return (
    <div className="panel">
      <h2>Reference Paths</h2>

      <div className="field">
        <input type="file" accept=".csv" onChange={handleUpload} />
      </div>

      <ul className="path-list">
        {paths.map((p) => (
          <li key={p.filename} className={p.filename === activePath ? 'active' : ''}>
            <span>{p.name} ({p.waypoints} pts)</span>
            <button onClick={() => handleActivate(p.filename)}>Use</button>
            {p.source === 'uploaded' && (
              <button onClick={() => handleDelete(p.filename)} className="btn-delete">
                Del
              </button>
            )}
          </li>
        ))}
      </ul>

      {message && <div className="status-text">{message}</div>}
    </div>
  );
}
