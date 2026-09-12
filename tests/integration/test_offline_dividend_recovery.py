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
from tests.unit.test_offline_dividends import dividend_policy, extended_policy, start
from tests.unit.test_offline_order_admission import NOW, SYMBOL, context, intent


def open_book(path):
    book = OfflineOrderJournal.create(path, initial_cash="2600", initial_positions={SYMBOL: 100}, commission_bps="0.5",
        minimum_commission="5", admission_policy=extended_policy(), dividend_policy=dividend_policy())
    start(book, NOW)
    return book


def accrue(book):
    book.record_dividend_entitlements(clock=lambda: NOW.replace(hour=15))
    book.accrue_dividends(clock=lambda: NOW + timedelta(days=1))


class OfflineDividendRecoveryTests(unittest.TestCase):
    def test_competing_receipts_cannot_double_credit_one_dividend(self):
        with tempfile.TemporaryDirectory() as directory:
            for same_id in (True, False):
                path = Path(directory)/(str(same_id) + ".sqlite")
                with open_book(path) as original:
                    accrue(original)
                    ready = Barrier(2)

                    def writer(index):
                        with OfflineOrderJournal(path) as book:
                            ready.wait(timeout=10)
                            try:
                                return book.record_dividend_cash_credit("div-one", "same" if same_id else str(index), "60",
                                    clock=lambda: NOW + timedelta(days=2))
                            except ValueError as exc:
                                return str(exc)

                    with ThreadPoolExecutor(max_workers=2) as pool:
                        results = list(pool.map(writer, (1, 2)))
                    self.assertEqual(results.count(True), 1)
                    self.assertEqual(Decimal(original.snapshot()["cash"]), 2660)
                    self.assertEqual(Decimal(original.snapshot()["dividends"]["receivable_total"]), 0)

    def test_record_capture_racing_late_fill_never_certifies_changed_holdings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"capture.sqlite"
            with open_book(path) as original:
                original.admit(intent(), context(original), clock=lambda: NOW)
                original.report_status("one", "cancelled", "CANCELLED", 0)
                ready = Barrier(2)

                def writer(action):
                    with OfflineOrderJournal(path) as book:
                        ready.wait(timeout=10)
                        try:
                            if action == "capture":
                                return book.record_dividend_entitlements(clock=lambda: NOW.replace(hour=15))
                            return book.fill("one", "late", 40, "4")
                        except ValueError as exc:
                            return str(exc)

                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(writer, ("capture", "fill")))
                self.assertTrue(results[1])
                snap = original.snapshot()
                entitlement = snap["dividends"]["entitlements"].get("div-one")
                if entitlement is not None:
                    self.assertEqual(entitlement["quantity"], 100)
                    self.assertIn("dividend_entitlement_requires_review", snap["faults"])
                else:
                    self.assertIn("unresolved", results[0])
                self.assertTrue(snap["paused"])

    def test_process_exit_preserves_atomic_receivable_and_cash_transfers(self):
        source = """
import os, sys
from datetime import timedelta
from tests.integration.test_offline_dividend_recovery import open_book
from tests.unit.test_offline_order_admission import NOW
book = open_book(sys.argv[1])
book.record_dividend_entitlements(clock=lambda: NOW.replace(hour=15))
phase, stage = sys.argv[2:]
if phase == 'credit':
    book.accrue_dividends(clock=lambda: NOW + timedelta(days=1))
kind = 'DIVIDEND_ACCRUAL' if phase == 'accrue' else 'DIVIDEND_CASH_CREDIT'
if stage == 'before':
    append = book._append
    def crash(state, event):
        append(state, event)
        if event['kind'] == kind:
            os._exit(7)
    book._append = crash
if phase == 'accrue':
    book.accrue_dividends(clock=lambda: NOW + timedelta(days=1))
else:
    book.record_dividend_cash_credit('div-one', 'credit', '60', clock=lambda: NOW + timedelta(days=2))
os._exit(7)
"""
        with tempfile.TemporaryDirectory() as directory:
            for phase in ("accrue", "credit"):
                for stage in ("before", "after"):
                    with self.subTest(phase=phase, stage=stage):
                        path = Path(directory)/(phase + stage + ".sqlite")
                        result = subprocess.run([sys.executable, "-c", source, str(path), phase, stage], capture_output=True, text=True, timeout=30)
                        self.assertEqual(result.returncode, 7, result.stderr)
                        with OfflineOrderJournal(path) as book:
                            snap = book.snapshot()
                            credited = phase == "credit" and stage == "after"
                            accrued = phase == "credit" or stage == "after"
                            self.assertEqual(Decimal(snap["cash"]), 2660 if credited else 2600)
                            self.assertEqual(Decimal(snap["dividends"]["receivable_total"]), 60 if accrued and not credited else 0)
                            self.assertEqual(bool(snap["dividends"]["price_basis"]), accrued)
                            if credited:
                                self.assertFalse(book.record_dividend_cash_credit("div-one", "credit", "60", clock=lambda: NOW + timedelta(days=2)))


if __name__ == "__main__":
    unittest.main()
