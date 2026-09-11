from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from threading import Barrier
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal


class OfflineOrderRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "orders.sqlite"
        self.book = OfflineOrderJournal.create(self.path, initial_cash="3000", initial_positions={},
            commission_bps="5", minimum_commission="5")
        self.addCleanup(lambda: self.book.close())

    def register(self, book, key):
        book.register(order_id=key, idempotency_key=key, symbol="510300.SH", side="BUY", quantity=200, limit_price="10")

    def crash_child(self, before_commit):
        source = """
import os, sys
from quant_robot.execution.offline_journal import OfflineOrderJournal
book = OfflineOrderJournal(sys.argv[1])
if sys.argv[2] == 'before_commit':
    original = book._append
    def crash(state, event):
        original(state, event)
        os._exit(7)
    book._append = crash
book.fill('o1', 'f1', 200, '10')
os._exit(7)
"""
        result = subprocess.run([sys.executable, "-c", source, str(self.path),
            "before_commit" if before_commit else "after_commit"], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.book.close()
        self.book = OfflineOrderJournal(self.path)

    def test_process_exit_after_commit_preserves_fill_and_identity(self):
        self.register(self.book, "o1")
        self.crash_child(before_commit=False)
        state = self.book.snapshot()
        self.assertEqual(float(state["cash"]), 995)
        self.assertEqual(state["positions"], {"510300.SH": 200})
        self.assertFalse(self.book.fill("o1", "f1", 200, "10"))

    def test_process_exit_inside_transaction_rolls_back_cash_fill_and_receipt_together(self):
        self.register(self.book, "o1")
        self.crash_child(before_commit=True)
        state = self.book.snapshot()
        self.assertEqual(float(state["cash"]), 3000)
        self.assertEqual(state["positions"], {})
        self.assertTrue(state["paused"])
        self.assertTrue(self.book.fill("o1", "f1", 200, "10"))
        self.assertEqual(float(self.book.snapshot()["cash"]), 995)

    def test_concurrent_writers_cannot_spend_same_reserved_cash(self):
        barrier = Barrier(2)

        def worker(key):
            with OfflineOrderJournal(self.path) as book:
                barrier.wait(timeout=10)
                try:
                    self.register(book, key)
                    return "registered"
                except ValueError as exc:
                    return str(exc)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, ["a", "b"]))
        self.assertCountEqual(results, ["registered", "insufficient unreserved cash"])
        self.assertEqual(len(self.book.snapshot()["orders"]), 1)

    def test_changed_event_body_is_detected_on_reopen(self):
        self.register(self.book, "o1")
        self.book.close()
        connection = sqlite3.connect(self.path)
        try:
            connection.execute("DROP TRIGGER events_no_update")
            payload = json.loads(connection.execute("SELECT payload FROM events WHERE sequence = 2").fetchone()[0])
            payload["data"]["quantity"] = 300
            connection.execute("UPDATE events SET payload = ? WHERE sequence = 2", (json.dumps(payload),))
            connection.commit()
        finally:
            connection.close()
        with self.assertRaisesRegex(ValueError, "hash or sequence"):
            OfflineOrderJournal(self.path)


if __name__ == "__main__":
    unittest.main()
