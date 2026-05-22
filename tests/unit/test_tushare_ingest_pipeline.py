import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.ingest.tushare_pipeline import run_tushare_daily_ingest
from quant_robot.data.ingest.tushare_pipeline import _asset_from_tushare_symbol


class FakeTushareDailyAdapter:
    def __init__(self) -> None:
        self.calls = []

    def fetch_trade_calendar(self, start_date: str, end_date: str):
        dates = pd.date_range(start_date, end_date, freq="D")
        return pd.DataFrame(
            {
                "exchange": ["SSE"] * len(dates),
                "date": dates.date,
                "is_open": [1] * len(dates),
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


class FakeTushareAdjustedAdapter(FakeTushareDailyAdapter):
    def fetch_adj_factor(self, ts_code: str = "", start_date: str = "", end_date: str = ""):
        return pd.DataFrame(
            {
                "symbol": ["000001.SZ", "000001.SZ"],
                "date": [pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-01-03").date()],
                "adj_factor": [1.0, 2.0],
            }
        )


class FakeInvalidTushareDailyAdapter(FakeTushareDailyAdapter):
    def fetch_daily_by_trade_date(self, trade_date: str):
        self.calls.append(trade_date)
        return pd.DataFrame(
            {
                "symbol": ["000001.SZ"],
                "date": [pd.to_datetime(trade_date, format="%Y%m%d").date()],
                "open": [10.0],
                "high": [11.0],
                "low": [9.5],
                "close": [-10.5],
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
            self.assertEqual(result["processed_rows"], 2)
            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("daily:20240102", manifest["completed"])

    def test_pipeline_marks_manifest_completed_only_after_processed_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_tushare_daily_ingest(FakeInvalidTushareDailyAdapter(), "2024-01-02", "2024-01-02", Path(tmp))

            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn("daily:20240102", manifest["completed"])
            self.assertIn("daily:20240102", manifest["failed"])

    def test_incremental_run_preserves_existing_processed_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_tushare_daily_ingest(FakeTushareDailyAdapter(), "2024-01-02", "2024-01-03", Path(tmp))
            run_tushare_daily_ingest(FakeTushareDailyAdapter(), "2024-01-02", "2024-01-04", Path(tmp))

            processed_file = (
                Path(tmp)
                / "processed"
                / "bars"
                / "frequency=1d"
                / "market=CN"
                / "year=2024"
                / "part-00000.csv"
            )
            processed = pd.read_csv(processed_file)

            self.assertEqual(len(processed), 3)
            self.assertEqual(sorted(processed["date"].unique().tolist()), ["2024-01-02", "2024-01-03", "2024-01-04"])

    def test_pipeline_applies_forward_adjusted_close_when_adj_factor_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_daily_ingest(FakeTushareAdjustedAdapter(), "2024-01-02", "2024-01-03", Path(tmp))
            processed_file = (
                Path(tmp)
                / "processed"
                / "bars"
                / "frequency=1d"
                / "market=CN"
                / "year=2024"
                / "part-00000.csv"
            )
            processed = pd.read_csv(processed_file).sort_values("date").reset_index(drop=True)

            self.assertTrue(result["adjusted"])
            self.assertAlmostEqual(processed.loc[0, "adj_close"], 10.5)
            self.assertAlmostEqual(processed.loc[1, "adj_close"], 21.0)

    def test_adjusted_close_is_stable_across_different_ingest_ranges(self):
        class ThreeDayAdjustedAdapter(FakeTushareDailyAdapter):
            def fetch_adj_factor(self, ts_code: str = "", start_date: str = "", end_date: str = ""):
                return pd.DataFrame(
                    {
                        "symbol": ["000001.SZ", "000001.SZ", "000001.SZ"],
                        "date": [
                            pd.Timestamp("2024-01-02").date(),
                            pd.Timestamp("2024-01-03").date(),
                            pd.Timestamp("2024-01-04").date(),
                        ],
                        "adj_factor": [1.0, 2.0, 4.0],
                    }
                )

        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            run_tushare_daily_ingest(ThreeDayAdjustedAdapter(), "2024-01-02", "2024-01-03", Path(first))
            run_tushare_daily_ingest(ThreeDayAdjustedAdapter(), "2024-01-02", "2024-01-04", Path(second))

            first_processed = pd.read_csv(
                Path(first) / "processed" / "bars" / "frequency=1d" / "market=CN" / "year=2024" / "part-00000.csv"
            )
            second_processed = pd.read_csv(
                Path(second) / "processed" / "bars" / "frequency=1d" / "market=CN" / "year=2024" / "part-00000.csv"
            )
            first_jan2 = first_processed[first_processed["date"] == "2024-01-02"].iloc[0]["adj_close"]
            second_jan2 = second_processed[second_processed["date"] == "2024-01-02"].iloc[0]["adj_close"]

            self.assertAlmostEqual(first_jan2, second_jan2)

    def test_asset_from_tushare_symbol_supports_beijing_exchange(self):
        asset = _asset_from_tushare_symbol("430047.BJ")

        self.assertEqual(asset.exchange, "XBEI")
        self.assertEqual(asset.asset_id, "CN_XBEI_430047")


if __name__ == "__main__":
    unittest.main()
