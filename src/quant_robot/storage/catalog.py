from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


DATA_FILE_SUFFIXES = {".csv", ".parquet", ".json"}


def build_storage_catalog(
    root: str | Path,
    *,
    include_datasets: bool = True,
    count_rows: bool = True,
) -> dict[str, Any]:
    root_path = Path(root)
    files = [path for path in root_path.rglob("*") if path.is_file() and path.suffix.lower() in DATA_FILE_SUFFIXES] if root_path.exists() else []
    datasets = [_file_summary(root_path, path, count_rows=count_rows) for path in sorted(files)] if include_datasets else []
    catalog = {
        "root": str(root_path),
        "total_files": len(files),
        "total_bytes": sum(path.stat().st_size for path in files),
        "total_rows": (
            sum(item["rows"] for item in datasets if item["rows"] is not None)
            if include_datasets and count_rows
            else None
        ),
    }
    if include_datasets:
        catalog["datasets"] = datasets
    return catalog


def _file_summary(root: Path, path: Path, *, count_rows: bool = True) -> dict[str, Any]:
    relative = path.relative_to(root).as_posix()
    parts = Path(relative).parts
    partition_start = next((index for index, part in enumerate(parts) if "=" in part), len(parts) - 1)
    dataset = "/".join(parts[:partition_start])
    return {
        "path": relative,
        "dataset": dataset,
        "format": path.suffix.lower().lstrip("."),
        "bytes": path.stat().st_size,
        "rows": _count_csv_rows(path) if count_rows and path.suffix.lower() == ".csv" else None,
        "partitions": _partitions(parts),
    }


def _partitions(parts: tuple[str, ...]) -> dict[str, str]:
    result = {}
    for part in parts:
        if "=" in part:
            key, value = part.split("=", 1)
            result[key] = value
    return result


def _count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        return sum(1 for _ in reader)
