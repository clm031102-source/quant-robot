import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.ingest.tushare_external_feeds import run_tushare_external_feed_ingest
from quant_robot.storage.dataset_store import DatasetStore


class FakeTushareExternalFeedAdapter:
    def __init__(self, raise_on_lpr: bool = False) -> None:
        self.raise_on_lpr = raise_on_lpr
        self.margin_calls: list[str] = []
        self.hk_hold_calls: list[str] = []
        self.hsgt_calls: list[str] = []
        self.shibor_calls: list[str] = []
        self.lpr_calls = 0

    def fetch_trade_calendar(self, start_date: str, end_date: str):
        dates = pd.date_range("2024-01-02", "2024-01-08", freq="B")
        return pd.DataFrame({"exchange": ["SSE"] * len(dates), "date": dates.date, "is_open": [1] * len(dates)})

    def fetch_margin_detail_by_trade_date(self, trade_date: str):
        self.margin_calls.append(trade_date)
        return pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "trade_date": [trade_date],
                "rzye": [100.0],
                "rqye": [10.0],
                "rzmre": [5.0],
                "rqyl": [2.0],
                "rzche": [3.0],
                "rqchl": [1.0],
                "rqmcl": [0.5],
                "rzrqye": [110.0],
            }
        )

    def fetch_hk_hold_by_trade_date(self, trade_date: str):
        self.hk_hold_calls.append(trade_date)
        return pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "trade_date": [trade_date],
                "vol": [2000.0],
                "ratio": [2.5],
                "exchange": ["SH"],
            }
        )

    def fetch_moneyflow_hsgt_by_trade_date(self, trade_date: str):
        self.hsgt_calls.append(trade_date)
        return pd.DataFrame(
            {
                "trade_date": [trade_date],
                "hgt": [1.0],
                "sgt": [2.0],
                "north_money": [3.0],
                "south_money": [4.0],
            }
        )

    def fetch_index_daily(self, ts_code: str, start_date: str, end_date: str):
        return pd.DataFrame(
            {
                "ts_code": [ts_code, ts_code],
                "trade_date": ["20240102", "20240103"],
                "close": [3000.0, 3010.0],
                "pct_chg": [0.1, 0.2],
                "amount": [100000.0, 110000.0],
            }
        )

    def fetch_index_dailybasic(self, ts_code: str, start_date: str, end_date: str):
        return pd.DataFrame(
            {
                "ts_code": [ts_code, ts_code],
                "trade_date": ["20240102", "20240103"],
                "turnover_rate": [0.8, 0.9],
                "turnover_rate_f": [0.7, 0.8],
                "pe": [12.0, 12.1],
                "pe_ttm": [11.5, 11.6],
                "pb": [1.2, 1.3],
            }
        )

    def fetch_shibor_by_date(self, date: str):
        self.shibor_calls.append(date)
        return pd.DataFrame(
            {
                "date": [date],
                "on": [1.0],
                "1w": [1.1],
                "1m": [1.2],
                "3m": [1.3],
                "1y": [1.8],
            }
        )

    def fetch_shibor_lpr(self):
        self.lpr_calls += 1
        if self.raise_on_lpr:
            raise RuntimeError("rate limit")
        return pd.DataFrame({"date": ["20240101"], "1y": [3.45], "5y": [3.95]})


class FakeShortCalendarExternalFeedAdapter(FakeTushareExternalFeedAdapter):
    def fetch_trade_calendar(self, start_date: str, end_date: str):
        dates = pd.date_range("2024-01-02", "2024-01-03", freq="B")
        return pd.DataFrame({"exchange": ["SSE"] * len(dates), "date": dates.date, "is_open": [1] * len(dates)})


