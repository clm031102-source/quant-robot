from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
import json

from quant_robot.execution.offline_journal import OfflineOrderJournal
from quant_robot.execution.offline_runtime import OfflineRuntime, read_observation, run_loop
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, intent, policy
from tests.unit.test_offline_order_timeouts import timeout_policy
from tests.unit.test_offline_dividends import dividend_policy, extended_policy
from tests.unit.test_offline_conversions import conversion_policy


def create_book(path):
    with OfflineOrderJournal.create(path, initial_cash="2600", initial_positions={SYMBOL: 100}, commission_bps="0.5",
            minimum_commission="5", admission_policy=policy(), timeout_policy=timeout_policy()):
        pass


def observation(runtime, now=NOW, *, opening=False):
    packet = context(runtime.book, now)
    packet.pop("journal_sequence"); packet.pop("journal_hash")
    if opening:
        packet["opening"] = {"instruments": {s: instrument(s) for s in (SYMBOL, OTHER)}, "sellable_positions": {SYMBOL: 100}}
    return packet


class OfflineRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)/"runtime.sqlite"
        create_book(self.path)
        self.now = NOW
        self.runtime = OfflineRuntime(self.path, clock=lambda: self.now)

    def tearDown(self):
        self.runtime.close()
        self.directory.cleanup()

    def test_tick_initializes_then_values_without_any_new_order(self):
        report = self.runtime.tick(observation(self.runtime, opening=True))
        self.assertEqual(report["status"], "ready")
        self.assertFalse(report["executable"])
        self.assertEqual(report["counts_as_forward_paper_days"], 0)
        self.assertEqual(Decimal(self.runtime.book.snapshot()["portfolio_valuation"]["last_valid"]["book_equity"]), 3000)

    def test_missing_feed_preserves_last_value_and_pauses_even_without_orders(self):
        self.runtime.tick(observation(self.runtime, opening=True))
        previous = self.runtime.book.snapshot()["portfolio_valuation"]["last_valid"]
        self.now += timedelta(seconds=31)
        report = self.runtime.tick(None)
        self.assertEqual(report["status"], "attention")
        snap = self.runtime.book.snapshot()
        self.assertTrue(snap["paused"])
        self.assertEqual(snap["portfolio_valuation"]["last_valid"], previous)

    def test_driver_prepares_but_never_invents_ack_or_fill(self):
        packet = observation(self.runtime, opening=True)
        packet["intents"] = [intent()]
        self.runtime.tick(packet)
        snap = self.runtime.book.snapshot()
        self.assertEqual(snap["orders"]["one"]["status"], "PENDING")
        self.assertIn("dispatch", snap["orders"]["one"])
        self.assertEqual(snap["orders"]["one"]["filled_quantity"], 0)
        self.assertEqual(Decimal(snap["cash"]), 2600)

    def test_timeout_processing_continues_when_feed_disappears(self):
        packet = observation(self.runtime, opening=True)
        packet["intents"] = [intent()]
        self.runtime.tick(packet)
        self.now += timedelta(seconds=21)
        self.runtime.tick(None)
        snap = self.runtime.book.snapshot()
        self.assertEqual(snap["orders"]["one"]["status"], "UNKNOWN")
        self.assertEqual(Decimal(snap["reserved_cash"]), 405)

    def test_explicit_receipts_are_processed_once_before_risk_is_recomputed(self):
        packet = observation(self.runtime, opening=True)
        packet["intents"] = [intent()]
        self.runtime.tick(packet)
        self.now += timedelta(seconds=10)
        packet = observation(self.runtime, self.now)
        packet["receipts"] = [{"kind": "fill", "order_id": "one", "fill_id": "partial", "quantity": 40, "price": "4"}]
        self.runtime.tick(packet)
        cash = self.runtime.book.snapshot()["cash"]
        self.runtime.tick(packet)
        snap = self.runtime.book.snapshot()
        self.assertEqual(snap["cash"], cash)
        self.assertEqual(snap["orders"]["one"]["filled_quantity"], 40)
        self.assertEqual(Decimal(snap["portfolio_valuation"]["last_valid"]["book_equity"]), 2995)

    def test_second_driver_is_rejected_before_it_can_quarantine_the_first_driver_orders(self):
        packet = observation(self.runtime, opening=True)
        packet["intents"] = [intent()]
        self.runtime.tick(packet)
        with self.assertRaisesRegex(ValueError, "driver"):
            with OfflineRuntime(self.path, clock=lambda: self.now):
                pass
        self.assertEqual(self.runtime.book.snapshot()["orders"]["one"]["status"], "PENDING")

    def test_malformed_account_receipt_pauses_before_new_intent_admission(self):
        packet = observation(self.runtime, opening=True)
        packet["receipts"] = [{"kind": "unrecognized-fill", "quantity": 100}]
        packet["intents"] = [intent()]
        self.runtime.tick(packet)
        snap = self.runtime.book.snapshot()
        self.assertTrue(snap["paused"])
        self.assertEqual(snap["orders"], {})
        self.assertIn("runtime_receipt_requires_review", snap["faults"])

    def test_only_complete_reconciliation_resolves_a_malformed_receipt_fault(self):
        packet = observation(self.runtime, opening=True)
        packet["receipts"] = [{"kind": "invalid"}]
        self.runtime.tick(packet)
        snap = self.runtime.book.snapshot()
        packet = observation(self.runtime, opening=True)
        packet["receipts"] = [{"kind": "reconcile", "snapshot_id": "full", "expected_sequence": snap["sequence"],
            "cash": snap["cash"], "positions": snap["positions"], "orders": {}}]
        self.assertEqual(self.runtime.tick(packet)["status"], "ready")
        self.assertFalse(self.runtime.book.snapshot()["paused"])

    def test_external_reconciliation_anchor_is_not_rewritten_by_the_driver(self):
        self.runtime.tick(observation(self.runtime, opening=True))
        snap = self.runtime.book.snapshot()
        packet = observation(self.runtime)
        packet["receipts"] = [{"kind": "reconcile", "snapshot_id": "stale", "expected_sequence": snap["sequence"]-1,
            "cash": snap["cash"], "positions": snap["positions"], "orders": {}}]
        report = self.runtime.tick(packet)
        self.assertTrue(any("stale reconciliation" in step.get("reason", "") for step in report["steps"]))
        self.assertTrue(self.runtime.book.snapshot()["paused"])

    def test_repeated_intent_is_not_readmitted_or_prepared_again(self):
        packet = observation(self.runtime, opening=True)
        packet["intents"] = [intent()]
        self.runtime.tick(packet)
        original = self.runtime.book.snapshot()["orders"]
        report = self.runtime.tick(packet)
        self.assertEqual(self.runtime.book.snapshot()["orders"], original)
        self.assertTrue(any(s["status"] == "already_attempted" for s in report["steps"]))
        self.assertFalse(any(s["stage"] == "dispatch" for s in report["steps"]))

    def test_rejected_intent_is_not_retried_with_the_same_identity(self):
        packet = observation(self.runtime, opening=True)
        packet["intents"] = [intent(quantity=101)]
        self.runtime.tick(packet)
        report = self.runtime.tick(packet)
        self.assertTrue(any(s["status"] == "already_attempted" for s in report["steps"]))
        self.assertEqual(self.runtime.book.snapshot()["orders"], {})

    def test_clock_is_rechecked_inside_dispatch_after_a_slow_stage(self):
        packet = observation(self.runtime, opening=True)
        packet["intents"] = [intent()]
        original = self.runtime.book.prepare_dispatch
        def delayed(*args, **kwargs):
            self.now += timedelta(seconds=31)
            return original(*args, **kwargs)
        self.runtime.book.prepare_dispatch = delayed
        report = self.runtime.tick(packet)
        self.assertEqual(report["status"], "attention")
        self.assertNotIn("dispatch", self.runtime.book.snapshot()["orders"]["one"])
        self.assertEqual(Decimal(self.runtime.book.snapshot()["reserved_cash"]), 405)

    def test_fresh_feed_restores_valuation_without_releasing_operator_stop(self):
        self.runtime.tick(observation(self.runtime, opening=True))
        self.runtime.book.set_kill_switch(True, reason="operator")
        self.runtime.tick(None)
        self.now += timedelta(seconds=1)
        self.runtime.tick(observation(self.runtime, self.now))
        snap = self.runtime.book.snapshot()
        self.assertTrue(snap["kill_switch"])
        self.assertFalse(snap["portfolio_valuation"]["unavailable"])

    def test_future_or_stale_quotes_are_not_given_fresh_timestamps(self):
        self.runtime.tick(observation(self.runtime, opening=True))
        for delta in (-31, 1):
            packet = observation(self.runtime)
            packet["quotes"][SYMBOL]["timestamp"] = (NOW + timedelta(seconds=delta)).isoformat()
            report = self.runtime.tick(packet)
            self.assertEqual(report["status"], "attention")
            self.assertTrue(self.runtime.book.snapshot()["portfolio_valuation"]["unavailable"])

    def test_non_synthetic_envelope_cannot_deliver_account_receipts(self):
        self.runtime.tick(observation(self.runtime, opening=True))
        packet = observation(self.runtime)
        packet["mode"] = "live"
        packet["intents"] = [intent()]
        report = self.runtime.tick(packet)
        self.assertEqual(report["feed_status"], "invalid")
        self.assertEqual(self.runtime.book.snapshot()["orders"], {})

    def test_restart_does_not_automatically_resend_an_ambiguous_order(self):
        packet = observation(self.runtime, opening=True)
        packet["intents"] = [intent()]
        self.runtime.tick(packet)
        self.runtime.close()
        self.runtime = OfflineRuntime(self.path, clock=lambda: self.now)
        self.runtime.tick(packet)
        row = self.runtime.book.snapshot()["orders"]["one"]
        self.assertEqual(row["status"], "UNKNOWN")
        self.assertEqual(row["filled_quantity"], 0)

    def test_repeated_cancel_request_does_not_extend_deadline(self):
        packet = observation(self.runtime, opening=True)
        packet["intents"] = [intent()]
        self.runtime.tick(packet)
        self.now += timedelta(seconds=1)
        packet = observation(self.runtime, self.now)
        packet["cancel_requests"] = ["one"]
        self.runtime.tick(packet)
        deadline = self.runtime.book.snapshot()["orders"]["one"]["cancel_request"]["confirmation_deadline"]
        self.now += timedelta(seconds=10)
        packet = observation(self.runtime, self.now)
        packet["cancel_requests"] = ["one"]
        self.runtime.tick(packet)
        self.assertEqual(self.runtime.book.snapshot()["orders"]["one"]["cancel_request"]["confirmation_deadline"], deadline)
        self.now += timedelta(seconds=21)
        self.runtime.tick(None)
        self.assertEqual(self.runtime.book.snapshot()["orders"]["one"]["timeout"]["reason"], "cancel_confirmation_timeout")

    def test_loop_survives_read_failure_and_resumes_with_fresh_feed(self):
        supplied, reports, sleeps = 0, [], []
        def supplier():
            nonlocal supplied
            supplied += 1
            if supplied == 2: raise FileNotFoundError("fixture feed missing")
            return observation(self.runtime, self.now, opening=supplied == 1)
        def report(value):
            reports.append(value)
            self.now += timedelta(seconds=1)
        result = run_loop(self.runtime, supplier, interval_seconds=60, max_ticks=3, sleep=sleeps.append, on_tick=report)
        self.assertEqual(result["ticks"], 3)
        self.assertEqual([r["status"] for r in reports], ["ready", "attention", "ready"])
        self.assertEqual(len(sleeps), 2)
        self.assertTrue(all(0 <= duration <= 60 for duration in sleeps))
        self.assertTrue(all(r["counts_as_forward_paper_days"] == 0 for r in reports))

    def test_observation_file_is_bounded_and_invalid_json_is_rejected(self):
        path = self.path.parent/"feed.json"
        path.write_text(json.dumps({"quotes": "x"*50}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "size"):
            read_observation(path, max_bytes=10)
        path.write_text("broken{", encoding="utf-8")
        with self.assertRaises(ValueError): read_observation(path)

    def test_backward_clock_cannot_append_another_tick(self):
        self.runtime.tick(observation(self.runtime, opening=True))
        sequence = self.runtime.book.snapshot()["sequence"]
        self.now -= timedelta(seconds=1)
        with self.assertRaisesRegex(ValueError, "backward"):
            self.runtime.tick(None)
        self.assertEqual(self.runtime.book.snapshot()["sequence"], sequence)

    def test_configuration_inspection_is_read_only_even_with_active_orders(self):
        packet = observation(self.runtime, opening=True)
        packet["intents"] = [intent()]
        self.runtime.tick(packet)
        sequence = self.runtime.book.snapshot()["sequence"]
        self.assertIsNotNone(OfflineOrderJournal.inspect_configuration(self.path)["timeout_policy"])
        self.assertEqual(self.runtime.book.snapshot()["sequence"], sequence)
        self.assertEqual(self.runtime.book.snapshot()["orders"]["one"]["status"], "PENDING")

    def test_driver_sequences_record_conversion_dividend_opening_and_explicit_cash_credit(self):
        path = self.path.parent/"corporate-runtime.sqlite"
        with OfflineOrderJournal.create(path, initial_cash="2600", initial_positions={SYMBOL: 100}, commission_bps="0.5",
                minimum_commission="5", admission_policy=extended_policy(), timeout_policy=timeout_policy(),
                dividend_policy=dividend_policy(), conversion_policy=conversion_policy()):
            pass
        with OfflineRuntime(path, clock=lambda: self.now) as runtime:
            runtime.tick(observation(runtime, opening=True))
            self.now = NOW.replace(hour=15)
            runtime.tick(observation(runtime, self.now))
            self.assertIn("merge-one", runtime.book.snapshot()["conversions"]["entitlements"])
            self.assertIn("div-one", runtime.book.snapshot()["dividends"]["entitlements"])
            self.now = (NOW + timedelta(days=1)).replace(hour=9)
            runtime.tick(None)
            snap = runtime.book.snapshot()
            self.assertEqual(snap["positions"], {SYMBOL: 50})
            self.assertEqual(Decimal(snap["dividends"]["receivable_total"]), 60)
            self.now = NOW + timedelta(days=2)
            packet = observation(runtime, self.now, opening=True)
            packet["opening"]["sellable_positions"] = {SYMBOL: 50}
            for row in packet["opening"]["instruments"].values(): row["valid_until"] = "2026-09-16"
            packet["quotes"][SYMBOL].update(bid="6.8", ask="6.8", price_basis_id=snap["price_basis"][SYMBOL])
            packet["receipts"] = [{"kind": "dividend_credit", "event_id": "div-one", "receipt_id": "paid", "cash_amount": "60"}]
            report = runtime.tick(packet)
            self.assertEqual(report["status"], "ready")
            self.assertEqual(Decimal(runtime.book.snapshot()["cash"]), 2660)
            self.assertEqual(Decimal(runtime.book.snapshot()["portfolio_valuation"]["last_valid"]["book_equity"]), 3000)

    def test_day_cutoff_does_not_create_a_terminal_order_confirmation(self):
        packet = observation(self.runtime, opening=True)
        packet["intents"] = [intent()]
        self.runtime.tick(packet)
        packet = observation(self.runtime)
        packet["receipts"] = [{"kind": "status", "order_id": "one", "report_id": "ack", "status": "ACCEPTED", "cumulative_quantity": 0}]
        self.runtime.tick(packet)
        self.now = NOW.replace(hour=15)
        self.runtime.tick(None)
        row = self.runtime.book.snapshot()["orders"]["one"]
        self.assertEqual(row["status"], "UNKNOWN")
        self.assertEqual(row["timeout"]["reason"], "day_order_expired")
        self.assertEqual(Decimal(self.runtime.book.snapshot()["reserved_cash"]), 405)

    def test_only_one_retry_is_used_when_valuation_anchor_keeps_changing(self):
        self.runtime.tick(observation(self.runtime, opening=True))
        original = self.runtime.book.record_valuation
        calls = 0
        def racing(packet, **kwargs):
            nonlocal calls
            calls += 1
            self.runtime.book.set_kill_switch(True, reason="concurrent state change")
            return original(packet, **kwargs)
        self.runtime.book.record_valuation = racing
        report = self.runtime.tick(observation(self.runtime))
        self.assertEqual(calls, 2)
        self.assertTrue(any("stale journal anchor" in step.get("reason", "") for step in report["steps"]))

    def test_missing_timeout_policy_is_rejected_without_recovery_side_effects(self):
        path = self.path.parent/"unsupported.sqlite"
        with OfflineOrderJournal.create(path, initial_cash="2600", initial_positions={SYMBOL: 100}, commission_bps="0.5",
                minimum_commission="5", admission_policy=policy()) as book:
            packet = context(book)
            packet.update(instruments={s: instrument(s) for s in (SYMBOL, OTHER)}, sellable_positions={SYMBOL: 100})
            book.begin_session(packet, clock=lambda: NOW)
            book.admit(intent(), context(book), clock=lambda: NOW)
            sequence = book.snapshot()["sequence"]
            with self.assertRaisesRegex(ValueError, "timeout"):
                with OfflineRuntime(path, clock=lambda: NOW): pass
            self.assertEqual(book.snapshot()["sequence"], sequence)
            self.assertEqual(book.snapshot()["orders"]["one"]["status"], "PENDING")

    def test_malformed_reconciliation_status_is_quarantined_instead_of_crashing_the_loop(self):
        packet = observation(self.runtime, opening=True)
        packet["intents"] = [intent()]
        self.runtime.tick(packet)
        snap = self.runtime.book.snapshot()
        packet = observation(self.runtime)
        packet["receipts"] = [{"kind": "reconcile", "snapshot_id": "malformed", "expected_sequence": snap["sequence"],
            "cash": snap["cash"], "positions": snap["positions"],
            "orders": {"one": {"status": [], "filled_quantity": 0, "filled_notional": "0", "commission": "0"}}}]
        self.assertEqual(self.runtime.tick(packet)["status"], "attention")
        self.assertIn("runtime_receipt_requires_review", self.runtime.book.snapshot()["faults"])


if __name__ == "__main__":
    unittest.main()
