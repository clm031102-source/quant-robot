import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.storage.moneyflow_inputs import discover_moneyflow_input_store_roots, load_moneyflow_inputs


class MoneyflowInputLoaderTests(unittest.TestCase):
    def test_loader_reads_all_moneyflow_input_year_partitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = DatasetStore(root)
            store.write_frame(_frame("2024-01-02"), "processed/moneyflow_inputs", {"frequency": "1d", "market": "CN", "year": "2024"})
            store.write_frame(_frame("2025-01-02"), "processed/moneyflow_inputs", {"frequency": "1d", "market": "CN", "year": "2025"})

            result = load_moneyflow_inputs(root, "CN")

            self.assertEqual(len(result), 2)
            self.assertEqual(sorted(pd.to_datetime(result["date"]).dt.year.unique().tolist()), [2024, 2025])

    def test_loader_discovers_store_root_processed_root_moneyflow_root_and_nested_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            search_root = Path(tmp)
            store_root = search_root / "nested" / "store"
            DatasetStore(store_root).write_frame(
                _frame("2024-01-02"),
                "processed/moneyflow_inputs",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )

            from_store_root = load_moneyflow_inputs(store_root, "CN")
            from_processed_root = load_moneyflow_inputs(store_root / "processed", "CN")
            from_moneyflow_root = load_moneyflow_inputs(store_root / "processed" / "moneyflow_inputs", "CN")
            from_search_root = load_moneyflow_inputs(search_root, "CN")

            self.assertEqual(len(from_store_root), 1)
            self.assertEqual(len(from_processed_root), 1)
            self.assertEqual(len(from_moneyflow_root), 1)
            self.assertEqual(len(from_search_root), 1)
            self.assertEqual(discover_moneyflow_input_store_roots(search_root, "CN"), [store_root])

    def test_loader_raises_when_moneyflow_inputs_are_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                load_moneyflow_inputs(Path(tmp), "CN")


def _frame(date: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [pd.Timestamp(date).date()],
            "asset_id": ["CN_XSHE_000001"],
            "symbol": ["000001.SZ"],
            "market": ["CN"],
            "source": ["tushare_moneyflow"],
            "buy_sm_amount": [100.0],
            "sell_sm_amount": [80.0],
            "buy_md_amount": [300.0],
            "sell_md_amount": [250.0],
            "buy_lg_amount": [500.0],
            "sell_lg_amount": [450.0],
            "buy_elg_amount": [700.0],
            "sell_elg_amount": [650.0],
            "net_mf_amount": [120.0],
        }
    )


if __name__ == "__main__":
    unittest.main()
