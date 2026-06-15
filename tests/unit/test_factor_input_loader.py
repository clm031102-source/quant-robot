import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.storage.factor_inputs import discover_factor_input_store_roots, load_factor_inputs


class FactorInputLoaderTests(unittest.TestCase):
    def test_loader_reads_all_factor_input_year_partitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = DatasetStore(root)
            store.write_frame(_frame("2024-01-02"), "processed/factor_inputs", {"frequency": "1d", "market": "CN", "year": "2024"})
            store.write_frame(_frame("2025-01-02"), "processed/factor_inputs", {"frequency": "1d", "market": "CN", "year": "2025"})

            result = load_factor_inputs(root, "CN")

            self.assertEqual(len(result), 2)
            self.assertEqual(sorted(pd.to_datetime(result["date"]).dt.year.unique().tolist()), [2024, 2025])

    def test_loader_discovers_store_root_processed_root_factor_input_root_and_nested_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            search_root = Path(tmp)
            store_root = search_root / "nested" / "store"
            DatasetStore(store_root).write_frame(
                _frame("2024-01-02"),
                "processed/factor_inputs",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )

            from_store_root = load_factor_inputs(store_root, "CN")
            from_processed_root = load_factor_inputs(store_root / "processed", "CN")
            from_factor_input_root = load_factor_inputs(store_root / "processed" / "factor_inputs", "CN")
            from_search_root = load_factor_inputs(search_root, "CN")

            self.assertEqual(len(from_store_root), 1)
            self.assertEqual(len(from_processed_root), 1)
            self.assertEqual(len(from_factor_input_root), 1)
            self.assertEqual(len(from_search_root), 1)
            self.assertEqual(discover_factor_input_store_roots(search_root, "CN"), [store_root])

    def test_loader_raises_when_factor_inputs_are_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                load_factor_inputs(Path(tmp), "CN")


def _frame(date: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [pd.Timestamp(date).date()],
            "asset_id": ["CN_XSHE_000001"],
            "symbol": ["000001.SZ"],
            "market": ["CN"],
            "source": ["tushare"],
            "turnover_rate": [1.0],
            "turnover_rate_f": [1.1],
            "volume_ratio": [0.9],
            "pe_ttm": [10.0],
            "pb": [2.0],
            "ps_ttm": [5.0],
            "dv_ttm": [3.0],
            "total_mv": [100000.0],
            "circ_mv": [50000.0],
        }
    )


if __name__ == "__main__":
    unittest.main()
