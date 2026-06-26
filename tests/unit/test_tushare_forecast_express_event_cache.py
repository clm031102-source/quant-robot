import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.ingest.tushare_forecast_express_events import (
    run_tushare_forecast_express_event_cache,
)
from quant_robot.storage.dataset_store import DatasetStore


class FakeForecastExpressEventAdapter:
    def __init__(self, short_calendar: bool = False) -> None:
        self.short_calendar = short_calendar
        self.calls: list[tuple[str, str, str]] = []

    def fetch_trade_calendar(self, start_date: str, end_date: str):
        if self.short_calendar:
            dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
        else:
            dates = pd.bdate_range("2024-01-02", "2024-02-09")
        return pd.DataFrame({"date": dates.date, "is_open": [1] * len(dates)})

    def fetch_event_endpoint(self, endpoint: str, **kwargs: object):
        start_date = str(kwargs["start_date"])
        end_date = str(kwargs["end_date"])
        self.calls.append((endpoint, start_date, end_date))
        if endpoint == "forecast":
            return self._forecast_rows(start_date)
        if endpoint == "express":
            return self._express_rows(start_date)
        raise AssertionError(f"unexpected endpoint {endpoint}")

    def _forecast_rows(self, start_date: str) -> pd.DataFrame:
        if start_date == "20240101":
            return pd.DataFrame(
                {
                    "ts_code": ["000001.SZ", "000002.SZ", "000001.SZ"],
                    "ann_date": ["20240102", "20240103", "20240102"],
                    "end_date": ["20240331", "20240331", "20240331"],
                    "p_change_min": [10.0, -5.0, 10.0],
                    "p_change_max": [20.0, 5.0, 20.0],
                    "net_profit_min": [100.0, -30.0, 100.0],
                    "net_profit_max": [120.0, -10.0, 120.0],
                    "type": ["preincrease", "warning", "preincrease"],
                }
            )
        if start_date == "20240201":
            return pd.DataFrame(
                {
                    "ts_code": ["600001.SH"],
                    "ann_date": ["20240201"],
                    "end_date": ["20240630"],
                    "p_change_min": [5.0],
                    "p_change_max": [15.0],
                    "net_profit_min": [50.0],
                    "net_profit_max": [70.0],
                    "type": ["preincrease"],
                }
            )
        return pd.DataFrame()

    def _express_rows(self, start_date: str) -> pd.DataFrame:
        if start_date == "20240101":
            return pd.DataFrame(
                {
                    "ts_code": ["000001.SZ", "000002.SZ"],
                    "ann_date": ["20240103", "20240103"],
                    "end_date": ["20240331", "20240331"],
                    "yoy_net_profit": [12.0, -8.0],
                    "diluted_roe": [3.0, -1.0],
                    "total_revenue": [1000.0, 900.0],
                }
            )
        return pd.DataFrame()


class FakeForecastRangeUnsupportedAdapter(FakeForecastExpressEventAdapter):
    def fetch_event_endpoint(self, endpoint: str, **kwargs: object):
        if endpoint == "forecast" and "start_date" in kwargs:
            raise Exception("ann_date and ts_code require at least one parameter")
        if endpoint == "forecast" and str(kwargs.get("ann_date")) == "20240102":
            self.calls.append((endpoint, str(kwargs["ann_date"]), "ann_date"))
            return pd.DataFrame(
                {
                    "ts_code": ["000001.SZ"],
                    "ann_date": ["20240102"],
                    "end_date": ["20240331"],
                    "p_change_min": [10.0],
                    "p_change_max": [20.0],
                    "net_profit_min": [100.0],
                    "net_profit_max": [120.0],
                }
            )
        if endpoint == "forecast" and "ann_date" in kwargs:
            self.calls.append((endpoint, str(kwargs["ann_date"]), "ann_date"))
            return pd.DataFrame()
        return super().fetch_event_endpoint(endpoint, **kwargs)


class TushareForecastExpressEventCacheTests(unittest.TestCase):
    def test_report_only_cache_audit_fetches_monthly_ranges_and_writes_no_processed_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeForecastExpressEventAdapter()

            result = run_tushare_forecast_express_event_cache(
                adapter,
                "2024-01-02",
                "2024-02-05",
                Path(tmp),
            )

            self.assertFalse(result["processed_writes_enabled"])
            self.assertFalse((Path(tmp) / "processed").exists())
            self.assertEqual(result["summary"]["endpoint_count"], 2)
            self.assertEqual(result["summary"]["fail_count"], 0)
            self.assertIn(("forecast", "20240101", "20240131"), adapter.calls)
            self.assertIn(("forecast", "20240201", "20240205"), adapter.calls)
            self.assertIn(("express", "20240101", "20240131"), adapter.calls)
            self.assertEqual(result["feed_quality"]["event_forecast"]["rows"], 3)
            self.assertEqual(result["feed_quality"]["event_forecast"]["duplicate_key_count"], 0)
            self.assertEqual(result["feed_quality"]["event_forecast"]["missing_available_date_count"], 0)
            self.assertEqual(result["feed_quality"]["event_express"]["rows"], 2)
            self.assertTrue((Path(tmp) / "forecast_express_event_cache_report.json").exists())

    def test_forecast_range_failure_falls_back_to_ann_date_queries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeForecastRangeUnsupportedAdapter()

            result = run_tushare_forecast_express_event_cache(
                adapter,
                "2024-01-02",
                "2024-01-03",
                Path(tmp),
                endpoints=("forecast",),
            )

            self.assertEqual(result["feed_quality"]["event_forecast"]["status"], "pass")
            self.assertEqual(result["feed_quality"]["event_forecast"]["rows"], 1)
            self.assertEqual(result["feed_quality"]["event_forecast"]["fetch_failure_count"], 0)
            self.assertIn(("forecast", "20240102", "ann_date"), adapter.calls)

    def test_execute_write_processed_writes_year_partitions_with_available_dates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_forecast_express_event_cache(
                FakeForecastExpressEventAdapter(),
                "2024-01-02",
                "2024-02-05",
                Path(tmp),
                execute_write_processed=True,
            )

            self.assertTrue(result["processed_writes_enabled"])
            store = DatasetStore(Path(tmp))
            forecast = store.read_frame(
                "processed/event_forecast",
                {"frequency": "event", "market": "CN", "year": "2024"},
            )
            self.assertIn("p_change_mid", forecast.columns)
            self.assertIn("net_profit_mid", forecast.columns)
            self.assertTrue((pd.to_datetime(forecast["available_date"]) > pd.to_datetime(forecast["event_date"])).all())
            express = store.read_frame(
                "processed/event_express",
                {"frequency": "event", "market": "CN", "year": "2024"},
            )
            self.assertIn("yoy_net_profit", express.columns)
            self.assertTrue((pd.to_datetime(express["available_date"]) > pd.to_datetime(express["event_date"])).all())

    def test_missing_next_trade_date_is_a_quality_failure_not_silent_available_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_forecast_express_event_cache(
                FakeForecastExpressEventAdapter(short_calendar=True),
                "2024-01-02",
                "2024-01-03",
                Path(tmp),
                endpoints=("forecast",),
            )

            forecast_quality = result["feed_quality"]["event_forecast"]
            self.assertEqual(forecast_quality["status"], "fail")
            self.assertEqual(forecast_quality["missing_available_date_count"], 1)
            self.assertEqual(result["summary"]["fail_count"], 1)
            report = json.loads((Path(tmp) / "forecast_express_event_cache_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["feed_quality"]["event_forecast"]["status"], "fail")


if __name__ == "__main__":
    unittest.main()
