from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

from quant_robot.storage.paths import dataset_path


class ParquetStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def write_dataset(self, frame: pd.DataFrame, name: str) -> Path:
        self._ensure_parquet_support()
        path = dataset_path(self.root, name)
        path.mkdir(parents=True, exist_ok=True)
        sorted_frame = self._sort_for_stability(frame)
        file_path = path / "part-00000.parquet"
        sorted_frame.to_parquet(file_path, index=False)
        return file_path

    def read_dataset(self, name: str) -> pd.DataFrame:
        self._ensure_parquet_support()
        path = dataset_path(self.root, name)
        return pd.read_parquet(path)

    @staticmethod
    def _ensure_parquet_support() -> None:
        if importlib.util.find_spec("pyarrow") is None and importlib.util.find_spec("fastparquet") is None:
            raise RuntimeError("Parquet support requires pyarrow or fastparquet")

    @staticmethod
    def _sort_for_stability(frame: pd.DataFrame) -> pd.DataFrame:
        sort_columns = [column for column in ["asset_id", "timestamp", "date"] if column in frame.columns]
        if not sort_columns:
            return frame.reset_index(drop=True)
        return frame.sort_values(sort_columns).reset_index(drop=True)
