import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.ingest.tushare_pipeline import run_tushare_daily_ingest


class FakeTushareDailyAdapter:
    def __init__(self) -> None:
        self.calls = []

    def fetch_trade_calendar(self, start_date: str, end_date: str):
        return pd.DataFrame(
            {
                "exchange": ["SSE", "SSE"],
                "date": [pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-01-03").date()],
                "is_open": [1, 1],
            }
        )

    def fetch_daily_by_trade_date(self, trade_date: str):
        self.calls.append(trade_date)
        return pd.DataFrame(
            {
                "symbol": ["000001.SZ"],
                "date": [pd.to_datetime(trade_date, format="%Y%m%d").date()],
                "open": [10.0],
                "high": [11.0],
                "low": [9.5],
                "close": [10.5],
                "volume": [10000.0],
                "amount": [200000.0],
            }
        )


class TushareIngestPipelineTests(unittest.TestCase):
    def test_pipeline_writes_raw_processed_manifest_and_quality_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeTushareDailyAdapter()

            result = run_tushare_daily_ingest(adapter, "2024-01-02", "2024-01-03", Path(tmp))

            self.assertEqual(adapter.calls, ["20240102", "20240103"])
            self.assertEqual(result["downloaded_trade_dates"], ["20240102", "20240103"])
            self.assertTrue((Path(tmp) / "manifest.json").exists())
            self.assertTrue((Path(tmp) / "quality_report.json").exists())
            self.assertGreater(result["processed_rows"], 0)

    def test_pipeline_resume_skips_completed_trade_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeTushareDailyAdapter()
            run_tushare_daily_ingest(adapter, "2024-01-02", "2024-01-03", Path(tmp))

            second_adapter = FakeTushareDailyAdapter()
            result = run_tushare_daily_ingest(second_adapter, "2024-01-02", "2024-01-03", Path(tmp), resume=True)

            self.assertEqual(second_adapter.calls, [])
            self.assertEqual(result["skipped_trade_dates"], ["20240102", "20240103"])
            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("daily:20240102", manifest["completed"])


if __name__ == "__main__":
    unittest.main()
