from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal
from quant_robot.execution.offline_runtime import OfflineRuntime
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, policy
from tests.unit.test_offline_order_timeouts import timeout_policy
from tests.unit.test_offline_runtime import observation


def create_baseline_book(path):
    cfg = {**policy(), "schema_version": 2, "max_drawdown": ".08", "capital_limit_cny": "10000",
        "daily_loss_basis": "previous_session_close_v1", "exposure_stop_action": "reduce_only"}
    book = OfflineOrderJournal.create(path, initial_cash="9010", initial_positions={SYMBOL: 200},
        commission_bps="5", minimum_commission="5", admission_policy=cfg, timeout_policy=timeout_policy())
    packet = context(book)
    packet["quotes"][SYMBOL].update(bid="4.95", ask="4.95")
    packet.update(instruments={code: instrument(code) for code in (SYMBOL, OTHER)}, sellable_positions={SYMBOL: 200})
    book.begin_session(packet, clock=lambda: NOW)
    return book


class OfflineSessionBaselineRuntimeTests(unittest.TestCase):
    def test_runtime_records_close_and_keeps_overnight_loss_in_the_next_opening(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runtime.sqlite"
            with create_baseline_book(path):
                pass
            now = NOW.replace(hour=15, minute=0)
            with OfflineRuntime(path, clock=lambda: now) as runtime:
                feed = observation(runtime, now)
                feed["quotes"][SYMBOL].update(bid="4.95", ask="4.95")
                runtime.tick(feed)
                self.assertIsNotNone(runtime.book.snapshot()["last_session_close"])
                now = NOW + timedelta(days=1)
                feed = observation(runtime, now, opening=True)
                feed["opening"]["sellable_positions"] = {SYMBOL: 200}
                feed["quotes"][SYMBOL].update(bid="4.455", ask="4.455")
                report = runtime.tick(feed)
                self.assertTrue(report["paused"])
                self.assertIn("daily_loss", report["risk_stop_causes"])
                self.assertEqual(Decimal(runtime.book.snapshot()["portfolio_valuation"]["last_valid"]["projected_daily_loss"]), 99)
                self.assertEqual(report["counts_as_forward_paper_days"], 0)
                self.assertFalse(report["executable"])

    def test_process_exit_cannot_leave_a_close_baseline_without_its_valuation_commit(self):
        source = '''
import os, sys
from tests.integration.test_offline_session_baseline_runtime import create_baseline_book
from tests.unit.test_offline_order_admission import NOW, SYMBOL, context
book = create_baseline_book(sys.argv[1])
now = NOW.replace(hour=15, minute=0)
if sys.argv[2] == 'before':
    append = book._append
    def crash(state, event):
        append(state, event)
        if event['kind'] == 'PORTFOLIO_VALUATION': os._exit(23)
    book._append = crash
packet = context(book, now)
packet['quotes'][SYMBOL].update(bid='4.95', ask='4.95')
book.record_valuation(packet, clock=lambda: now)
os._exit(23)
'''
        with tempfile.TemporaryDirectory() as directory:
            for phase in ("before", "after"):
                path = Path(directory) / (phase + ".sqlite")
                process = subprocess.run([sys.executable, "-c", source, str(path), phase], capture_output=True, text=True, timeout=30)
                self.assertEqual(process.returncode, 23, process.stdout + process.stderr)
                snapshot = OfflineOrderJournal.inspect_snapshot(path)
                self.assertEqual(snapshot["last_session_close"] is not None, phase == "after")
                self.assertEqual(snapshot["portfolio_valuation"]["last_valid"] is not None, phase == "after")
                if phase == "after":
                    self.assertEqual(snapshot["last_session_close"]["event_sequence"], snapshot["portfolio_valuation"]["last_valid"]["event_sequence"])


if __name__ == "__main__":
    unittest.main()
