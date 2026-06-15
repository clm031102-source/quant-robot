import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.ingest.tushare_moneyflow_inputs import run_tushare_moneyflow_ingest
from quant_robot.storage.dataset_store import DatasetStore


class FakeTushareMoneyflowAdapter:
    def __init__(self) -> None:
        self.calls = []

    def fetch_trade_calendar(self, start_date: str, end_date: str):
        dates = pd.date_range(start_date, end_date, freq="D")
        return pd.DataFrame({"exchange": ["SSE"] * len(dates), "date": dates.date, "is_open": [1] * len(dates)})

    def fetch_moneyflow_by_trade_date(self, trade_date: str):
        self.calls.append(trade_date)
        date = pd.to_datetime(trade_date, format="%Y%m%d").date()
        return pd.DataFrame(
            {
                "symbol": ["000001.SZ", "600519.SH"],
                "date": [date, date],
                "buy_sm_vol": [10.0, 11.0],
                "buy_sm_amount": [100.0, 110.0],
                "sell_sm_vol": [8.0, 9.0],
                "sell_sm_amount": [80.0, 90.0],
                "buy_md_vol": [30.0, 31.0],
                "buy_md_amount": [300.0, 310.0],
                "sell_md_vol": [25.0, 26.0],
                "sell_md_amount": [250.0, 260.0],
                "buy_lg_vol": [50.0, 51.0],
                "buy_lg_amount": [500.0, 510.0],
                "sell_lg_vol": [45.0, 46.0],
                "sell_lg_amount": [450.0, 460.0],
                "buy_elg_vol": [70.0, 71.0],
                "buy_elg_amount": [700.0, 710.0],
                "sell_elg_vol": [65.0, 66.0],
                "sell_elg_amount": [650.0, 660.0],
                "net_mf_vol": [12.0, 13.0],
                "net_mf_amount": [120.0, 130.0],
            }
        )


class FakeInvalidMoneyflowAdapter(FakeTushareMoneyflowAdapter):
    def fetch_moneyflow_by_trade_date(self, trade_date: str):
        self.calls.append(trade_date)
        return pd.DataFrame({"symbol": ["BAD"], "date": [pd.Timestamp("2024-01-02").date()]})


class FakeMissingMoneyflowAdapter(FakeTushareMoneyflowAdapter):
    def fetch_moneyflow_by_trade_date(self, trade_date: str):
        frame = super().fetch_moneyflow_by_trade_date(trade_date)
        frame.loc[0, "net_mf_amount"] = pd.NA
        return frame


class TushareMoneyflowInputsIngestTests(unittest.TestCase):
    def test_moneyflow_ingest_writes_raw_processed_manifest_and_quality_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeTushareMoneyflowAdapter()

            result = run_tushare_moneyflow_ingest(adapter, "2024-01-02", "2024-01-03", Path(tmp))

            self.assertEqual(adapter.calls, ["20240102", "20240103"])
            self.assertEqual(result["source"], "tushare")
            self.assertEqual(result["dataset"], "moneyflow")
            self.assertEqual(result["processed_rows"], 4)
            self.assertTrue((Path(tmp) / "manifest.json").exists())
            self.assertTrue((Path(tmp) / "moneyflow_input_quality_report.json").exists())
            processed = DatasetStore(Path(tmp)).read_frame(
                "processed/moneyflow_inputs",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            self.assertEqual(set(processed["asset_id"]), {"CN_XSHE_000001", "CN_XSHG_600519"})
            self.assertEqual(set(processed["source"]), {"tushare_moneyflow"})
            self.assertIn("net_mf_amount", processed.columns)

    def test_moneyflow_quality_report_tracks_missing_numeric_by_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_moneyflow_ingest(FakeMissingMoneyflowAdapter(), "2024-01-02", "2024-01-02", Path(tmp))

            self.assertEqual(result["quality_report"]["missing_numeric_rows"], 1)
            self.assertEqual(result["quality_report"]["missing_numeric_by_column"], {"net_mf_amount": 1})

    def test_moneyflow_ingest_resume_skips_completed_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_tushare_moneyflow_ingest(FakeTushareMoneyflowAdapter(), "2024-01-02", "2024-01-03", Path(tmp))
            second_adapter = FakeTushareMoneyflowAdapter()

            result = run_tushare_moneyflow_ingest(second_adapter, "2024-01-02", "2024-01-03", Path(tmp), resume=True)

            self.assertEqual(second_adapter.calls, [])
            self.assertEqual(result["skipped_trade_dates"], ["20240102", "20240103"])
            self.assertEqual(result["processed_rows"], 4)
            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("moneyflow:20240102", manifest["completed"])

    def test_moneyflow_ingest_marks_failed_when_processing_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_tushare_moneyflow_ingest(FakeInvalidMoneyflowAdapter(), "2024-01-02", "2024-01-02", Path(tmp))

            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn("moneyflow:20240102", manifest["completed"])
            self.assertIn("moneyflow:20240102", manifest["failed"])


if __name__ == "__main__":
    unittest.main()
