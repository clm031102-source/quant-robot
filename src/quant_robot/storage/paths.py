from __future__ import annotations

from pathlib import Path


def bars_partition_path(root: str | Path, frequency: str, market: str, year: int) -> Path:
    return Path(root) / "bars" / f"frequency={frequency}" / f"market={market}" / f"year={year}"


def dataset_path(root: str | Path, name: str) -> Path:
    return Path(root) / name
