from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


DATA_FILE_SUFFIXES = {".csv", ".parquet"}
FINGERPRINT_SCHEMA_VERSION = 1


def fingerprint_frame(frame: pd.DataFrame, *, chunk_rows: int = 100_000) -> str:
    digest = hashlib.sha256()
    schema = [(str(column), str(frame[column].dtype)) for column in frame.columns]
    digest.update(json.dumps(schema, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))
    digest.update(str(len(frame)).encode("ascii"))
    for start in range(0, len(frame), max(int(chunk_rows), 1)):
        chunk = frame.iloc[start : start + chunk_rows]
        hashes = pd.util.hash_pandas_object(chunk, index=False, categorize=True)
        digest.update(hashes.to_numpy(dtype="uint64", copy=False).tobytes())
    return digest.hexdigest()


def fingerprint_schema(frame: pd.DataFrame) -> str:
    schema = [(str(column), str(frame[column].dtype)) for column in frame.columns]
    encoded = json.dumps(schema, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def fingerprint_dataset_root(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    files = _dataset_files(root_path)
    digest = hashlib.sha256()
    inventory: list[dict[str, Any]] = []
    for path in files:
        relative = path.name if root_path.is_file() else path.relative_to(root_path).as_posix()
        content_sha256 = sha256_file(path)
        stat = path.stat()
        row = {
            "path": relative,
            "size_bytes": int(stat.st_size),
            "mtime_ns": int(stat.st_mtime_ns),
            "sha256": content_sha256,
        }
        inventory.append(row)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(content_sha256.encode("ascii"))
        digest.update(b"\n")
    return {
        "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
        "root": str(root_path),
        "exists": root_path.exists(),
        "file_count": len(inventory),
        "content_sha256": digest.hexdigest(),
        "files": inventory,
    }


def fingerprint_research_source(root: str | Path, *, dataset: str) -> dict[str, Any]:
    root_path = Path(root)
    if root_path.is_file() and root_path.suffix.lower() == ".json":
        try:
            payload = json.loads(root_path.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError):
            payload = None
        if isinstance(payload, dict) and isinstance(payload.get("segments"), list):
            return fingerprint_authority_dataset_config(root_path, dataset=dataset, payload=payload)
    return fingerprint_dataset_root(root_path)


def fingerprint_authority_dataset_config(
    config_path: str | Path,
    *,
    dataset: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path = Path(config_path)
    data = payload if payload is not None else json.loads(path.read_text(encoding="utf-8-sig"))
    market = str(data.get("market", "CN")).upper()
    digest = hashlib.sha256()
    inventory: list[dict[str, Any]] = []

    if path.is_file():
        _append_fingerprint_file(
            inventory,
            digest,
            path,
            label=path.name,
        )
    segments = data.get("segments", []) if isinstance(data.get("segments"), list) else []
    missing_segment_data = False
    for index, raw_segment in enumerate(segments):
        if not isinstance(raw_segment, dict) or not raw_segment.get("root"):
            missing_segment_data = True
            continue
        segment_root = Path(str(raw_segment["root"]))
        base = segment_root / dataset / "frequency=1d" / f"market={market}"
        files = sorted(
            candidate
            for candidate in base.rglob("*")
            if candidate.is_file() and candidate.suffix.lower() in DATA_FILE_SUFFIXES
        ) if base.exists() else []
        if not files:
            missing_segment_data = True
        segment_contract = json.dumps(
            {
                "index": index,
                "root": str(segment_root),
                "start_date": raw_segment.get("start_date"),
                "end_date": raw_segment.get("end_date"),
                "adjusted_only": raw_segment.get("adjusted_only"),
                "dataset": dataset,
                "market": market,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        digest.update(segment_contract.encode("utf-8"))
        digest.update(b"\n")
        for candidate in files:
            _append_fingerprint_file(
                inventory,
                digest,
                candidate,
                label=f"segment_{index:03d}/{candidate.relative_to(segment_root).as_posix()}",
            )
    return {
        "fingerprint_schema_version": FINGERPRINT_SCHEMA_VERSION,
        "root": str(path),
        "exists": path.is_file() and bool(segments) and not missing_segment_data,
        "file_count": len(inventory),
        "content_sha256": digest.hexdigest(),
        "files": inventory,
        "dataset": dataset,
        "market": market,
        "authority_config": True,
    }


def sha256_file(path: str | Path, *, chunk_bytes: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_bytes):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text_parts(parts: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(str(part).encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _append_fingerprint_file(
    inventory: list[dict[str, Any]],
    digest: Any,
    path: Path,
    *,
    label: str,
) -> None:
    content_sha256 = sha256_file(path)
    stat = path.stat()
    row = {
        "path": label,
        "size_bytes": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
        "sha256": content_sha256,
    }
    inventory.append(row)
    digest.update(label.encode("utf-8"))
    digest.update(b"\0")
    digest.update(str(stat.st_size).encode("ascii"))
    digest.update(b"\0")
    digest.update(content_sha256.encode("ascii"))
    digest.update(b"\n")


def _dataset_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in DATA_FILE_SUFFIXES
    )
