import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.cn_etf_theme_map import load_cn_etf_theme_map
from quant_robot.storage.cn_etf_peer_mapping import load_cn_etf_peer_mapping
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
            peer_mapping = load_cn_etf_peer_mapping(root)
            self.assertEqual(len(peer_mapping), 2)
            self.assertEqual(peer_mapping["peer_id"].nunique(), 1)
            self.assertEqual(set(peer_mapping["known_from"].astype(str)), {"2026-06-21"})
            self.assertEqual(result["peer_mapping_rows"], 2)
            self.assertEqual(adapter.calls, [("fetch_fund_basic", "E")])

    def test_empty_provider_response_is_rejected_without_writing_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "returned no rows"):
                run_tushare_fund_basic_ingest(
                    _EmptyFundBasicAdapter(),
                    tmp,
                    market="E",
                    snapshot="2026-06-21",
                )

            self.assertFalse((Path(tmp) / "metadata").exists())


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
                "benchmark": ["CSI 300 Index Return × 100%", "CSI 300 Index Return×100%"],
                "list_date": [pd.Timestamp("2012-05-28").date(), pd.Timestamp("2013-07-08").date()],
                "delist_date": [pd.NaT, pd.NaT],
                "found_date": [pd.Timestamp("2012-05-28").date(), pd.Timestamp("2013-07-08").date()],
            }
        )


class _EmptyFundBasicAdapter:
    def fetch_fund_basic(self, market: str = "E") -> pd.DataFrame:
        return pd.DataFrame()


if __name__ == "__main__":
    unittest.main()
