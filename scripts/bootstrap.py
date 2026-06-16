from __future__ import annotations

import sys
from pathlib import Path


def ensure_workspace_imports() -> None:
    project_root = Path(__file__).resolve().parents[1]
    preferred = [str(project_root / "src"), str(project_root)]
    existing = [path for path in sys.path if path not in preferred]
    sys.path[:] = preferred + existing
