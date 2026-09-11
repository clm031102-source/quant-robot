from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Barrier
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, intent, policy


class OfflineDispatchRecoveryTests(unittest.TestCase):
    def test_two_writers_cannot_both_prepare_the_same_reserved_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dispatch.sqlite"
            with OfflineOrderJournal.create(path, initial_cash="3000", initial_positions={},
                    commission_bps="0.5", minimum_commission="5", admission_policy=policy()) as original:
                packet = context(original)
                packet.update(instruments={s: instrument(s) for s in (SYMBOL, OTHER)}, sellable_positions={})
                original.begin_session(packet, clock=lambda: NOW)
                opened, start, captured = Barrier(3), Barrier(3), Barrier(2)

                def writer(key):
                    # Both connections open before reservation, so this exercises
                    # concurrent dispatch rather than restart quarantine.
                    with OfflineOrderJournal(path) as book:
                        opened.wait(timeout=10)
                        start.wait(timeout=10)
                        packet = context(book)
                        captured.wait(timeout=10)
                        try:
                            book.prepare_dispatch("one", key, packet, clock=lambda: NOW)
                            return "prepared"
                        except ValueError as exc:
                            return str(exc)

                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(writer, key) for key in ["first", "second"]]
                    opened.wait(timeout=10)
                    original.admit(intent(), context(original), clock=lambda: NOW)
                    start.wait(timeout=10)
                    results = [future.result(timeout=20) for future in futures]
                self.assertEqual(results.count("prepared"), 1)
                self.assertTrue(any("never-prepared" in result for result in results))
                self.assertEqual(original.snapshot()["orders"]["one"]["filled_quantity"], 0)
                self.assertFalse(original.snapshot()["executable"])

    def test_real_exit_before_and_after_commit_preserves_atomic_dispatch_evidence(self):
        source = """
import os, sys
from quant_robot.execution.offline_journal import OfflineOrderJournal
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, intent, policy
book = OfflineOrderJournal.create(sys.argv[1], initial_cash='3000', initial_positions={},
    commission_bps='0.5', minimum_commission='5', admission_policy=policy())
packet = context(book)
packet.update(instruments={s: instrument(s) for s in (SYMBOL, OTHER)}, sellable_positions={})
book.begin_session(packet, clock=lambda: NOW)
book.admit(intent(), context(book), clock=lambda: NOW)
if sys.argv[2] == 'before':
    append = book._append
    def crash(state, event):
        append(state, event)
        if event['kind'] == 'DISPATCH_PREPARED':
            os._exit(7)
    book._append = crash
book.prepare_dispatch('one', 'attempt', context(book), clock=lambda: NOW)
os._exit(7)
"""
        with tempfile.TemporaryDirectory() as directory:
            for stage in ["before", "after"]:
                path = Path(directory) / (stage + ".sqlite")
                result = subprocess.run([sys.executable, "-c", source, str(path), stage],
                    capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 7, result.stderr)
                with OfflineOrderJournal(path) as book:
                    snap = book.snapshot()
                    self.assertEqual("dispatch" in snap["orders"]["one"], stage == "after")
                    self.assertEqual(snap["orders"]["one"]["status"], "UNKNOWN")
                    self.assertTrue(snap["paused"])
                    self.assertEqual(float(snap["reserved_cash"]), 405)
                    self.assertEqual(snap["positions"], {})
                    with self.assertRaises(ValueError):
                        book.prepare_dispatch("one", "retry", context(book), clock=lambda: NOW)


if __name__ == "__main__":
    unittest.main()
