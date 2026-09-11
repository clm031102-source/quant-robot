from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, intent, policy


def timeout_policy():
    return {"schema_version": 1, "mode": "offline_fixture_only", "policy_id": "fixture-timeouts",
        "ack_timeout_seconds": 20, "cancel_timeout_seconds": 30, "day_order_cutoff": "15:00"}


class OfflineOrderTimeoutTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "timeouts.sqlite"
        self.book = OfflineOrderJournal.create(self.path, initial_cash="3000", initial_positions={},
            commission_bps="0.5", minimum_commission="5", admission_policy=policy(), timeout_policy=timeout_policy())
        self.addCleanup(lambda: self.book.close())
        packet = context(self.book)
        packet.update(instruments={s: instrument(s) for s in (SYMBOL, OTHER)}, sellable_positions={})
        self.book.begin_session(packet, clock=lambda: NOW)
        self.book.admit(intent(), context(self.book), clock=lambda: NOW)

    def prepare(self):
        self.book.prepare_dispatch("one", "prepare-one", context(self.book), clock=lambda: NOW)

    def monitor(self, seconds):
        return self.book.monitor_timeouts(clock=lambda: NOW + timedelta(seconds=seconds))

    def test_missing_acknowledgement_becomes_unknown_without_releasing_cash(self):
        self.prepare()
        self.assertFalse(self.monitor(19))
        self.assertTrue(self.monitor(20))
        snap = self.book.snapshot()
        self.assertEqual(snap["orders"]["one"]["status"], "UNKNOWN")
        self.assertEqual(snap["orders"]["one"]["timeout"]["reason"], "acknowledgement_timeout")
        self.assertEqual(Decimal(snap["reserved_cash"]), 405)
        self.assertTrue(snap["paused"])

    def test_received_ack_is_not_cancelled_at_local_signal_expiry(self):
        self.prepare()
        self.book.report_status("one", "ack", "ACCEPTED", 0)
        self.assertFalse(self.monitor(121))
        self.assertEqual(self.book.snapshot()["orders"]["one"]["status"], "ACCEPTED")

    def test_unconfirmed_cancel_times_out_and_retains_reservation(self):
        self.prepare()
        self.book.report_status("one", "ack", "ACCEPTED", 0)
        self.book.request_cancel("one", clock=lambda: NOW + timedelta(seconds=10))
        self.assertFalse(self.monitor(39))
        self.assertTrue(self.monitor(40))
        snap = self.book.snapshot()
        self.assertEqual(snap["orders"]["one"]["timeout"]["reason"], "cancel_confirmation_timeout")
        self.assertEqual(Decimal(snap["reserved_cash"]), 405)

    def test_day_expiry_uses_explicit_order_cutoff_not_submission_window(self):
        self.prepare()
        self.book.report_status("one", "ack", "ACCEPTED", 0)
        self.assertFalse(self.monitor(4 * 3600 + 57 * 60))
        self.assertTrue(self.monitor(5 * 3600))
        self.assertEqual(self.book.snapshot()["orders"]["one"]["timeout"]["reason"], "day_order_expired")

    def test_unprepared_expired_intent_is_quarantined_with_identity_and_cash_retained(self):
        self.assertTrue(self.monitor(120))
        snap = self.book.snapshot()
        self.assertEqual(snap["orders"]["one"]["timeout"]["reason"], "unprepared_intent_expired")
        self.assertEqual(Decimal(snap["reserved_cash"]), 405)
        with self.assertRaises(ValueError):
            self.book.prepare_dispatch("one", "late", context(self.book), clock=lambda: NOW)

    def test_repeated_cancel_does_not_extend_its_deadline(self):
        self.prepare()
        self.book.request_cancel("one", clock=lambda: NOW)
        first = self.book.snapshot()["orders"]["one"]["cancel_request"]
        self.assertFalse(self.book.request_cancel("one", clock=lambda: NOW + timedelta(seconds=29)))
        self.assertEqual(first, self.book.snapshot()["orders"]["one"]["cancel_request"])
        self.assertTrue(self.monitor(30))

    def test_repeated_timeout_sweep_is_idempotent(self):
        self.prepare()
        self.monitor(20)
        sequence = self.book.snapshot()["sequence"]
        self.assertFalse(self.monitor(21))
        self.assertEqual(sequence, self.book.snapshot()["sequence"])

    def test_timeout_keeps_order_unknown_after_late_ack_until_complete_reconciliation(self):
        self.prepare()
        self.monitor(20)
        self.book.report_status("one", "late-ack", "ACCEPTED", 0)
        self.assertEqual(self.book.snapshot()["orders"]["one"]["status"], "UNKNOWN")
        self.reconcile("ACCEPTED")
        self.assertFalse(self.book.snapshot()["paused"])
        self.assertFalse(self.monitor(30))

    def reconcile(self, status):
        snap = self.book.snapshot()
        order = snap["orders"]["one"]
        row = {k: order[k] for k in ["filled_quantity", "filled_notional", "commission"]}
        row["status"] = status
        self.book.reconcile(snapshot_id="complete-" + str(snap["sequence"]), expected_sequence=snap["sequence"],
            cash=snap["cash"], positions=snap["positions"], orders={"one": row})

    def test_expired_day_does_not_allow_active_reconciliation(self):
        self.prepare()
        self.monitor(5 * 3600)
        with self.assertRaisesRegex(ValueError, "terminal reconciliation"):
            self.reconcile("ACCEPTED")

    def test_unknown_ack_order_is_also_marked_expired_when_the_day_ends(self):
        self.prepare()
        self.monitor(20)
        self.assertTrue(self.monitor(5 * 3600))
        with self.assertRaisesRegex(ValueError, "terminal reconciliation"):
            self.reconcile("ACCEPTED")
        self.assertFalse(self.monitor(5 * 3600 + 1))

    def test_unconfirmed_cancel_cannot_be_cleared_by_another_pending_snapshot(self):
        self.prepare()
        self.book.request_cancel("one", clock=lambda: NOW)
        self.monitor(30)
        with self.assertRaisesRegex(ValueError, "terminal reconciliation"):
            self.reconcile("CANCEL_PENDING")

    def test_late_partial_fill_consumes_reserved_cash_and_stays_unknown(self):
        self.prepare()
        self.monitor(20)
        self.book.fill("one", "late", 40, "4")
        snap = self.book.snapshot()
        self.assertEqual(snap["orders"]["one"]["status"], "UNKNOWN")
        self.assertEqual(snap["positions"], {SYMBOL: 40})
        self.assertEqual(Decimal(snap["reserved_cash"]), 240)
        self.assertEqual(Decimal(snap["orders"]["one"]["commission"]), 5)
        self.assertFalse(self.book.fill("one", "late", 40, "4"))

    def test_confirmed_cancel_releases_only_unfilled_reservation_and_fault_requires_reconcile(self):
        self.prepare()
        self.book.request_cancel("one", clock=lambda: NOW)
        self.monitor(30)
        self.book.fill("one", "late", 40, "4")
        self.book.report_status("one", "cancelled", "CANCELLED", 40)
        self.assertEqual(Decimal(self.book.snapshot()["reserved_cash"]), 0)
        self.assertTrue(self.book.snapshot()["paused"])
        self.reconcile("CANCELLED")
        self.assertFalse(self.book.snapshot()["paused"])

    def test_timeout_does_not_erase_operator_stop(self):
        self.prepare()
        self.book.set_kill_switch(True, reason="fixture stop")
        self.monitor(20)
        self.reconcile("ACCEPTED")
        self.assertTrue(self.book.snapshot()["kill_switch"])

    def test_restart_preserves_timeout_policy_deadline_fault_and_reservation(self):
        self.prepare()
        self.monitor(20)
        before = self.book.snapshot()
        self.book.close()
        self.book = OfflineOrderJournal(self.path)
        after = self.book.snapshot()
        self.assertEqual(after["timeout_policy_fingerprint"], before["timeout_policy_fingerprint"])
        self.assertEqual(after["orders"]["one"]["dispatch"], before["orders"]["one"]["dispatch"])
        self.assertEqual(after["orders"]["one"]["timeout"], before["orders"]["one"]["timeout"])
        self.assertEqual(after["reserved_cash"], before["reserved_cash"])
        self.assertTrue(after["paused"])

    def test_clock_before_decision_or_backward_after_timeout_is_rejected(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "precedes"):
            self.monitor(-1)
        with self.assertRaisesRegex(ValueError, "precedes"):
            self.book.request_cancel("one", clock=lambda: NOW - timedelta(seconds=1))
        self.monitor(20)
        with self.assertRaisesRegex(ValueError, "backward"):
            self.monitor(19)

    def test_completed_order_is_not_reclassified_by_elapsed_time(self):
        self.prepare()
        self.book.fill("one", "full", 100, "4")
        self.assertFalse(self.monitor(24 * 3600))
        self.assertEqual(self.book.snapshot()["orders"]["one"]["status"], "FILLED")

    def test_legacy_journal_does_not_silently_invent_timeout_defaults(self):
        with OfflineOrderJournal.create(self.path.parent / "legacy.sqlite", initial_cash="1000", initial_positions={},
                commission_bps="0", minimum_commission="0") as legacy:
            with self.assertRaisesRegex(ValueError, "frozen timeout policy"):
                legacy.monitor_timeouts(clock=lambda: NOW)

    def test_invalid_or_non_offline_timeout_policy_is_rejected_before_file_creation(self):
        for index, change in enumerate([{"ack_timeout_seconds": 0}, {"cancel_timeout_seconds": True},
                {"ack_timeout_seconds": 86401}, {"day_order_cutoff": "14:00"},
                {"day_order_cutoff": "15:00:00"}, {"mode": "live"}]):
            path = self.path.parent / (str(index) + ".sqlite")
            bad = {**timeout_policy(), **change}
            with self.subTest(change=change), self.assertRaises(ValueError):
                OfflineOrderJournal.create(path, initial_cash="1000", initial_positions={}, commission_bps="0",
                    minimum_commission="0", admission_policy=policy(), timeout_policy=bad)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
