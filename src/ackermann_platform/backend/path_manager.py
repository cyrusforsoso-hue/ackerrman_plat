"""Path file management: list, upload, delete CSV waypoint files."""
import csv
import os
import re
import uuid
from typing import List, Optional


PATHS_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'paths')


class PathManager:
    def __init__(self):
        os.makedirs(PATHS_DIR, exist_ok=True)

    def list_paths(self) -> List[dict]:
        """Return all available paths, both built-in and user-uploaded."""
        paths = []

        # Built-in path from pure_pursuit data directory
        builtin = os.path.join(
            os.path.dirname(__file__), '..', '..', 'pure_pursuit', 'data', 'path.csv'
        )
        if os.path.exists(builtin):
            paths.append({
                'name': 'default (built-in)',
                'filename': 'default',
                'source': 'builtin',
                'waypoints': self._count_waypoints(builtin),
            })

        # User-uploaded paths
        for fname in sorted(os.listdir(PATHS_DIR)):
            if fname.endswith('.csv'):
                fpath = os.path.join(PATHS_DIR, fname)
                display = fname.replace('.csv', '')
                paths.append({
                    'name': f'{display} (uploaded)',
                    'filename': fname,
                    'source': 'uploaded',
                    'waypoints': self._count_waypoints(fpath),
                })

        return paths

    def add_path(self, filename: str, content: bytes) -> dict:
        """Save uploaded CSV and return its metadata."""
        safe = re.sub(r'[^\w\-.]', '_', filename)
        if not safe.endswith('.csv'):
            safe += '.csv'
        if not safe or safe == '.csv':
            safe = f'path_{uuid.uuid4().hex[:8]}.csv'

        fpath = os.path.join(PATHS_DIR, safe)
        # Avoid overwrite
        base, ext = os.path.splitext(safe)
        counter = 1
        while os.path.exists(fpath):
            fpath = os.path.join(PATHS_DIR, f'{base}_{counter}{ext}')
            counter += 1

        with open(fpath, 'wb') as f:
            f.write(content)

        return {
            'name': os.path.basename(fpath),
            'filename': os.path.basename(fpath),
            'source': 'uploaded',
            'waypoints': self._count_waypoints(fpath),
        }

    def delete_path(self, filename: str) -> bool:
        """Delete an uploaded path. Returns False if not found or is builtin."""
        if filename == 'default':
            return False
        safe = re.sub(r'[^\w\-.]', '_', filename)
        fpath = os.path.join(PATHS_DIR, safe)
        if os.path.exists(fpath):
            os.remove(fpath)
            return True
        return False

    def get_path_filepath(self, filename: str) -> Optional[str]:
        """Get absolute file path for a path by filename."""
        if filename == 'default':
            builtin = os.path.join(
                os.path.dirname(__file__), '..', '..', 'pure_pursuit', 'data', 'path.csv'
            )
            return builtin if os.path.exists(builtin) else None
        fpath = os.path.join(PATHS_DIR, os.path.basename(filename))
        return fpath if os.path.exists(fpath) else None

    @staticmethod
    def _count_waypoints(filepath: str) -> int:
        try:
            with open(filepath, 'r') as f:
                reader = csv.reader(f)
                return sum(1 for row in reader if row and not row[0].startswith('#'))
        except Exception:
            return 0
