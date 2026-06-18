import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.ingest.tushare_pipeline import run_tushare_daily_ingest
from quant_robot.data.ingest.tushare_pipeline import _asset_from_tushare_symbol
from quant_robot.storage.dataset_store import DatasetStore


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

    def fetch_etf_daily_by_trade_date(self, trade_date: str):
        self.calls.append(f"etf:{trade_date}")
        return pd.DataFrame(
            {
                "symbol": ["510300.SH"],
                "date": [pd.to_datetime(trade_date, format="%Y%m%d").date()],
                "open": [4.0],
                "high": [4.1],
                "low": [3.9],
                "close": [4.05],
                "volume": [100000.0],
                "amount": [405000.0],
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


class FakeEmptyTushareDailyAdapter(FakeTushareDailyAdapter):
    def fetch_daily_by_trade_date(self, trade_date: str):
        self.calls.append(trade_date)
        return pd.DataFrame(columns=["symbol", "date", "open", "high", "low", "close", "volume", "amount"])


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

    def test_pipeline_refetches_completed_trade_date_when_raw_partition_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DatasetStore(Path(tmp))
            store.write_frame(
                pd.DataFrame(columns=["symbol", "date", "open", "high", "low", "close", "volume", "amount"]),
                "raw/tushare/daily",
                {"trade_date": "20240102"},
            )
            (Path(tmp) / "manifest.json").write_text(
                json.dumps({"completed": {"daily:20240102": {"rows": 0}}, "failed": {}, "metadata": {}}),
                encoding="utf-8",
            )

            adapter = FakeTushareDailyAdapter()
            result = run_tushare_daily_ingest(adapter, "2024-01-02", "2024-01-02", Path(tmp), resume=True)

            self.assertEqual(adapter.calls, ["20240102"])
            self.assertEqual(result["downloaded_trade_dates"], ["20240102"])
            self.assertEqual(result["skipped_trade_dates"], [])
            self.assertEqual(result["processed_rows"], 1)
            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["completed"]["daily:20240102"]["rows"], 1)

    def test_pipeline_rejects_empty_raw_response_for_open_trade_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "empty raw response"):
                run_tushare_daily_ingest(FakeEmptyTushareDailyAdapter(), "2024-01-02", "2024-01-02", Path(tmp))

            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn("daily:20240102", manifest["completed"])
            self.assertIn("daily:20240102", manifest["failed"])

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

            processed = _read_processed_bars(Path(tmp), "CN", "2024")

            self.assertEqual(len(processed), 3)
            self.assertEqual(sorted(processed["date"].unique().tolist()), ["2024-01-02", "2024-01-03", "2024-01-04"])

    def test_pipeline_applies_forward_adjusted_close_when_adj_factor_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_daily_ingest(FakeTushareAdjustedAdapter(), "2024-01-02", "2024-01-03", Path(tmp))
            processed = _read_processed_bars(Path(tmp), "CN", "2024").sort_values("date").reset_index(drop=True)

            self.assertTrue(result["adjusted"])
            self.assertEqual(result["adjustment_report"]["status"], "applied")
            self.assertAlmostEqual(result["adjustment_report"]["coverage"], 1.0)
            self.assertAlmostEqual(processed.loc[0, "adj_close"], 10.5)
            self.assertAlmostEqual(processed.loc[1, "adj_close"], 21.0)

    def test_pipeline_skips_adjusted_close_when_adj_factor_coverage_is_partial(self):
        class PartialAdjustedAdapter(FakeTushareDailyAdapter):
            def fetch_adj_factor(self, ts_code: str = "", start_date: str = "", end_date: str = ""):
                return pd.DataFrame(
                    {
                        "symbol": ["000001.SZ"],
                        "date": [pd.Timestamp("2024-01-02").date()],
                        "adj_factor": [2.0],
                    }
                )

        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_daily_ingest(PartialAdjustedAdapter(), "2024-01-02", "2024-01-03", Path(tmp))
            processed = _read_processed_bars(Path(tmp), "CN", "2024").sort_values("date").reset_index(drop=True)

            self.assertFalse(result["adjusted"])
            self.assertEqual(result["adjustment_report"]["status"], "partial_adj_factor_coverage")
            self.assertEqual(result["adjustment_report"]["missing_rows"], 1)
            self.assertAlmostEqual(result["adjustment_report"]["coverage"], 0.5)
            self.assertAlmostEqual(processed.loc[0, "adj_close"], processed.loc[0, "close"])
            self.assertAlmostEqual(processed.loc[1, "adj_close"], processed.loc[1, "close"])

    def test_pipeline_falls_back_to_trade_date_adj_factor_when_range_coverage_is_partial(self):
        class FallbackAdjustedAdapter(FakeTushareDailyAdapter):
            def fetch_adj_factor(self, ts_code: str = "", start_date: str = "", end_date: str = ""):
                return pd.DataFrame(
                    {
                        "symbol": ["000001.SZ"],
                        "date": [pd.Timestamp("2024-01-02").date()],
                        "adj_factor": [2.0],
                    }
                )

            def fetch_adj_factor_by_trade_date(self, trade_date: str):
                date = pd.to_datetime(trade_date, format="%Y%m%d").date()
                factor = 2.0 if trade_date == "20240102" else 3.0
                return pd.DataFrame(
                    {
                        "symbol": ["000001.SZ"],
                        "date": [date],
                        "adj_factor": [factor],
                    }
                )

        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_daily_ingest(FallbackAdjustedAdapter(), "2024-01-02", "2024-01-03", Path(tmp))
            processed = _read_processed_bars(Path(tmp), "CN", "2024").sort_values("date").reset_index(drop=True)

            self.assertTrue(result["adjusted"])
            self.assertEqual(result["adjustment_report"]["status"], "applied")
            self.assertTrue(result["adjustment_report"]["fallback_used"])
            self.assertEqual(result["adjustment_report"]["range_factor_rows"], 1)
            self.assertEqual(result["adjustment_report"]["fallback_factor_rows"], 2)
            self.assertAlmostEqual(result["adjustment_report"]["coverage"], 1.0)
            self.assertAlmostEqual(processed.loc[0, "adj_close"], processed.loc[0, "close"] * 2.0)
            self.assertAlmostEqual(processed.loc[1, "adj_close"], processed.loc[1, "close"] * 3.0)

    def test_pipeline_falls_back_to_trade_date_adj_factor_when_range_response_is_empty(self):
        class EmptyRangeFallbackAdjustedAdapter(FakeTushareDailyAdapter):
            def fetch_adj_factor(self, ts_code: str = "", start_date: str = "", end_date: str = ""):
                return pd.DataFrame(columns=["symbol", "date", "adj_factor"])

            def fetch_adj_factor_by_trade_date(self, trade_date: str):
                date = pd.to_datetime(trade_date, format="%Y%m%d").date()
                factor = 2.0 if trade_date == "20240102" else 3.0
                return pd.DataFrame(
                    {
                        "symbol": ["000001.SZ"],
                        "date": [date],
                        "adj_factor": [factor],
                    }
                )

        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_daily_ingest(EmptyRangeFallbackAdjustedAdapter(), "2024-01-02", "2024-01-03", Path(tmp))
            processed = _read_processed_bars(Path(tmp), "CN", "2024").sort_values("date").reset_index(drop=True)

            self.assertTrue(result["adjusted"])
            self.assertEqual(result["adjustment_report"]["status"], "applied")
            self.assertTrue(result["adjustment_report"]["fallback_used"])
            self.assertEqual(result["adjustment_report"]["range_factor_rows"], 0)
            self.assertEqual(result["adjustment_report"]["fallback_factor_rows"], 2)
            self.assertAlmostEqual(processed.loc[0, "adj_close"], processed.loc[0, "close"] * 2.0)
            self.assertAlmostEqual(processed.loc[1, "adj_close"], processed.loc[1, "close"] * 3.0)

    def test_trade_date_adj_factor_fallback_retries_empty_date_response(self):
        class RetryEmptyFallbackAdjustedAdapter(FakeTushareDailyAdapter):
            def __init__(self) -> None:
                super().__init__()
                self.factor_calls_by_date = {}

            def fetch_adj_factor(self, ts_code: str = "", start_date: str = "", end_date: str = ""):
                return pd.DataFrame(columns=["symbol", "date", "adj_factor"])

            def fetch_adj_factor_by_trade_date(self, trade_date: str):
                self.factor_calls_by_date[trade_date] = self.factor_calls_by_date.get(trade_date, 0) + 1
                if trade_date == "20240103" and self.factor_calls_by_date[trade_date] == 1:
                    return pd.DataFrame(columns=["symbol", "date", "adj_factor"])
                date = pd.to_datetime(trade_date, format="%Y%m%d").date()
                factor = 2.0 if trade_date == "20240102" else 3.0
                return pd.DataFrame(
                    {
                        "symbol": ["000001.SZ"],
                        "date": [date],
                        "adj_factor": [factor],
                    }
                )

        with tempfile.TemporaryDirectory() as tmp:
            adapter = RetryEmptyFallbackAdjustedAdapter()
            result = run_tushare_daily_ingest(adapter, "2024-01-02", "2024-01-03", Path(tmp))

            self.assertTrue(result["adjusted"])
            self.assertEqual(adapter.factor_calls_by_date["20240103"], 2)
            self.assertEqual(result["adjustment_report"]["fallback_factor_rows"], 2)

    def test_pipeline_skips_adjusted_close_when_adj_factor_keys_duplicate(self):
        class DuplicateAdjustedAdapter(FakeTushareDailyAdapter):
            def fetch_adj_factor(self, ts_code: str = "", start_date: str = "", end_date: str = ""):
                return pd.DataFrame(
                    {
                        "symbol": ["000001.SZ", "000001.SZ", "000001.SZ"],
                        "date": [
                            pd.Timestamp("2024-01-02").date(),
                            pd.Timestamp("2024-01-02").date(),
                            pd.Timestamp("2024-01-03").date(),
                        ],
                        "adj_factor": [1.0, 1.1, 2.0],
                    }
                )

        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_daily_ingest(DuplicateAdjustedAdapter(), "2024-01-02", "2024-01-03", Path(tmp))
            processed = _read_processed_bars(Path(tmp), "CN", "2024").sort_values("date").reset_index(drop=True)

            self.assertFalse(result["adjusted"])
            self.assertEqual(result["adjustment_report"]["status"], "duplicate_adj_factor_keys")
            self.assertEqual(result["adjustment_report"]["duplicate_factor_keys"], 1)
            self.assertEqual(len(processed), 2)
            self.assertAlmostEqual(processed.loc[0, "adj_close"], processed.loc[0, "close"])
            self.assertAlmostEqual(processed.loc[1, "adj_close"], processed.loc[1, "close"])

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

            first_processed = _read_processed_bars(Path(first), "CN", "2024")
            second_processed = _read_processed_bars(Path(second), "CN", "2024")
            first_jan2 = first_processed[first_processed["date"] == "2024-01-02"].iloc[0]["adj_close"]
            second_jan2 = second_processed[second_processed["date"] == "2024-01-02"].iloc[0]["adj_close"]

            self.assertAlmostEqual(first_jan2, second_jan2)

    def test_asset_from_tushare_symbol_supports_beijing_exchange(self):
        asset = _asset_from_tushare_symbol("430047.BJ")

        self.assertEqual(asset.exchange, "XBEI")
        self.assertEqual(asset.asset_id, "CN_XBEI_430047")

    def test_pipeline_can_ingest_cn_etf_daily_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeTushareDailyAdapter()

            result = run_tushare_daily_ingest(adapter, "2024-01-02", "2024-01-02", Path(tmp), market="CN_ETF")

            processed = _read_processed_bars(Path(tmp), "CN_ETF", "2024")
            self.assertEqual(adapter.calls, ["etf:20240102"])
            self.assertEqual(result["market"], "CN_ETF")
            self.assertEqual(processed.loc[0, "asset_id"], "CN_ETF_XSHG_510300")
            self.assertEqual(processed.loc[0, "asset_type"], "etf")


def _read_processed_bars(root: Path, market: str, year: str) -> pd.DataFrame:
    frame = DatasetStore(root).read_frame(
        "processed/bars",
        {"frequency": "1d", "market": market, "year": year},
    )
    frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
    return frame


if __name__ == "__main__":
    unittest.main()
