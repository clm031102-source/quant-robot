import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.ingest.tushare_tradeability_feeds import run_tushare_tradeability_feed_ingest
from quant_robot.storage.dataset_store import DatasetStore


class FakeTushareTradeabilityAdapter:
    def __init__(self) -> None:
        self.limit_calls: list[str] = []
        self.suspend_calls: list[str] = []
        self.stock_status_calls: list[str] = []
        self.namechange_calls: list[tuple[str, str]] = []

    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        dates = pd.date_range("2024-01-02", "2024-01-08", freq="B")
        return pd.DataFrame({"exchange": ["SSE"] * len(dates), "date": dates.date, "is_open": [1] * len(dates)})

    def fetch_stk_limit_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        self.limit_calls.append(trade_date)
        return pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "trade_date": [trade_date],
                "up_limit": [11.0],
                "down_limit": [9.0],
            }
        )

    def fetch_suspend_d_by_date(self, trade_date: str) -> pd.DataFrame:
        self.suspend_calls.append(trade_date)
        return pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "trade_date": [trade_date],
                "suspend_timing": ["09:30"],
                "suspend_type": ["S"],
            }
        )

    def fetch_namechange(self, start_date: str, end_date: str) -> pd.DataFrame:
        self.namechange_calls.append((start_date, end_date))
        return pd.DataFrame(
            {
                "ts_code": ["000001.SZ", "000002.SZ"],
                "name": ["Ping An Bank", "*ST Sample"],
                "start_date": ["20240102", "20240103"],
                "end_date": ["20240104", None],
                "ann_date": ["20240102", "20240103"],
                "change_reason": ["rename", "special treatment"],
            }
        )

    def fetch_stock_basic(self, list_status: str = "L") -> pd.DataFrame:
        self.stock_status_calls.append(list_status)
        return pd.DataFrame(
            {
                "asset_id": [f"CN_XSHE_00000{len(self.stock_status_calls)}"],
                "symbol": [f"00000{len(self.stock_status_calls)}.SZ"],
                "market": ["CN"],
                "exchange": ["XSHE"],
                "asset_type": ["stock"],
                "currency": ["CNY"],
                "timezone": ["Asia/Shanghai"],
                "calendar": ["XSHE"],
                "name": [f"status {list_status}"],
                "is_active": [list_status == "L"],
                "area": ["Shenzhen"],
                "industry": ["Bank"],
                "stock_market": ["Main"],
                "list_date": [pd.Timestamp("2020-01-01").date()],
                "delist_date": [pd.Timestamp("2024-01-04").date() if list_status == "D" else pd.NaT],
                "is_hs": [""],
            }
        )


class FakeTushareTradeabilityAdapterWithNoPausedStatus(FakeTushareTradeabilityAdapter):
    def fetch_stock_basic(self, list_status: str = "L") -> pd.DataFrame:
        if list_status == "P":
            return pd.DataFrame(
                {
                    "asset_id": [],
                    "symbol": [],
                    "market": [],
                    "exchange": [],
                    "list_status": [],
                }
            )
        return super().fetch_stock_basic(list_status)


class FakeTushareTradeabilityAdapterWithDuplicateEvents(FakeTushareTradeabilityAdapter):
    def fetch_suspend_d_by_date(self, trade_date: str) -> pd.DataFrame:
        self.suspend_calls.append(trade_date)
        return pd.DataFrame(
            {
                "ts_code": ["000001.SZ", "000001.SZ"],
                "trade_date": [trade_date, trade_date],
                "suspend_timing": ["09:30", "09:30"],
                "suspend_type": ["S", "S"],
            }
        )

    def fetch_namechange(self, start_date: str, end_date: str) -> pd.DataFrame:
        self.namechange_calls.append((start_date, end_date))
        return pd.DataFrame(
            {
                "ts_code": ["000002.SZ", "000002.SZ"],
                "name": ["*ST Sample", "*ST Sample"],
                "start_date": ["20240103", "20240103"],
                "end_date": [None, None],
                "ann_date": ["20240103", "20240103"],
                "change_reason": ["special treatment", "special treatment"],
            }
        )


