import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.cn_etf_theme_map import load_cn_etf_theme_map
from quant_robot.storage.dataset_store import DatasetStore
from scripts.ingest_tushare_fund_basic import run_tushare_fund_basic_ingest


class TushareFundBasicIngestTests(unittest.TestCase):
    def test_ingest_writes_fund_basic_snapshot_for_theme_map_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = _FakeFundBasicAdapter()

            result = run_tushare_fund_basic_ingest(adapter, root, market="E", snapshot="2026-06-21")

            self.assertEqual(result["rows"], 2)
            self.assertEqual(result["snapshot"], "2026-06-21")
            stored = DatasetStore(root).read_frame(
                "metadata/tushare_fund_basic",
                {"market": "E", "snapshot": "2026-06-21"},
            )
            self.assertEqual(set(stored["symbol"]), {"510300.SH", "512880.SH"})
            theme_map = load_cn_etf_theme_map(root)
            self.assertEqual(set(theme_map["symbol"]), {"510300.SH", "512880.SH"})
            self.assertEqual(adapter.calls, [("fetch_fund_basic", "E")])


class _FakeFundBasicAdapter:
    def __init__(self) -> None:
        self.calls = []

    def fetch_fund_basic(self, market: str = "E") -> pd.DataFrame:
        self.calls.append(("fetch_fund_basic", market))
        return pd.DataFrame(
            {
                "symbol": ["510300.SH", "512880.SH"],
                "name": ["CSI 300 ETF", "Securities ETF"],
                "market": ["E", "E"],
                "fund_type": ["ETF", "ETF"],
                "type": ["ETF", "ETF"],
                "invest_type": ["Passive", "Passive"],
                "status": ["L", "L"],
                "is_etf": [True, True],
                "list_date": [pd.Timestamp("2012-05-28").date(), pd.Timestamp("2013-07-08").date()],
                "delist_date": [pd.NaT, pd.NaT],
                "found_date": [pd.Timestamp("2012-05-28").date(), pd.Timestamp("2013-07-08").date()],
            }
        )


if __name__ == "__main__":
    unittest.main()
