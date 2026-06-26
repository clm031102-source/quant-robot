import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.dragon_tiger_coverage_audit import (
    render_dragon_tiger_coverage_audit_markdown,
    run_dragon_tiger_coverage_audit,
)
from quant_robot.storage.dataset_store import DatasetStore


class FakeDragonTigerAdapter:
    def fetch_trade_calendar(self, start_date: str, end_date: str):
        dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
        return pd.DataFrame({"date": dates.date, "is_open": [1, 1, 1]})

    def fetch_top_list_by_trade_date(self, trade_date: str):
        return pd.DataFrame(
            {
                "trade_date": [trade_date, trade_date],
                "ts_code": ["000001.SZ", "000001.SZ"],
                "name": ["Ping An Bank", "Ping An Bank"],
                "pct_change": [10.0, 10.0],
                "amount": [1000.0, 1000.0],
                "net_amount": [120.0, -20.0],
                "net_rate": [12.0, -2.0],
                "amount_rate": [8.0, 8.0],
                "reason": ["reason_a", "reason_b"],
            }
        )

    def fetch_top_inst_by_trade_date(self, trade_date: str):
        return pd.DataFrame(
            {
                "trade_date": [trade_date],
                "ts_code": ["000001.SZ"],
                "exalter": ["institution"],
                "side": ["buy"],
                "buy": [300.0],
                "sell": [100.0],
                "net_buy": [200.0],
                "reason": ["reason_a"],
            }
        )


class FakeShortCalendarDragonTigerAdapter(FakeDragonTigerAdapter):
    def fetch_trade_calendar(self, start_date: str, end_date: str):
        dates = pd.to_datetime(["2024-01-02"])
        return pd.DataFrame({"date": dates.date, "is_open": [1]})


class FakeTransientEmptyCalendarDragonTigerAdapter(FakeDragonTigerAdapter):
    def __init__(self) -> None:
        self.calendar_calls = 0

    def fetch_trade_calendar(self, start_date: str, end_date: str):
        self.calendar_calls += 1
        if self.calendar_calls == 1:
            return pd.DataFrame(columns=["date", "is_open"])
        return super().fetch_trade_calendar(start_date, end_date)


class DragonTigerCoverageAuditTests(unittest.TestCase):
    def test_builds_pit_safe_coverage_audit_and_processed_aggregate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "report"
            processed_root = Path(tmp) / "processed_root"

            result = run_dragon_tiger_coverage_audit(
                FakeDragonTigerAdapter(),
                "2024-01-02",
                "2024-01-03",
                output_dir,
                processed_root=processed_root,
                execute_write_processed=True,
            )

            self.assertEqual(result["summary"]["status"], "pass")
            self.assertTrue(result["summary"]["pit_prescreen_allowed"])
            self.assertEqual(result["endpoint_quality"]["top_list"]["warnings"], [])
            self.assertEqual(result["endpoint_quality"]["top_list"]["rows"], 4)
            self.assertEqual(result["endpoint_quality"]["top_inst"]["rows"], 2)
            self.assertEqual(result["aggregate_quality"]["rows"], 2)
            self.assertEqual(result["aggregate_quality"]["lag_violation_count"], 0)
            self.assertTrue((output_dir / "dragon_tiger_coverage_audit.json").exists())
            markdown = render_dragon_tiger_coverage_audit_markdown(result)
            self.assertIn("Dragon-Tiger Full Coverage Audit", markdown)

            store = DatasetStore(processed_root)
            stock_day = store.read_frame(
                "processed/dragon_tiger_stock_day",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            self.assertTrue((pd.to_datetime(stock_day["available_date"]) > pd.to_datetime(stock_day["date"])).all())
            self.assertEqual(stock_day["top_list_event_count"].sum(), 4)
            self.assertEqual(stock_day["top_inst_net_buy_sum"].sum(), 400.0)

    def test_missing_next_trade_date_blocks_pit_prescreen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_dragon_tiger_coverage_audit(
                FakeShortCalendarDragonTigerAdapter(),
                "2024-01-02",
                "2024-01-02",
                Path(tmp),
            )

            self.assertEqual(result["summary"]["status"], "fail")
            self.assertIn("top_list:missing_available_date_rows", result["summary"]["blockers"])
            self.assertIn("top_inst:missing_available_date_rows", result["summary"]["blockers"])
            self.assertFalse(result["summary"]["pit_prescreen_allowed"])

    def test_retries_transient_empty_trade_calendar_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeTransientEmptyCalendarDragonTigerAdapter()

            result = run_dragon_tiger_coverage_audit(
                adapter,
                "2024-01-02",
                "2024-01-03",
                Path(tmp),
            )

            self.assertEqual(result["summary"]["status"], "pass")
            self.assertEqual(adapter.calendar_calls, 2)


if __name__ == "__main__":
    unittest.main()