class TushareTradeabilityFeedIngestTests(unittest.TestCase):
    def test_report_only_ingest_adds_availability_lag_and_stock_status_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeTushareTradeabilityAdapter()

            result = run_tushare_tradeability_feed_ingest(adapter, "2024-01-02", "2024-01-03", Path(tmp))

            self.assertFalse(result["processed_writes_enabled"])
            self.assertEqual(result["summary"]["feed_count"], 4)
            self.assertEqual(result["summary"]["fail_count"], 0)
            self.assertEqual(adapter.limit_calls, ["20240102", "20240103"])
            self.assertEqual(adapter.suspend_calls, ["20240102", "20240103"])
            self.assertEqual(adapter.stock_status_calls, ["L", "P", "D"])
            limit_quality = result["feed_quality"]["tradeability_stk_limit"]
            self.assertEqual(limit_quality["status"], "pass")
            self.assertEqual(limit_quality["rows"], 2)
            self.assertEqual(limit_quality["available_date_min"], "2024-01-03")
            name_quality = result["feed_quality"]["tradeability_namechange"]
            self.assertEqual(name_quality["st_name_rows"], 1)

    def test_missing_paused_stock_status_is_warning_not_failure_when_live_and_delisted_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeTushareTradeabilityAdapterWithNoPausedStatus()

            result = run_tushare_tradeability_feed_ingest(adapter, "2024-01-02", "2024-01-03", Path(tmp))

            stock_quality = result["feed_quality"]["stock_basic_status"]
            self.assertEqual(stock_quality["status"], "pass")
            self.assertEqual(stock_quality["missing_status_values"], [])
            self.assertEqual(stock_quality["missing_optional_status_values"], ["P"])
            self.assertIn("missing_optional_status:P", stock_quality["warnings"])

    def test_duplicate_suspension_and_namechange_events_are_normalized_before_quality(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeTushareTradeabilityAdapterWithDuplicateEvents()

            result = run_tushare_tradeability_feed_ingest(adapter, "2024-01-02", "2024-01-03", Path(tmp))

            suspension_quality = result["feed_quality"]["tradeability_suspension"]
            namechange_quality = result["feed_quality"]["tradeability_namechange"]
            self.assertEqual(suspension_quality["status"], "pass")
            self.assertEqual(suspension_quality["duplicate_key_count"], 0)
            self.assertEqual(suspension_quality["rows"], 2)
            self.assertEqual(namechange_quality["status"], "pass")
            self.assertEqual(namechange_quality["duplicate_key_count"], 0)
            self.assertEqual(namechange_quality["rows"], 1)

    def test_execute_write_processed_writes_tradeability_partitions_and_metadata_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeTushareTradeabilityAdapter()

            result = run_tushare_tradeability_feed_ingest(
                adapter,
                "2024-01-02",
                "2024-01-03",
                Path(tmp),
                execute_write_processed=True,
                snapshot="2026-06-23",
            )

            self.assertTrue(result["processed_writes_enabled"])
            store = DatasetStore(Path(tmp))
            limits = store.read_frame(
                "processed/tradeability_stk_limit",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            self.assertTrue({"up_limit", "down_limit", "available_date"}.issubset(limits.columns))
            self.assertTrue((pd.to_datetime(limits["available_date"]) > pd.to_datetime(limits["date"])).all())
            suspensions = store.read_frame(
                "processed/tradeability_suspension",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            self.assertIn("suspend_type", suspensions.columns)
            status_d = store.read_frame("metadata/tushare_stock_basic", {"list_status": "D", "snapshot": "2026-06-23"})
            self.assertEqual(status_d.loc[0, "symbol"], "000003.SZ")
            coverage = store.read_frame(
                "metadata/tushare_tradeability_feed_coverage",
                {"market": "CN", "shard": "20240102_20240103"},
            )
            self.assertEqual(result["coverage_manifest_written"], True)
            self.assertEqual(
                set(coverage["feed"]),
                {
                    "tradeability_stk_limit",
                    "tradeability_suspension",
                    "tradeability_namechange",
                    "stock_basic_status_snapshot",
                },
            )
            self.assertEqual(coverage["start_date"].iloc[0], "2024-01-02")
            self.assertEqual(coverage["end_date"].iloc[0], "2024-01-03")

    def test_execute_write_processed_can_separate_report_and_processed_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeTushareTradeabilityAdapter()
            report_dir = Path(tmp) / "reports"
            processed_dir = Path(tmp) / "processed"

            result = run_tushare_tradeability_feed_ingest(
                adapter,
                "2024-01-02",
                "2024-01-03",
                report_dir,
                processed_output_dir=processed_dir,
                execute_write_processed=True,
                snapshot="2026-06-23",
            )

            self.assertEqual(result["processed_output_dir"], str(processed_dir))
            self.assertTrue((report_dir / "tradeability_feed_ingestion_report.json").exists())
            store = DatasetStore(processed_dir)
            limits = store.read_frame(
                "processed/tradeability_stk_limit",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            self.assertEqual(len(limits), 2)
            self.assertFalse((report_dir / "processed" / "tradeability_stk_limit").exists())


if __name__ == "__main__":
    unittest.main()
