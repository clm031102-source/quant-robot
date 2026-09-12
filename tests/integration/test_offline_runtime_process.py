import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from quant_robot.execution.offline_runtime import OfflineRuntime
from tests.unit.test_offline_runtime import create_book, observation
from tests.unit.test_offline_order_admission import NOW, SYMBOL, intent
from datetime import timedelta
from decimal import Decimal


class OfflineRuntimeProcessTests(unittest.TestCase):
    def test_process_held_lease_rejects_second_owner_and_releases_after_forced_exit(self):
        source = """
import sys, time
from pathlib import Path
from quant_robot.execution.offline_runtime import OfflineRuntime
from tests.unit.test_offline_order_admission import NOW
with OfflineRuntime(sys.argv[1], clock=lambda: NOW):
    Path(sys.argv[2]).write_text('ready', encoding='utf-8')
    time.sleep(30)
"""
        with tempfile.TemporaryDirectory() as directory:
            path, ready = Path(directory)/"owned.sqlite", Path(directory)/"ready.txt"
            create_book(path)
            child = subprocess.Popen([sys.executable, "-c", source, str(path), str(ready)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                deadline = time.monotonic() + 15
                while not ready.exists() and child.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(ready.exists())
                self.assertIsNone(child.poll())
                with self.assertRaisesRegex(ValueError, "driver"):
                    with OfflineRuntime(path, clock=lambda: NOW): pass
            finally:
                if child.poll() is None: child.kill()
                child.communicate(timeout=10)
            self.assertTrue(Path(str(path) + ".driver.lock").exists())
            with OfflineRuntime(path, clock=lambda: NOW) as successor:
                self.assertIsNotNone(successor.book)

    def test_cli_runs_multiple_ticks_and_stale_feed_triggers_timeout_without_fills(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path, feed, report = root/"cli.sqlite", root/"feed.json", root/"report.json"
            create_book(path)
            with OfflineRuntime(path, clock=lambda: NOW) as runtime:
                packet = observation(runtime, opening=True)
                packet["intents"] = [intent()]
            feed.write_text(json.dumps(packet), encoding="utf-8")
            legacy = root/"legacy"
            package = legacy/"quant_robot"
            (package/"execution").mkdir(parents=True)
            (package/"__init__.py").write_text("", encoding="utf-8")
            (package/"execution/__init__.py").write_text("", encoding="utf-8")
            (package/"execution/offline_runtime.py").write_text("raise RuntimeError('legacy runtime used')", encoding="utf-8")
            env = {**os.environ, "PYTHONPATH": str(legacy)}
            result = subprocess.run([sys.executable, "scripts/run_offline_runtime.py", "--journal", str(path), "--feed", str(feed),
                "--report", str(report), "--max-ticks", "2", "--interval-seconds", "0.01", "--fixture-clock-start", NOW.isoformat(),
                "--fixture-step-seconds", "31"], capture_output=True, text=True, timeout=30, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[-1]["clock_mode"], "synthetic_fixture")
            self.assertIn("order_timeout_requires_reconciliation", rows[-1]["faults"])
            self.assertIn("portfolio_valuation_unavailable", rows[-1]["faults"])
            self.assertEqual(rows[-1]["counts_as_forward_paper_days"], 0)
            self.assertFalse(rows[-1]["executable"])
            self.assertEqual(json.loads(report.read_text(encoding="utf-8")), rows[-1])

    def test_cli_rejects_output_aliases_and_invalid_limits_before_mutating_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            path, feed = Path(directory)/"protected.sqlite", Path(directory)/"feed.json"
            create_book(path)
            feed.write_text("{}", encoding="utf-8")
            original = path.read_bytes()
            for extra in (["--report", str(path)], ["--report", str(feed)], ["--interval-seconds", "0"], ["--max-ticks", "0"]):
                with self.subTest(extra=extra):
                    result = subprocess.run([sys.executable, "scripts/run_offline_runtime.py", "--journal", str(path), "--feed", str(feed), *extra],
                        capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(path.read_bytes(), original)
                    self.assertEqual(feed.read_text(encoding="utf-8"), "{}")

    def test_exit_after_receipt_commit_replays_the_input_without_duplicate_fill(self):
        source = """
import os, sys
from datetime import timedelta
from quant_robot.execution.offline_runtime import OfflineRuntime
from tests.unit.test_offline_runtime import observation
from tests.unit.test_offline_order_admission import NOW, intent
now = NOW
with OfflineRuntime(sys.argv[1], clock=lambda: now) as runtime:
    packet = observation(runtime, opening=True)
    packet['intents'] = [intent()]
    runtime.tick(packet)
    now += timedelta(seconds=10)
    packet = observation(runtime, now)
    packet['receipts'] = [{'kind':'fill','order_id':'one','fill_id':'committed','quantity':100,'price':'4'}]
    fill = runtime.book.fill
    def crash(*args, **kwargs):
        fill(*args, **kwargs)
        os._exit(7)
    runtime.book.fill = crash
    runtime.tick(packet)
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"replay.sqlite"
            create_book(path)
            result = subprocess.run([sys.executable, "-c", source, str(path)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 7, result.stderr)
            now = NOW + timedelta(seconds=10)
            with OfflineRuntime(path, clock=lambda: now) as runtime:
                packet = observation(runtime, now)
                packet["receipts"] = [{"kind": "fill", "order_id": "one", "fill_id": "committed", "quantity": 100, "price": "4"}]
                self.assertEqual(runtime.tick(packet)["status"], "ready")
                snap = runtime.book.snapshot()
                self.assertEqual(snap["positions"], {SYMBOL: 200})
                self.assertEqual(Decimal(snap["cash"]), 2195)
                self.assertEqual(Decimal(snap["portfolio_valuation"]["last_valid"]["book_equity"]), 2995)


if __name__ == "__main__":
    unittest.main()
