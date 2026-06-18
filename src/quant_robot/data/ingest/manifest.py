from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class IngestManifest:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.data = self._load()

    def is_completed(self, key: str) -> bool:
        return key in self.data["completed"]

    def mark_completed(self, key: str, rows: int) -> None:
        self.data["completed"][key] = {"rows": int(rows)}
        self.data["failed"].pop(key, None)

    def mark_failed(self, key: str, reason: str) -> None:
        self.data["failed"][key] = reason
        self.data["completed"].pop(key, None)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, sort_keys=True), encoding="utf-8")

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"completed": {}, "failed": {}, "metadata": {}}
        loaded = json.loads(self.path.read_text(encoding="utf-8"))
        return {
            "completed": loaded.get("completed", {}),
            "failed": loaded.get("failed", {}),
            "metadata": loaded.get("metadata", {}),
        }