class FakeFlakyCalendarExternalFeedAdapter(FakeTushareExternalFeedAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.calendar_calls = 0

    def fetch_trade_calendar(self, start_date: str, end_date: str):
        self.calendar_calls += 1
        if self.calendar_calls == 1:
            return pd.DataFrame(columns=["exchange", "date", "is_open"])
        return super().fetch_trade_calendar(start_date, end_date)


class FakeMixedHkHoldExternalFeedAdapter(FakeTushareExternalFeedAdapter):
    def fetch_hk_hold_by_trade_date(self, trade_date: str):
        self.hk_hold_calls.append(trade_date)
        return pd.DataFrame(
            {
                "ts_code": ["000001.SZ", "00001.HK"],
                "trade_date": [trade_date, trade_date],
                "vol": [2000.0, 3000.0],
                "ratio": [2.5, 3.5],
                "exchange": ["SH", "HK"],
            }
        )


class TushareExternalFeedIngestTests(unittest.TestCase):
    def test_report_only_ingest_adds_availability_lag_and_writes_no_processed_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeTushareExternalFeedAdapter()

            result = run_tushare_external_feed_ingest(adapter, "2024-01-02", "2024-01-03", Path(tmp))

            self.assertFalse(result["processed_writes_enabled"])
            self.assertFalse((Path(tmp) / "processed").exists())
            self.assertTrue((Path(tmp) / "external_feed_ingestion_report.json").exists())
            self.assertEqual(result["summary"]["feed_count"], 5)
            self.assertEqual(result["summary"]["fail_count"], 0)
            margin_quality = result["feed_quality"]["external_margin_detail"]
            self.assertEqual(margin_quality["rows"], 2)
            self.assertEqual(margin_quality["duplicate_key_count"], 0)
            self.assertEqual(margin_quality["lag_violation_count"], 0)
            self.assertEqual(margin_quality["date_min"], "2024-01-02")
            self.assertEqual(margin_quality["available_date_min"], "2024-01-03")

    def test_execute_write_processed_writes_year_partitions_with_available_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeTushareExternalFeedAdapter()

            result = run_tushare_external_feed_ingest(
                adapter,
                "2024-01-02",
                "2024-01-03",
                Path(tmp),
                execute_write_processed=True,
            )

            self.assertTrue(result["processed_writes_enabled"])
            store = DatasetStore(Path(tmp))
            margin = store.read_frame(
                "processed/external_margin_detail",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            self.assertTrue((pd.to_datetime(margin["available_date"]) > pd.to_datetime(margin["date"])).all())
            macro = store.read_frame(
                "processed/external_macro_rates",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            self.assertEqual(macro["lpr_1y"].notna().sum(), 2)
            self.assertEqual(macro["lpr_5y"].notna().sum(), 2)

    def test_lpr_cache_prevents_second_lpr_endpoint_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            first_adapter = FakeTushareExternalFeedAdapter()
            run_tushare_external_feed_ingest(first_adapter, "2024-01-02", "2024-01-03", Path(tmp))
            self.assertEqual(first_adapter.lpr_calls, 1)

            second_adapter = FakeTushareExternalFeedAdapter(raise_on_lpr=True)
            result = run_tushare_external_feed_ingest(second_adapter, "2024-01-02", "2024-01-03", Path(tmp))

            self.assertEqual(second_adapter.lpr_calls, 0)
            self.assertEqual(result["feed_quality"]["external_macro_rates"]["status"], "pass")
            cached = json.loads((Path(tmp) / "external_lpr_cache.json").read_text(encoding="utf-8"))
            self.assertEqual(cached["rows"][0]["lpr_1y"], 3.45)

    def test_empty_lpr_cache_is_refreshed_instead_of_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "external_lpr_cache.json"
            cache_path.write_text(json.dumps({"rows": []}), encoding="utf-8")
            adapter = FakeTushareExternalFeedAdapter()

            result = run_tushare_external_feed_ingest(adapter, "2024-01-02", "2024-01-03", Path(tmp))

            self.assertEqual(adapter.lpr_calls, 1)
            self.assertEqual(result["feed_quality"]["external_macro_rates"]["status"], "pass")
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            self.assertEqual(cached["rows"][0]["lpr_1y"], 3.45)

    def test_missing_next_trade_date_is_a_quality_failure_not_silent_signal_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_external_feed_ingest(
                FakeShortCalendarExternalFeedAdapter(),
                "2024-01-03",
                "2024-01-03",
                Path(tmp),
            )

            margin_quality = result["feed_quality"]["external_margin_detail"]
            self.assertEqual(margin_quality["status"], "fail")
            self.assertEqual(margin_quality["missing_available_date_count"], 1)
            self.assertEqual(result["summary"]["fail_count"], 5)

    def test_hk_hold_drops_non_cn_stock_symbols_for_cn_stock_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_external_feed_ingest(
                FakeMixedHkHoldExternalFeedAdapter(),
                "2024-01-02",
                "2024-01-02",
                Path(tmp),
            )

            hk_hold_quality = result["feed_quality"]["external_hk_hold"]
            self.assertEqual(hk_hold_quality["status"], "pass")
            self.assertEqual(hk_hold_quality["rows"], 1)
            self.assertEqual(hk_hold_quality["dropped_non_cn_symbol_count"], 1)

    def test_retries_transient_empty_trade_calendar_response_before_failing_shard(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeFlakyCalendarExternalFeedAdapter()

            result = run_tushare_external_feed_ingest(adapter, "2024-01-02", "2024-01-03", Path(tmp))

            self.assertEqual(adapter.calendar_calls, 2)
            self.assertEqual(result["summary"]["fail_count"], 0)

    def test_progress_callback_records_per_endpoint_date_start_and_done_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            events: list[dict[str, object]] = []

            run_tushare_external_feed_ingest(
                FakeTushareExternalFeedAdapter(),
                "2024-01-02",
                "2024-01-03",
                Path(tmp),
                progress_callback=events.append,
            )

            margin_start = [
                event
                for event in events
                if event["endpoint"] == "margin_detail"
                and event["trade_date"] == "20240102"
                and event["status"] == "start"
            ]
            margin_done = [
                event
                for event in events
                if event["endpoint"] == "margin_detail"
                and event["trade_date"] == "20240102"
                and event["status"] == "done"
            ]
            self.assertEqual(len(margin_start), 1)
            self.assertEqual(len(margin_done), 1)
            self.assertEqual(margin_done[0]["rows"], 1)


if __name__ == "__main__":
    unittest.main()
