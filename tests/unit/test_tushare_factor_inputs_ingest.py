import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.ingest.tushare_factor_inputs import run_tushare_daily_basic_ingest
from quant_robot.storage.dataset_store import DatasetStore


class FakeTushareDailyBasicAdapter:
    def __init__(self) -> None:
        self.calls = []

    def fetch_trade_calendar(self, start_date: str, end_date: str):
        dates = pd.date_range(start_date, end_date, freq="D")
        return pd.DataFrame({"exchange": ["SSE"] * len(dates), "date": dates.date, "is_open": [1] * len(dates)})

    def fetch_daily_basic_by_trade_date(self, trade_date: str):
        self.calls.append(trade_date)
        date = pd.to_datetime(trade_date, format="%Y%m%d").date()
        return pd.DataFrame(
            {
                "symbol": ["000001.SZ", "600519.SH"],
                "date": [date, date],
                "turnover_rate": [1.0, 0.5],
                "turnover_rate_f": [1.2, 0.6],
                "volume_ratio": [1.1, 0.9],
                "pe": [8.0, 30.0],
                "pe_ttm": [7.5, 28.0],
                "pb": [0.8, 10.0],
                "ps": [1.2, 15.0],
                "ps_ttm": [1.1, 14.0],
                "dv_ratio": [3.0, 1.5],
                "dv_ttm": [3.2, 1.6],
                "total_share": [1000.0, 2000.0],
                "float_share": [800.0, 1200.0],
                "free_share": [600.0, 1000.0],
                "total_mv": [120000.0, 300000.0],
                "circ_mv": [90000.0, 200000.0],
            }
        )


class FakeInvalidDailyBasicAdapter(FakeTushareDailyBasicAdapter):
    def fetch_daily_basic_by_trade_date(self, trade_date: str):
        self.calls.append(trade_date)
        return pd.DataFrame({"symbol": ["BAD"], "date": [pd.Timestamp("2024-01-02").date()], "pb": [1.0]})


class TushareFactorInputsIngestTests(unittest.TestCase):
    def test_daily_basic_ingest_writes_raw_processed_manifest_and_quality_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeTushareDailyBasicAdapter()

            result = run_tushare_daily_basic_ingest(adapter, "2024-01-02", "2024-01-03", Path(tmp))

            self.assertEqual(adapter.calls, ["20240102", "20240103"])
            self.assertEqual(result["source"], "tushare")
            self.assertEqual(result["dataset"], "daily_basic")
            self.assertEqual(result["processed_rows"], 4)
            self.assertTrue((Path(tmp) / "manifest.json").exists())
            self.assertTrue((Path(tmp) / "factor_input_quality_report.json").exists())
            processed = DatasetStore(Path(tmp)).read_frame(
                "processed/factor_inputs",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            self.assertEqual(set(processed["asset_id"]), {"CN_XSHE_000001", "CN_XSHG_600519"})
            self.assertEqual(set(processed["source"]), {"tushare"})

    def test_daily_basic_ingest_resume_skips_completed_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_tushare_daily_basic_ingest(FakeTushareDailyBasicAdapter(), "2024-01-02", "2024-01-03", Path(tmp))
            second_adapter = FakeTushareDailyBasicAdapter()

            result = run_tushare_daily_basic_ingest(second_adapter, "2024-01-02", "2024-01-03", Path(tmp), resume=True)

            self.assertEqual(second_adapter.calls, [])
            self.assertEqual(result["skipped_trade_dates"], ["20240102", "20240103"])
            self.assertEqual(result["processed_rows"], 4)
            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("daily_basic:20240102", manifest["completed"])

    def test_daily_basic_ingest_marks_failed_when_processing_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_tushare_daily_basic_ingest(FakeInvalidDailyBasicAdapter(), "2024-01-02", "2024-01-02", Path(tmp))

            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn("daily_basic:20240102", manifest["completed"])
            self.assertIn("daily_basic:20240102", manifest["failed"])


if __name__ == "__main__":
    unittest.main()
