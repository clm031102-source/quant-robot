from datetime import timedelta
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal
from quant_robot.execution.offline_runtime import OfflineRuntime
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, intent, policy
from tests.unit.test_offline_order_timeouts import timeout_policy
from tests.unit.test_offline_target_compiler import target
from tests.unit.test_offline_runtime import observation


class OfflineExposureStopRuntimeTests(unittest.TestCase):
    def test_real_cli_keeps_stop_causes_and_prepares_one_synthetic_reduction(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cli.sqlite"
            cfg = {**policy(), "schema_version": 2, "max_drawdown": ".08", "capital_limit_cny": "10000",
                "exposure_stop_action": "reduce_only"}
            with OfflineOrderJournal.create(path, initial_cash="9010", initial_positions={SYMBOL: 200},
                    commission_bps="5", minimum_commission="5", admission_policy=cfg, timeout_policy=timeout_policy()) as book:
                packet = context(book)
                packet["quotes"][SYMBOL].update(bid="4.95", ask="4.95")
                packet.update(instruments={code: instrument(code) for code in (SYMBOL, OTHER)}, sellable_positions={SYMBOL: 200})
                book.begin_session(packet, clock=lambda: NOW)
                feed = context(book, NOW + timedelta(seconds=1))
                feed.pop("journal_sequence")
                feed.pop("journal_hash")
                feed["quotes"][SYMBOL].update(bid="5.01", ask="5.01")
                feed["targets"] = [target(book, target_notional_cny="0", limit_price="5.01")]
            feed_path, report_path = path.with_suffix(".feed.json"), path.with_suffix(".report.json")
            feed_path.write_text(json.dumps(feed), encoding="utf-8")
            result = subprocess.run([sys.executable, "scripts/run_offline_runtime.py", "--journal", str(path),
                "--feed", str(feed_path), "--report", str(report_path), "--max-ticks", "1",
                "--fixture-clock-start", (NOW + timedelta(seconds=1)).isoformat()],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "attention")
            self.assertEqual(report["risk_stop_causes"], ["single_position"])
            self.assertEqual(report["counts_as_forward_paper_days"], 0)
            snapshot = OfflineOrderJournal.inspect_snapshot(path)
            self.assertIn("dispatch", snapshot["orders"]["target-one"])
            self.assertEqual(snapshot["orders"]["target-one"]["filled_quantity"], 0)
            self.assertTrue(snapshot["risk_session"]["risk_stop"])

    def test_driver_prepares_only_guarded_reductions_while_reporting_attention(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "exposure-runtime.sqlite"
            cfg = {**policy(), "schema_version": 2, "max_drawdown": ".08", "capital_limit_cny": "10000",
                "exposure_stop_action": "reduce_only"}
            with OfflineOrderJournal.create(path, initial_cash="9010", initial_positions={SYMBOL: 200},
                    commission_bps="5", minimum_commission="5", admission_policy=cfg, timeout_policy=timeout_policy()) as book:
                packet = context(book)
                packet["quotes"][SYMBOL].update(bid="4.95", ask="4.95")
                packet.update(instruments={code: instrument(code) for code in (SYMBOL, OTHER)}, sellable_positions={SYMBOL: 200})
                book.begin_session(packet, clock=lambda: NOW)
            now = NOW + timedelta(seconds=1)
            with OfflineRuntime(path, clock=lambda: now) as runtime:
                feed = observation(runtime, now)
                feed["quotes"][SYMBOL].update(bid="5.01", ask="5.01")
                feed["intents"] = [intent("buy-denied", code=OTHER)]
                feed["targets"] = [target(runtime.book, target_notional_cny="0", limit_price="5.01")]
                report = runtime.tick(feed)
                snap = runtime.book.snapshot()
                self.assertEqual(set(snap["orders"]), {"target-one"})
                row = snap["orders"]["target-one"]
                self.assertIn("dispatch", row)
                self.assertEqual(row["filled_quantity"], 0)
                self.assertEqual(report["status"], "attention")
                self.assertTrue(report["paused"])
                self.assertEqual(report["counts_as_forward_paper_days"], 0)
                self.assertFalse(report["executable"])
                runtime.tick(feed)
                self.assertEqual(runtime.book.snapshot()["orders"], snap["orders"])
            with OfflineRuntime(path, clock=lambda: now) as restarted:
                feed.pop("targets")
                feed.pop("intents")
                report = restarted.tick(feed)
                self.assertEqual(restarted.book.snapshot()["orders"]["target-one"]["status"], "UNKNOWN")
                self.assertFalse(any(step["stage"] == "dispatch" for step in report["steps"]))


if __name__ == "__main__":
    unittest.main()
