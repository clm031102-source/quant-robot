import json
from pathlib import Path
import tempfile
import unittest

from quant_robot.execution.offline_runtime_health import health_record, validate_health, read_health, SupervisorPermit
from quant_robot.execution.offline_runtime import OfflineRuntime
from tests.unit.test_offline_runtime import create_book, observation
from tests.unit.test_offline_order_admission import NOW, intent


class OfflineRuntimeHealthTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name)/"journal.sqlite"
        self.health = Path(temporary.name)/"health.json"
        self.identity = dict(instance_id="a"*32, journal_path=str(self.path.resolve()), genesis_hash="b"*64)

    def record(self, **changes):
        result = health_record("supervisor", **self.identity, process_id=123, phase="running", monotonic_ns=10000000000)
        result.update(changes)
        return result

    def validate(self, value, **changes):
        return validate_health(value, role="supervisor", **self.identity, process_id=123,
            now_ns=changes.get("now_ns", 11000000000), max_age_seconds=2)

    def test_market_clock_is_not_used_for_process_freshness(self):
        self.validate(self.record(market_observed_at="2099-01-01T00:00:00+00:00"))
        with self.assertRaisesRegex(ValueError, "stale"):
            self.validate(self.record(), now_ns=14000000000)

    def test_old_instance_wrong_process_or_journal_is_rejected(self):
        for field, value in (("instance_id", "c"*32), ("process_id", 456),
                ("journal_path", str(self.path.parent/"other.sqlite")), ("genesis_hash", "d"*64)):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "identity"):
                self.validate(self.record(**{field:value}))

    def test_future_non_finite_or_boolean_time_is_rejected(self):
        for value in (True, float("nan"), -1, 12000000000):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.validate(self.record(updated_monotonic_ns=value))

    def test_invalid_schema_role_or_live_claim_is_rejected(self):
        for change in ({"schema_version":2}, {"role":"worker"}, {"executable":True}, {"mode":"live"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.validate(self.record(**change))

    def test_bounded_reader_rejects_missing_malformed_and_oversized_evidence(self):
        with self.assertRaises(OSError): read_health(self.health)
        for value in ("{", "x"*65537, "[]"):
            self.health.write_text(value)
            with self.subTest(length=len(value)), self.assertRaises(ValueError): read_health(self.health)

    def test_permit_requires_fresh_running_supervisor(self):
        permit = SupervisorPermit(self.health, **self.identity, process_id=123, max_age_seconds=2,
            monotonic_ns=lambda:11000000000)
        self.health.write_text(json.dumps(self.record()))
        self.assertIsNone(permit())
        self.health.write_text(json.dumps(self.record(phase="stopped")))
        with self.assertRaisesRegex(ValueError, "running"): permit()

    def runtime(self, guard):
        create_book(self.path)
        runtime = OfflineRuntime(self.path, clock=lambda:NOW, admission_guard=guard)
        self.addCleanup(runtime.close)
        return runtime

    def test_lost_supervisor_blocks_new_intent_but_still_records_valuation(self):
        lost = False
        runtime = self.runtime(lambda:"supervisor stale" if lost else None)
        runtime.tick(observation(runtime, opening=True))
        lost = True
        packet = observation(runtime); packet["intents"]=[intent()]
        result = runtime.tick(packet)
        state = runtime.book.snapshot()
        self.assertEqual(result["status"], "attention")
        self.assertIn("runtime_supervision_requires_review",state["faults"])
        self.assertEqual(state["orders"],{})
        self.assertIsNotNone(state["portfolio_valuation"]["last_valid"])

    def test_health_is_rechecked_before_dispatch_after_admission(self):
        calls = 0
        def guard():
            nonlocal calls
            calls += 1
            return "supervisor stale" if calls >= 3 else None
        runtime = self.runtime(guard)
        packet = observation(runtime, opening=True);packet["intents"]=[intent()]
        runtime.tick(packet)
        state=runtime.book.snapshot()
        self.assertIn("one",state["orders"])
        self.assertNotIn("dispatch",state["orders"]["one"])
        self.assertTrue(state["paused"])

    def test_lost_supervisor_does_not_discard_real_explicit_fixture_fill(self):
        lost = False
        runtime=self.runtime(lambda:"stale" if lost else None)
        packet=observation(runtime,opening=True);packet["intents"]=[intent()]
        runtime.tick(packet);lost=True
        packet=observation(runtime);packet['receipts']=[dict(kind="fill",order_id="one",fill_id="actual",quantity=100,price="4")]
        runtime.tick(packet)
        self.assertEqual(runtime.book.snapshot()["orders"]["one"]["filled_quantity"],100)
        self.assertTrue(runtime.book.snapshot()["paused"])

    def test_guard_exception_is_latched_and_repeated_failures_do_not_spam_faults(self):
        def guard(): raise OSError("missing permit")
        runtime=self.runtime(guard)
        runtime.tick(observation(runtime,opening=True))
        runtime.tick(observation(runtime))
        events=[json.loads(row[0]) for row in runtime.book._db.execute("SELECT payload FROM events")]
        self.assertEqual(sum(e["kind"]=="FAULT" for e in events),1)
        with self.assertRaisesRegex(ValueError,"reconciliation"):
            runtime.book.set_kill_switch(False,reason="cannot bypass supervision fault")


if __name__ == "__main__": unittest.main()
