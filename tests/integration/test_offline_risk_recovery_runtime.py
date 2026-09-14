"""Synthetic two-session recovery; never market evidence or forward paper days."""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from quant_robot.execution.offline_runtime import OfflineRuntime
from tests.integration.test_offline_session_baseline_runtime import create_baseline_book
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, intent
from tests.unit.test_offline_runtime import observation
from tests.unit.test_offline_target_compiler import target


class OfflineRiskRecoveryRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.now = NOW

    def create(self, name):
        path = Path(self.directory.name) / (name + ".sqlite")
        with create_baseline_book(path):
            pass
        return path

    def tick(self, runtime, now, price="5.002", *, opening=False, **fields):
        self.now = now
        feed = observation(runtime, now, opening=opening)
        feed["quotes"][SYMBOL].update(bid=price, ask=price)
        if opening:
            feed["opening"]["sellable_positions"] = runtime.book.snapshot()["positions"]
        feed.update(fields)
        report = runtime.tick(feed)
        self.assertFalse(report["executable"])
        self.assertEqual(report["counts_as_forward_paper_days"], 0)
        return report

    def reduce(self, runtime, *, fill=True):
        report = self.tick(runtime, NOW + timedelta(seconds=1),
            targets=[target(runtime.book, limit_price="5.002")],
            intents=[intent("before-reduction", code=OTHER)])
        self.assertEqual(report["risk_stop_causes"], ["single_position"])
        state = runtime.book.snapshot()
        self.assertNotIn("before-reduction", state["orders"])
        order = state["orders"]["target-one"]
        self.assertEqual((order["side"], order["quantity"], order["filled_quantity"]), ("SELL", 100, 0))
        self.assertIn("dispatch", order)
        self.assertEqual(state["positions"], {SYMBOL: 200})
        self.assertEqual(Decimal(state["cash"]), Decimal("9010"))
        if fill:
            self.tick(runtime, NOW + timedelta(seconds=2), receipts=[{
                "kind": "fill", "order_id": "target-one", "fill_id": "explicit-reduction",
                "quantity": 100, "price": "5.002"}])
            state = runtime.book.snapshot()
            self.assertEqual(state["positions"], {SYMBOL: 100})
            self.assertEqual(Decimal(state["cash"]), Decimal("9505.2"))
            self.assertTrue(state["paused"])

    def test_filled_reduction_and_qualified_close_allow_new_risk_only_next_session(self):
        path = self.create("recovery")
        with OfflineRuntime(path, clock=lambda: self.now) as runtime:
            self.reduce(runtime)
            now = NOW + timedelta(seconds=3)
            self.tick(runtime, now, intents=[intent("same-day", code=OTHER, now=now)])
            self.assertNotIn("same-day", runtime.book.snapshot()["orders"])
            self.tick(runtime, NOW.replace(hour=15, minute=0))
            closing = runtime.book.snapshot()["last_session_close"]
            self.assertEqual(Decimal(closing["book_equity"]), Decimal("10005.4"))
        self.now = NOW + timedelta(days=1)
        with OfflineRuntime(path, clock=lambda: self.now) as restarted:
            self.assertEqual(restarted.book.snapshot()["last_session_close"], closing)
            report = self.tick(restarted, self.now, opening=True,
                intents=[intent("next-day", code=OTHER, now=self.now)])
            self.assertEqual(report["status"], "ready")
            self.assertEqual(report["risk_stop_causes"], [])
            self.assertEqual(restarted.book.snapshot()["orders"]["next-day"]["filled_quantity"], 0)
            self.tick(restarted, self.now + timedelta(seconds=1), receipts=[{
                "kind": "fill", "order_id": "next-day", "fill_id": "explicit-new-position",
                "quantity": 100, "price": "4"}])
            state = restarted.book.snapshot()
            self.assertEqual(state["positions"], {SYMBOL: 100, OTHER: 100})
            self.assertEqual(Decimal(state["cash"]), Decimal("9100.2"))
            self.assertEqual(Decimal(state["portfolio_valuation"]["last_valid"]["book_equity"]), Decimal("10000.4"))

    def test_missing_close_unresolved_reduction_or_unknown_receipt_prevent_recovery(self):
        for failure in ("missing_close", "unresolved_reduction", "unknown_receipt"):
            with self.subTest(failure=failure):
                path = self.create(failure)
                with OfflineRuntime(path, clock=lambda: self.now) as runtime:
                    self.reduce(runtime, fill=failure != "unresolved_reduction")
                    if failure == "unknown_receipt":
                        self.tick(runtime, NOW + timedelta(seconds=3), receipts=[{"kind": "unrecognized"}])
                    if failure != "missing_close":
                        self.tick(runtime, NOW.replace(hour=15, minute=0))
                    self.assertIsNone(runtime.book.snapshot()["last_session_close"])
                self.now = NOW + timedelta(days=1)
                with OfflineRuntime(path, clock=lambda: self.now) as restarted:
                    report = self.tick(restarted, self.now, opening=True,
                        intents=[intent("blocked", code=OTHER, now=self.now)])
                    self.assertTrue(report["paused"])
                    self.assertNotIn("blocked", restarted.book.snapshot()["orders"])
                    self.assertTrue(any(step["stage"] == "opening" and step["status"] == "rejected"
                        for step in report["steps"]))

    def test_daily_stop_resets_after_valid_close_but_drawdown_never_automatically_resets(self):
        for low, expected_cause in (("4.60", "daily_loss"), ("0.50", "cumulative_drawdown")):
            with self.subTest(cause=expected_cause):
                path = self.create(expected_cause)
                with OfflineRuntime(path, clock=lambda: self.now) as runtime:
                    report = self.tick(runtime, NOW + timedelta(seconds=1), low)
                    self.assertIn(expected_cause, report["risk_stop_causes"])
                    now = NOW + timedelta(seconds=2)
                    report = self.tick(runtime, now, "4.95", intents=[intent("intraday", code=OTHER, now=now)])
                    self.assertIn(expected_cause, report["risk_stop_causes"])
                    self.assertNotIn("intraday", runtime.book.snapshot()["orders"])
                    self.tick(runtime, NOW.replace(hour=15, minute=0), "4.95")
                    self.assertIsNotNone(runtime.book.snapshot()["last_session_close"])
                self.now = NOW + timedelta(days=1)
                with OfflineRuntime(path, clock=lambda: self.now) as restarted:
                    report = self.tick(restarted, self.now, "4.95", opening=True,
                        intents=[intent("next-day", code=OTHER, now=self.now)])
                    if expected_cause == "daily_loss":
                        self.assertFalse(report["paused"])
                        self.assertIn("next-day", restarted.book.snapshot()["orders"])
                    else:
                        self.assertTrue(report["paused"])
                        self.assertIn("cumulative_drawdown", report["risk_stop_causes"])
                        self.assertNotIn("next-day", restarted.book.snapshot()["orders"])

    def test_new_session_rechecks_exposure_before_allowing_another_buy(self):
        path = self.create("still-over-limit")
        with OfflineRuntime(path, clock=lambda: self.now) as runtime:
            self.tick(runtime, NOW + timedelta(seconds=1))
            self.tick(runtime, NOW.replace(hour=15, minute=0))
            self.assertIsNotNone(runtime.book.snapshot()["last_session_close"])
        self.now = NOW + timedelta(days=1)
        with OfflineRuntime(path, clock=lambda: self.now) as restarted:
            report = self.tick(restarted, self.now, opening=True,
                intents=[intent("still-blocked", code=OTHER, now=self.now)])
            self.assertEqual(report["risk_stop_causes"], ["single_position"])
            self.assertNotIn("still-blocked", restarted.book.snapshot()["orders"])
            self.assertEqual(restarted.book.snapshot()["positions"], {SYMBOL: 200})


if __name__ == "__main__":
    unittest.main()
