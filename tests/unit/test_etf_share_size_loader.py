import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.storage.etf_share_size import load_etf_share_size_inputs


class EtfShareSizeLoaderTests(unittest.TestCase):
    def test_loader_accepts_store_root_processed_root_or_nested_search_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            search_root = Path(tmp)
            store_root = search_root / "tushare_cn_etf"
            frame = pd.DataFrame(
                {
                    "date": [pd.Timestamp("2024-01-02").date()],
                    "asset_id": ["CN_ETF_XSHG_510300"],
                    "symbol": ["510300.SH"],
                    "market": ["CN_ETF"],
                    "source": ["tushare_etf_share_size"],
                    "total_share": [10_000_000.0],
                    "total_size": [40_000_000.0],
                    "nav": [4.0],
                    "close": [4.04],
                }
            )
            DatasetStore(store_root).write_frame(
                frame,
                "processed/etf_share_size",
                {"frequency": "1d", "market": "CN_ETF", "year": "2024"},
            )

            from_store_root = load_etf_share_size_inputs(store_root, "CN_ETF")
            from_processed_root = load_etf_share_size_inputs(store_root / "processed", "CN_ETF")
            from_search_root = load_etf_share_size_inputs(search_root, "CN_ETF")

            self.assertEqual(len(from_store_root), 1)
            self.assertEqual(len(from_processed_root), 1)
            self.assertEqual(len(from_search_root), 1)

    def test_loader_requires_specific_market(self):
        with self.assertRaisesRegex(ValueError, "market must be specific"):
            load_etf_share_size_inputs(Path("."), "ALL")


if __name__ == "__main__":
    unittest.main()
