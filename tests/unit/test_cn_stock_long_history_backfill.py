import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.cn_stock_long_history_backfill import (
    build_monthly_windows,
    run_cn_stock_long_history_backfill,
)


class CnStockLongHistoryBackfillTests(unittest.TestCase):
    def test_build_monthly_windows_splits_inclusive_date_range(self):
        windows = build_monthly_windows("2015-01-15", "2015-03-10")

        self.assertEqual(
            windows,
            [
                {"start_date": "2015-01-15", "end_date": "2015-01-31"},
                {"start_date": "2015-02-01", "end_date": "2015-02-28"},
                {"start_date": "2015-03-01", "end_date": "2015-03-10"},
            ],
        )

    def test_dry_run_returns_plan_without_calling_ingest(self):
        calls = []

        def fake_ingest(**kwargs):
            calls.append(kwargs)
            return {}

        with tempfile.TemporaryDirectory() as tmp:
            pack = run_cn_stock_long_history_backfill(
                start_date="2015-01-01",
                end_date="2015-01-31",
                output_dir=Path(tmp),
                execute=False,
                ingest_runner=fake_ingest,
            )

        self.assertEqual(pack["mode"], "dry_run")
        self.assertEqual(pack["summary"]["windows"], 1)
        self.assertEqual(calls, [])

    def test_execute_retries_daily_until_adjustment_is_applied(self):
        calls = []

        def fake_ingest(**kwargs):
            calls.append(kwargs)
            source = kwargs["source"]
            if source == "tushare" and sum(call["source"] == "tushare" for call in calls) == 1:
                return {"adjusted": False, "adjustment_report": {"coverage": 0.8, "status": "partial_adj_factor_coverage"}}
            if source == "tushare":
                return {"adjusted": True, "adjustment_report": {"coverage": 1.0, "status": "applied"}}
            return {"processed_rows": 10, "quality_report": {"rows": 10}}

        with tempfile.TemporaryDirectory() as tmp:
            pack = run_cn_stock_long_history_backfill(
                start_date="2015-01-01",
                end_date="2015-01-31",
                output_dir=Path(tmp),
                execute=True,
                daily_adjustment_retries=2,
                ingest_runner=fake_ingest,
            )

        daily_attempts = [call for call in calls if call["source"] == "tushare"]
        self.assertEqual(len(daily_attempts), 2)
        self.assertEqual(pack["summary"]["blockers"], 0)
        self.assertEqual(pack["windows"][0]["interfaces"][0]["attempts"], 2)

    def test_execute_records_blocker_when_daily_adjustment_retries_are_exhausted(self):
        def fake_ingest(**kwargs):
            if kwargs["source"] == "tushare":
                return {"adjusted": False, "adjustment_report": {"coverage": 0.8, "status": "partial_adj_factor_coverage"}}
            return {"processed_rows": 10, "quality_report": {"rows": 10}}

        with tempfile.TemporaryDirectory() as tmp:
            pack = run_cn_stock_long_history_backfill(
                start_date="2015-01-01",
                end_date="2015-01-31",
                output_dir=Path(tmp),
                execute=True,
                daily_adjustment_retries=1,
                ingest_runner=fake_ingest,
            )
            self.assertTrue((Path(tmp) / "cn_stock_long_history_backfill_summary.json").exists())

        self.assertEqual(pack["summary"]["blockers"], 1)
        self.assertIn("daily_adjustment_incomplete", pack["windows"][0]["interfaces"][0]["blockers"])

    def test_execute_retries_empty_raw_response_for_factor_interfaces(self):
        calls = []

        def fake_ingest(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise RuntimeError("empty raw response for open trade date 20150209")
            return {"processed_rows": 10, "quality_report": {"rows": 10}}

        with tempfile.TemporaryDirectory() as tmp:
            pack = run_cn_stock_long_history_backfill(
                start_date="2015-02-01",
                end_date="2015-02-28",
                output_dir=Path(tmp),
                execute=True,
                interfaces=("daily_basic",),
                empty_raw_retries=2,
                ingest_runner=fake_ingest,
            )

        self.assertEqual(len(calls), 2)
        self.assertEqual(pack["summary"]["blockers"], 0)
        self.assertEqual(pack["windows"][0]["interfaces"][0]["attempts"], 2)
        self.assertEqual(pack["windows"][0]["interfaces"][0]["latest"]["processed_rows"], 10)

    def test_execute_records_blocker_when_empty_raw_response_retries_are_exhausted(self):
        calls = []

        def fake_ingest(**kwargs):
            calls.append(kwargs)
            raise RuntimeError("empty raw response for open trade date 20150209")

        with tempfile.TemporaryDirectory() as tmp:
            pack = run_cn_stock_long_history_backfill(
                start_date="2015-02-01",
                end_date="2015-02-28",
                output_dir=Path(tmp),
                execute=True,
                interfaces=("daily_basic",),
                empty_raw_retries=2,
                ingest_runner=fake_ingest,
            )
            self.assertTrue((Path(tmp) / "cn_stock_long_history_backfill_summary.json").exists())

        result = pack["windows"][0]["interfaces"][0]
        self.assertEqual(len(calls), 2)
        self.assertEqual(pack["summary"]["blockers"], 1)
        self.assertEqual(result["attempts"], 2)
        self.assertIn("empty_raw_response", result["blockers"])
        self.assertIn("20150209", result["latest"]["error"])

    def test_execute_retries_empty_trade_calendar_like_monthly_response(self):
        calls = []

        def fake_ingest(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return {
                    "processed_rows": 0,
                    "downloaded_trade_dates": [],
                    "skipped_trade_dates": [],
                    "quality_report": {"rows": 0},
                }
            return {"processed_rows": 10, "quality_report": {"rows": 10}}

        with tempfile.TemporaryDirectory() as tmp:
            pack = run_cn_stock_long_history_backfill(
                start_date="2015-05-01",
                end_date="2015-05-31",
                output_dir=Path(tmp),
                execute=True,
                interfaces=("daily_basic",),
                empty_raw_retries=2,
                ingest_runner=fake_ingest,
            )

        self.assertEqual(len(calls), 2)
        self.assertEqual(pack["summary"]["blockers"], 0)
        self.assertEqual(pack["windows"][0]["interfaces"][0]["attempts"], 2)

    def test_execute_records_blocker_when_empty_trade_calendar_response_retries_are_exhausted(self):
        calls = []

        def fake_ingest(**kwargs):
            calls.append(kwargs)
            return {
                "processed_rows": 0,
                "downloaded_trade_dates": [],
                "skipped_trade_dates": [],
                "quality_report": {"rows": 0},
            }

        with tempfile.TemporaryDirectory() as tmp:
            pack = run_cn_stock_long_history_backfill(
                start_date="2015-05-01",
                end_date="2015-05-31",
                output_dir=Path(tmp),
                execute=True,
                interfaces=("daily_basic",),
                empty_raw_retries=2,
                ingest_runner=fake_ingest,
            )

        result = pack["windows"][0]["interfaces"][0]
        self.assertEqual(len(calls), 2)
        self.assertEqual(pack["summary"]["blockers"], 1)
        self.assertIn("empty_trade_calendar_response", result["blockers"])
        self.assertIn("2015-05-01", result["latest"]["error"])


if __name__ == "__main__":
    unittest.main()
