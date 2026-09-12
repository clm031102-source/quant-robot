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
from tests.unit.test_offline_conversions import conversion_policy, start
from tests.unit.test_offline_dividends import extended_policy
from tests.unit.test_offline_order_admission import NOW, SYMBOL, context, intent


def open_book(path, *, old_order=False):
    book = OfflineOrderJournal.create(path, initial_cash="2600", initial_positions={SYMBOL: 100}, commission_bps="0.5",
        minimum_commission="5", admission_policy=extended_policy(), conversion_policy=conversion_policy())
    start(book)
    if old_order:
        book.admit(intent(), context(book), clock=lambda: NOW)
        book.report_status("one", "cancelled", "CANCELLED", 0)
    book.record_conversion_entitlements(clock=lambda: NOW.replace(hour=15))
    return book


class OfflineConversionRecoveryTests(unittest.TestCase):
    def test_two_writers_cannot_convert_the_same_holder_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"convert.sqlite"
            with open_book(path) as original:
                ready = Barrier(2)

                def writer(_):
                    with OfflineOrderJournal(path) as book:
                        ready.wait(timeout=10)
                        return book.apply_share_conversions(clock=lambda: NOW + timedelta(days=1))

                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(writer, (1, 2)))
                self.assertEqual(sorted(results), [False, True])
                self.assertEqual(original.snapshot()["positions"], {SYMBOL: 50})

    def test_conversion_racing_old_fill_never_mixes_old_and_new_share_units(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"fill-race.sqlite"
            with open_book(path, old_order=True) as original:
                ready = Barrier(2)

                def writer(action):
                    with OfflineOrderJournal(path) as book:
                        ready.wait(timeout=10)
                        try:
                            if action == "fill": return book.fill("one", "late", 40, "4")
                            return book.apply_share_conversions(clock=lambda: NOW + timedelta(days=1))
                        except ValueError as exc:
                            return str(exc)

                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(writer, ("convert", "fill")))
                self.assertIs(results[1], True)
                snap = original.snapshot()
                if snap["conversions"]["applied"]:
                    self.assertEqual(snap["positions"], {SYMBOL: 50})
                    self.assertEqual(Decimal(snap["cash"]), 2600)
                    self.assertIn("late", snap["conversions"]["unapplied_fills"])
                else:
                    self.assertEqual(snap["positions"], {SYMBOL: 140})
                    self.assertEqual(Decimal(snap["cash"]), 2435)
                self.assertIn("share_conversion_requires_review", snap["faults"])

    def test_process_exit_preserves_atomic_conversion_and_deferred_receipts(self):
        source = """
import os, sys
from datetime import timedelta
from tests.integration.test_offline_conversion_recovery import open_book
from tests.unit.test_offline_order_admission import NOW
phase, stage = sys.argv[2:]
book = open_book(sys.argv[1], old_order=phase == 'defer')
if phase == 'defer': book.apply_share_conversions(clock=lambda: NOW + timedelta(days=1))
kind = 'SHARE_CONVERSIONS' if phase == 'convert' else 'CONVERSION_UNAPPLIED_FILL'
if stage == 'before':
    append = book._append
    def crash(state, event):
        append(state, event)
        if event['kind'] == kind: os._exit(7)
    book._append = crash
if phase == 'convert': book.apply_share_conversions(clock=lambda: NOW + timedelta(days=1))
else: book.fill('one', 'late', 40, '4')
os._exit(7)
"""
        with tempfile.TemporaryDirectory() as directory:
            for phase in ("convert", "defer"):
                for stage in ("before", "after"):
                    with self.subTest(phase=phase, stage=stage):
                        path = Path(directory)/(phase + stage + ".sqlite")
                        result = subprocess.run([sys.executable, "-c", source, str(path), phase, stage], capture_output=True, text=True, timeout=30)
                        self.assertEqual(result.returncode, 7, result.stderr)
                        with OfflineOrderJournal(path) as book:
                            snap = book.snapshot()
                            converted = phase == "defer" or stage == "after"
                            self.assertEqual(snap["positions"], {SYMBOL: 50 if converted else 100})
                            self.assertEqual(Decimal(snap["cash"]), 2600)
                            self.assertEqual(bool(snap["price_basis"]), converted)
                            self.assertEqual(bool(snap["conversions"]["locks"]), converted)
                            if phase == "defer":
                                self.assertEqual(bool(snap["conversions"]["unapplied_fills"]), stage == "after")
                                self.assertEqual(book.fill("one", "late", 40, "4"), stage == "before")


if __name__ == "__main__":
    unittest.main()
