from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Callable


def atomic_write(path: str | Path, writer: Callable[[Path], None]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.stem}.",
        suffix=target.suffix,
        dir=target.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        writer(temporary)
        with temporary.open("rb+") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        # Windows readers can briefly deny replacement even when they only read.
        # Reuse the already-fsynced file, with at most five 10 ms waits. Persistent
        # access errors and all other I/O errors still propagate to the caller.
        for attempt in range(6):
            try:
                os.replace(temporary, target)
                break
            except OSError as exc:
                if getattr(exc, "winerror", None) not in {5, 32, 33} or attempt == 5:
                    raise
                time.sleep(0.01)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def atomic_write_text(path: str | Path, text: str, *, encoding: str = "utf-8") -> Path:
    return atomic_write(path, lambda temporary: temporary.write_text(text, encoding=encoding))


def atomic_write_json(path: str | Path, payload: Any) -> Path:
    return atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
