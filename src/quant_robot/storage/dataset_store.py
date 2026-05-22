from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


class DatasetStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def write_frame(self, frame: pd.DataFrame, dataset: str, partitions: dict[str, str]) -> Path:
        path = self.partition_path(dataset, partitions)
        path.mkdir(parents=True, exist_ok=True)
        sorted_frame = _stable_sort(frame)
        if _has_parquet_engine():
            file_path = path / "part-00000.parquet"
            sorted_frame.to_parquet(file_path, index=False)
            return file_path
        file_path = path / "part-00000.csv"
        sorted_frame.to_csv(file_path, index=False)
        return file_path

    def read_frame(self, dataset: str, partitions: dict[str, str]) -> pd.DataFrame:
        path = self.partition_path(dataset, partitions)
        parquet_files = sorted(path.glob("*.parquet"))
        if parquet_files:
            return pd.concat([pd.read_parquet(file) for file in parquet_files], ignore_index=True)
        csv_files = sorted(path.glob("*.csv"))
        if csv_files:
            return pd.concat([pd.read_csv(file) for file in csv_files], ignore_index=True)
        raise FileNotFoundError(f"No dataset files found under {path}")

    def exists(self, dataset: str, partitions: dict[str, str]) -> bool:
        path = self.partition_path(dataset, partitions)
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
