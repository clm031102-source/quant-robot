from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Barrier
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, intent, policy
from tests.unit.test_offline_order_timeouts import timeout_policy


class OfflineTimeoutRecoveryTests(unittest.TestCase):
    def test_concurrent_fill_and_timeout_never_release_or_charge_cash_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "timeout.sqlite"
            with OfflineOrderJournal.create(path, initial_cash="3000", initial_positions={}, commission_bps="0.5",
                    minimum_commission="5", admission_policy=policy(), timeout_policy=timeout_policy()) as original:
                packet = context(original)
                packet.update(instruments={s: instrument(s) for s in (SYMBOL, OTHER)}, sellable_positions={})
                original.begin_session(packet, clock=lambda: NOW)
                opened, start = Barrier(3), Barrier(3)

                def writer(action):
                    with OfflineOrderJournal(path) as book:
                        opened.wait(timeout=10)
                        start.wait(timeout=10)
                        return (book.fill("one", "fill", 100, "4") if action == "fill" else
                            book.monitor_timeouts(clock=lambda: NOW + timedelta(seconds=20)))

                with ThreadPoolExecutor(max_workers=2) as pool:
                    filled, monitored = [pool.submit(writer, name) for name in ["fill", "monitor"]]
                    opened.wait(timeout=10)
                    original.admit(intent(), context(original), clock=lambda: NOW)
                    original.prepare_dispatch("one", "prepare", context(original), clock=lambda: NOW)
                    start.wait(timeout=10)
                    self.assertTrue(filled.result(timeout=20))
                    timed_out = monitored.result(timeout=20)
                snap = original.snapshot()
                self.assertEqual(snap["orders"]["one"]["status"], "FILLED")
                self.assertEqual(float(snap["cash"]), 2595)
                self.assertEqual(float(snap["reserved_cash"]), 0)
                self.assertEqual(snap["positions"], {SYMBOL: 100})
                self.assertEqual(snap["paused"], timed_out)
                self.assertFalse(original.fill("one", "fill", 100, "4"))

    def test_two_order_timeout_event_is_atomic_across_real_process_exit(self):
        source = """
import os, sys
from datetime import timedelta
from quant_robot.execution.offline_journal import OfflineOrderJournal
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, intent, policy
from tests.unit.test_offline_order_timeouts import timeout_policy
book = OfflineOrderJournal.create(sys.argv[1], initial_cash='3000', initial_positions={}, commission_bps='0.5',
    minimum_commission='5', admission_policy=policy(), timeout_policy=timeout_policy())
packet = context(book)
packet.update(instruments={s: instrument(s) for s in (SYMBOL, OTHER)}, sellable_positions={})
book.begin_session(packet, clock=lambda: NOW)
for key, symbol in [('one', SYMBOL), ('two', OTHER)]:
    book.admit(intent(key, code=symbol), context(book), clock=lambda: NOW)
    book.prepare_dispatch(key, 'prepare-' + key, context(book), clock=lambda: NOW)
if sys.argv[2] == 'before':
    append = book._append
    def crash(state, event):
        append(state, event)
        if event['kind'] == 'ORDER_TIMEOUT':
            os._exit(7)
    book._append = crash
book.monitor_timeouts(clock=lambda: NOW + timedelta(seconds=20))
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
                    self.assertEqual(sum("timeout" in row for row in snap["orders"].values()), 2 if stage == "after" else 0)
                    self.assertTrue(snap["paused"])
                    self.assertEqual(float(snap["reserved_cash"]), 810)
                    self.assertEqual(float(snap["cash"]), 3000)
                    self.assertEqual(snap["positions"], {})


if __name__ == "__main__":
    unittest.main()
