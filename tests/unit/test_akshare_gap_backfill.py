import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.akshare_gap_backfill import run_akshare_gap_backfill
from quant_robot.storage.processed_bars import load_processed_bars


class FakeGapAdapter:
    def __init__(self):
        self.calls = []

    def fetch_ohlcv(self, asset, request):
        self.calls.append((asset.symbol, request.start, request.end))
        if asset.symbol == "510300.SH":
            return pd.DataFrame(
                {
                    "date": ["2024-01-03"],
                    "open": [3.0],
                    "high": [3.2],
                    "low": [2.9],
                    "close": [3.1],
                    "adj_close": [3.1],
                    "volume": [10000],
                    "amount": [31000.0],
                }
            )
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "adj_close", "volume", "amount"])


class AkshareGapBackfillTests(unittest.TestCase):
    def test_backfill_merges_provider_rows_and_records_empty_provider_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed_root = root / "processed"
            output_dir = root / "report"
            gap_rows = [
                {"gap_id": "DG-CN_ETF_XSHG_510300-20240103", "symbol": "510300.SH", "missing_date": "2024-01-03"},
                {"gap_id": "DG-CN_ETF_XSHG_510500-20240104", "symbol": "510500.SH", "missing_date": "2024-01-04"},
            ]

            report = run_akshare_gap_backfill(
                gap_rows=gap_rows,
                processed_root=processed_root,
                output_dir=output_dir,
                adapter=FakeGapAdapter(),
            )

            self.assertEqual(report["summary"]["gap_rows"], 2)
            self.assertEqual(report["summary"]["resolved_with_provider"], 1)
            self.assertEqual(report["summary"]["no_target_row_from_provider"], 1)
            self.assertTrue((output_dir / "akshare_gap_backfill_report.json").exists())
            self.assertTrue((output_dir / "akshare_gap_backfill_rows.csv").exists())
            processed = load_processed_bars(processed_root, "CN_ETF")
            self.assertEqual(processed.loc[0, "asset_id"], "CN_ETF_XSHG_510300")
            self.assertEqual(str(pd.to_datetime(processed.loc[0, "date"]).date()), "2024-01-03")


if __name__ == "__main__":
    unittest.main()
