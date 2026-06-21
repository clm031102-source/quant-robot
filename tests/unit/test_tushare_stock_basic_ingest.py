import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from scripts.ingest_tushare_stock_basic import run_tushare_stock_basic_ingest


class TushareStockBasicIngestTests(unittest.TestCase):
    def test_ingest_writes_stock_basic_snapshot_for_industry_research(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = _FakeStockBasicAdapter()

            result = run_tushare_stock_basic_ingest(adapter, root, list_status="L", snapshot="2026-06-21")

            self.assertEqual(result["rows"], 2)
            self.assertEqual(result["snapshot"], "2026-06-21")
            self.assertEqual(result["list_status"], "L")
            stored = DatasetStore(root).read_frame(
                "metadata/tushare_stock_basic",
                {"list_status": "L", "snapshot": "2026-06-21"},
            )
            self.assertEqual(set(stored["symbol"]), {"000001.SZ", "600000.SH"})
            self.assertEqual(set(stored["industry"]), {"银行"})
            self.assertEqual(adapter.calls, [("fetch_stock_basic", "L")])


class _FakeStockBasicAdapter:
    def __init__(self) -> None:
        self.calls = []

    def fetch_stock_basic(self, list_status: str = "L") -> pd.DataFrame:
        self.calls.append(("fetch_stock_basic", list_status))
        return pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001", "CN_XSHG_600000"],
                "symbol": ["000001.SZ", "600000.SH"],
                "market": ["CN", "CN"],
                "exchange": ["XSHE", "XSHG"],
                "asset_type": ["stock", "stock"],
                "currency": ["CNY", "CNY"],
                "timezone": ["Asia/Shanghai", "Asia/Shanghai"],
                "calendar": ["XSHE", "XSHG"],
                "name": ["Ping An Bank", "SPD Bank"],
                "is_active": [True, True],
                "area": ["深圳", "上海"],
                "industry": ["银行", "银行"],
                "stock_market": ["主板", "主板"],
                "list_date": [pd.Timestamp("1991-04-03").date(), pd.Timestamp("1999-11-10").date()],
                "delist_date": [pd.NaT, pd.NaT],
                "is_hs": ["S", "H"],
            }
        )


if __name__ == "__main__":
    unittest.main()
