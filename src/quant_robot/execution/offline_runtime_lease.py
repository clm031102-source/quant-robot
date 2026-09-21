"""Process-held advisory ownership; the leftover file is never the lock itself."""
from __future__ import annotations

import os
from pathlib import Path


class RuntimeLease:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()

    def __init__(self, journal_path, *, role="driver"):
        if role not in {"driver", "supervisor"}:
            raise ValueError("invalid offline lease role")
        path = Path(str(Path(journal_path).resolve()) + "." + role + ".lock")
        self._file = path.open("a+b")
        self._locked = False
        try:
            self._file.seek(0, os.SEEK_END)
            if self._file.tell() == 0:
                self._file.write(b"0")
                self._file.flush()
            self._file.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._locked = True
        except OSError as exc:
            self.close()
            raise ValueError("another offline " + role + " owns this journal") from exc

    def close(self):
        if self._file is None:
            return
        try:
            if self._locked:
                self._file.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        finally:
            self._file.close()
            self._file, self._locked = None, False
