from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Barrier
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, intent, policy


def open_book(path):
    book = OfflineOrderJournal.create(path, initial_cash="2600", initial_positions={SYMBOL: 100},
        commission_bps="0.5", minimum_commission="5", admission_policy=policy())
    packet = context(book)
    packet.update(instruments={s: instrument(s) for s in (SYMBOL, OTHER)}, sellable_positions={SYMBOL: 100})
    book.begin_session(packet, clock=lambda: NOW)
    return book


class OfflineValuationRecoveryTests(unittest.TestCase):
    def test_competing_frames_require_rebinding_without_creating_a_quote_outage(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "valuation.sqlite"
            with open_book(path) as original:
                captured = Barrier(2)

                def writer(price):
                    with OfflineOrderJournal(path) as book:
                        packet = context(book)
                        packet["quotes"][SYMBOL].update(bid=price, ask=price)
                        captured.wait(timeout=10)
                        try:
                            book.record_valuation(packet, clock=lambda: NOW)
                            return "valued"
                        except ValueError as exc:
                            return str(exc)

                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(writer, ["4", "3.4"]))
                self.assertEqual(results.count("valued"), 1)
                self.assertTrue(any("stale journal anchor" in r for r in results))
                self.assertFalse(original.snapshot()["portfolio_valuation"]["unavailable"])
                later = NOW + timedelta(seconds=1)
                packet = context(original, later)
                packet["quotes"][SYMBOL].update(bid="3.4", ask="3.4")
                original.record_valuation(packet, clock=lambda: later)
                self.assertTrue(original.snapshot()["risk_session"]["risk_stop"])
                self.assertEqual(Decimal(original.snapshot()["portfolio_valuation"]["last_valid"]["book_equity"]), 2940)

    def test_fill_racing_a_valuation_never_presents_old_book_value_as_current(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fill-race.sqlite"
            with open_book(path) as original:
                opened, start, captured = Barrier(3), Barrier(3), Barrier(2)

                def writer(action):
                    with OfflineOrderJournal(path) as book:
                        opened.wait(timeout=10)
                        start.wait(timeout=10)
                        packet = context(book)
                        captured.wait(timeout=10)
                        try:
                            return book.fill("one", "fill", 100, "4") if action == "fill" else book.record_valuation(packet, clock=lambda: NOW)
                        except ValueError as exc:
                            return str(exc)

                with ThreadPoolExecutor(max_workers=2) as pool:
                    filled, valued = [pool.submit(writer, action) for action in ["fill", "value"]]
                    opened.wait(timeout=10)
                    original.admit(intent(), context(original), clock=lambda: NOW)
                    original.record_valuation(context(original), clock=lambda: NOW)
                    start.wait(timeout=10)
                    self.assertTrue(filled.result(timeout=20))
                    result = valued.result(timeout=20)
                    self.assertTrue(result is True or "stale journal anchor" in result)
                self.assertFalse(original.snapshot()["portfolio_valuation"]["matches_current_journal"])
                original.record_valuation(context(original), clock=lambda: NOW)
                snap = original.snapshot()
                self.assertEqual(Decimal(snap["portfolio_valuation"]["last_valid"]["book_equity"]), 2995)
                self.assertTrue(snap["portfolio_valuation"]["matches_current_journal"])

    def test_process_exit_cannot_commit_valuation_without_its_loss_stop(self):
        source = """
import os, sys
from tests.integration.test_offline_valuation_recovery import open_book
from tests.unit.test_offline_order_admission import NOW, SYMBOL, context
book = open_book(sys.argv[1])
if sys.argv[2] == 'before':
    append = book._append
    def crash(state, event):
        append(state, event)
        if event['kind'] == 'PORTFOLIO_VALUATION':
            os._exit(7)
    book._append = crash
packet = context(book)
packet['quotes'][SYMBOL].update(bid='3.4', ask='3.4')
book.record_valuation(packet, clock=lambda: NOW)
os._exit(7)
"""
        with tempfile.TemporaryDirectory() as directory:
            for stage in ["before", "after"]:
                path = Path(directory) / (stage + ".sqlite")
                result = subprocess.run([sys.executable, "-c", source, str(path), stage], capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 7, result.stderr)
                with OfflineOrderJournal(path) as book:
                    snap = book.snapshot()
                    self.assertEqual(snap["portfolio_valuation"]["last_valid"] is not None, stage == "after")
                    self.assertEqual(snap["risk_session"]["risk_stop"], stage == "after")
                    self.assertEqual(snap["positions"], {SYMBOL: 100})
                    self.assertEqual(Decimal(snap["cash"]), 2600)


if __name__ == "__main__":
    unittest.main()
