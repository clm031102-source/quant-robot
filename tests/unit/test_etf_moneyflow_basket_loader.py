import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.storage.etf_moneyflow_baskets import load_etf_moneyflow_baskets


class EtfMoneyflowBasketLoaderTests(unittest.TestCase):
    def test_loader_accepts_store_root_metadata_root_or_nested_search_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            search_root = Path(tmp)
            store_root = search_root / "tushare_cn_etf"
            frame = pd.DataFrame(
                {
                    "etf_asset_id": ["CN_ETF_XSHG_510300"],
                    "etf_symbol": ["510300.SH"],
                    "stock_asset_id": ["CN_XSHG_600519"],
                    "stock_symbol": ["600519.SH"],
                    "weight": [0.6],
                    "known_date": [pd.Timestamp("2024-01-01").date()],
                    "end_date": [pd.NaT],
                    "source": ["fixture_basket"],
                }
            )
            DatasetStore(store_root).write_frame(
                frame,
                "metadata/etf_moneyflow_baskets",
                {"market": "CN_ETF"},
            )

            from_store_root = load_etf_moneyflow_baskets(store_root, "CN_ETF")
            from_metadata_root = load_etf_moneyflow_baskets(store_root / "metadata", "CN_ETF")
            from_search_root = load_etf_moneyflow_baskets(search_root, "CN_ETF")

            self.assertEqual(len(from_store_root), 1)
            self.assertEqual(len(from_metadata_root), 1)
            self.assertEqual(len(from_search_root), 1)

    def test_loader_requires_specific_market(self):
        with self.assertRaisesRegex(ValueError, "market must be specific"):
            load_etf_moneyflow_baskets(Path("."), "ALL")


if __name__ == "__main__":
    unittest.main()
