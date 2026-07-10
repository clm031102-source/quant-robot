from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

from quant_robot.storage.atomic import atomic_write, atomic_write_json


FORMAT_MARKER = "_format.json"


class DatasetStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def write_frame(self, frame: pd.DataFrame, dataset: str, partitions: dict[str, str]) -> Path:
        path = self.partition_path(dataset, partitions)
        path.mkdir(parents=True, exist_ok=True)
        sorted_frame = _stable_sort(frame)
        if _has_parquet_engine():
            file_path = path / "part-00000.parquet"
            storage_format = "parquet"
            atomic_write(file_path, lambda temporary: sorted_frame.to_parquet(temporary, index=False))
        else:
            file_path = path / "part-00000.csv"
            storage_format = "csv"
            atomic_write(file_path, lambda temporary: sorted_frame.to_csv(temporary, index=False))
        atomic_write_json(path / FORMAT_MARKER, {"format": storage_format, "file": file_path.name})
        _remove_stale_partition_files(path, keep=file_path)
        return file_path

    def read_frame(self, dataset: str, partitions: dict[str, str]) -> pd.DataFrame:
        path = self.partition_path(dataset, partitions)
        marked_files = _marked_files(path)
        if marked_files is not None:
            storage_format, files = marked_files
            if storage_format == "parquet" and files:
                return pd.concat([pd.read_parquet(file) for file in files], ignore_index=True)
            if storage_format == "csv" and files:
                return pd.concat([pd.read_csv(file) for file in files], ignore_index=True)
            raise FileNotFoundError(f"Dataset format marker points to missing files under {path}")
        parquet_files = sorted(path.glob("*.parquet"))
        if parquet_files:
            return pd.concat([pd.read_parquet(file) for file in parquet_files], ignore_index=True)
        csv_files = sorted(path.glob("*.csv"))
        if csv_files:
            return pd.concat([pd.read_csv(file) for file in csv_files], ignore_index=True)
        raise FileNotFoundError(f"No dataset files found under {path}")

    def exists(self, dataset: str, partitions: dict[str, str]) -> bool:
        path = self.partition_path(dataset, partitions)
        marked_files = _marked_files(path)
        if marked_files is not None:
            return bool(marked_files[1])
        return any(path.glob("*.parquet")) or any(path.glob("*.csv"))

    def partition_path(self, dataset: str, partitions: dict[str, str]) -> Path:
        path = self.root / dataset
        for key in sorted(partitions):
            path = path / f"{key}={partitions[key]}"
        return path


def _has_parquet_engine() -> bool:
    return importlib.util.find_spec("pyarrow") is not None or importlib.util.find_spec("fastparquet") is not None


def _stable_sort(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [column for column in ["asset_id", "symbol", "date", "timestamp"] if column in frame.columns]
    if not columns:
        return frame.reset_index(drop=True)
    return frame.sort_values(columns).reset_index(drop=True)


def _marked_files(path: Path) -> tuple[str, list[Path]] | None:
    marker = path / FORMAT_MARKER
    if not marker.exists():
        return None
    try:
        import json

        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ValueError(f"Invalid dataset format marker: {marker}") from None
    storage_format = str(payload.get("format", ""))
    if storage_format not in {"parquet", "csv"}:
        raise ValueError(f"Invalid dataset storage format in {marker}: {storage_format}")
    configured_file = str(payload.get("file", "")).strip()
    files = [path / configured_file] if configured_file else sorted(path.glob(f"*.{storage_format}"))
    return storage_format, [file for file in files if file.exists()]


def _remove_stale_partition_files(path: Path, *, keep: Path) -> None:
    for pattern in ("*.parquet", "*.csv"):
        for candidate in path.glob(pattern):
            if candidate != keep:
                candidate.unlink(missing_ok=True)
