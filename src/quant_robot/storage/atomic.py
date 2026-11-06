from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any, BinaryIO, Callable


def _open_windows_file(path: str | Path, access: int):
    import ctypes
    from ctypes import wintypes

    filename = str(Path(path))
    if "\x00" in filename:
        raise ValueError("embedded null character")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.CreateFileW(
        filename, access, 0x1 | 0x2 | 0x4, None, 3, 0x80, None,
    )  # SHARE_READ | SHARE_WRITE | SHARE_DELETE, OPEN_EXISTING.
    if handle == ctypes.c_void_p(-1).value:
        error = ctypes.WinError(ctypes.get_last_error())
        error.filename = str(path)
        raise error
    return kernel, handle


def open_atomic_read(path: str | Path) -> BinaryIO:
    """Read the opened version without preventing an atomic publisher replacing it.

    Writers must publish by replacement, not mutate the opened file in place.
    On Windows the default CRT reader denies deletion, so even a paused reader
    can exhaust the publisher's contention budget. Share deletion explicitly;
    the handle still refers to the complete old file after the path is replaced.
    """
    if os.name != "nt":
        return Path(path).open("rb")

    import msvcrt

    kernel, handle = _open_windows_file(path, 0x80000000)  # GENERIC_READ.
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException:
        kernel.CloseHandle(handle)
        raise
    # The CRT owns the native handle after open_osfhandle succeeds.
    try:
        return os.fdopen(descriptor, "rb")
    except BaseException:
        os.close(descriptor)
        raise


def _replace_open_windows_file(source: Path, target: Path) -> None:
    """Atomically rename while readers retain their already-open file version."""
    import ctypes
    from ctypes import wintypes

    name = str(target.absolute()).encode("utf-16-le")

    class RenameInfo(ctypes.Structure):
        _fields_ = [("Flags", wintypes.DWORD), ("RootDirectory", wintypes.HANDLE),
                    ("FileNameLength", wintypes.DWORD), ("FileName", ctypes.c_ubyte * (len(name) + 2))]

    info = RenameInfo()
    info.Flags = 0x1 | 0x2  # REPLACE_IF_EXISTS | POSIX_SEMANTICS; no ACL/readonly bypass.
    info.FileNameLength = len(name)
    # Win32 FILE_RENAME_INFO.FileName requires a NUL-terminated UTF-16 string.
    # Its byte length excludes the terminator; structure padding is insufficient.
    info.FileName[:] = name + b"\x00\x00"
    kernel, handle = _open_windows_file(source, 0x10000)  # DELETE access for rename.
    try:
        kernel.SetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.c_int,
            ctypes.c_void_p, wintypes.DWORD]
        kernel.SetFileInformationByHandle.restype = wintypes.BOOL
        if not kernel.SetFileInformationByHandle(handle, 22, ctypes.byref(info), ctypes.sizeof(info)):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(handle)


def _replace_atomic(source: Path, target: Path) -> None:
    try:
        os.replace(source, target)
    except OSError as exc:
        if os.name != "nt" or getattr(exc, "winerror", None) not in {5, 32, 33}:
            raise
        # MoveFileEx (os.replace) rejects an open target even when its readers
        # share deletion. FileRenameInfoEx preserves those readers' snapshots.
        try:
            _replace_open_windows_file(source, target)
        except OSError as native_error:
            if getattr(native_error, "winerror", None) in {1, 50, 87, 120}:
                # Unsupported OS/filesystem: retain the ordinary failure and
                # bounded retry behavior, never delete or overwrite in place.
                raise exc from native_error
            raise


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
                _replace_atomic(temporary, target)
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
