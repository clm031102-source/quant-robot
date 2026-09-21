from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, intent, policy


class OfflinePortfolioValuationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "valuation.sqlite"
        self.book = OfflineOrderJournal.create(self.path, initial_cash="2600", initial_positions={SYMBOL: 100},
            commission_bps="0.5", minimum_commission="5", admission_policy=policy())
        self.addCleanup(lambda: self.book.close())
        self.start(NOW)

    def start(self, now):
        packet = context(self.book, now)
        packet.update(instruments={s: instrument(s) for s in (SYMBOL, OTHER)}, sellable_positions=self.book.snapshot()["positions"])
        self.book.begin_session(packet, clock=lambda: now)

    def value(self, price="4", *, now=NOW, packet=None):
        if packet is None:
            packet = context(self.book, now)
            packet["quotes"][SYMBOL].update(bid=price, ask=price)
        return self.book.record_valuation(packet, clock=lambda: now)

    def last(self):
        return self.book.snapshot()["portfolio_valuation"]["last_valid"]

    def test_loss_limit_is_detected_without_any_new_order(self):
        self.assertTrue(self.value("3.4"))
        snap = self.book.snapshot()
        self.assertEqual(snap["orders"], {})
        self.assertEqual(Decimal(self.last()["book_equity"]), 2940)
        self.assertEqual(Decimal(self.last()["book_loss_from_open"]), 60)
        self.assertTrue(snap["risk_session"]["risk_stop"])
        self.assertFalse(snap["executable"])

    def test_missing_quote_preserves_last_valid_value_and_pauses_new_risk(self):
        self.value()
        before = self.last()
        packet = context(self.book)
        del packet["quotes"][SYMBOL]
        with self.assertRaisesRegex(ValueError, "missing quote"):
            self.value(packet=packet)
        self.assertEqual(self.last(), before)
        self.assertTrue(self.book.snapshot()["portfolio_valuation"]["unavailable"])
        with self.assertRaisesRegex(ValueError, "paused"):
            self.book.admit(intent(), context(self.book), clock=lambda: NOW)

    def test_valuation_keeps_running_under_operator_stop(self):
        self.book.set_kill_switch(True, reason="synthetic operator stop")
        self.assertTrue(self.value("3.9"))
        self.assertEqual(Decimal(self.last()["book_equity"]), 2990)
        self.assertTrue(self.book.snapshot()["kill_switch"])

    def test_quote_recovery_clears_only_valuation_fault(self):
        self.book.admit(intent(), context(self.book), clock=lambda: NOW)
        self.book.report_status("one", "unknown", "UNKNOWN", 0)
        bad = context(self.book)
        del bad["quotes"][SYMBOL]
        with self.assertRaises(ValueError):
            self.value(packet=bad)
        self.value()
        snap = self.book.snapshot()
        self.assertFalse(snap["portfolio_valuation"]["unavailable"])
        self.assertIn("unknown_order_state", snap["faults"])
        self.assertTrue(snap["paused"])
        self.assertFalse(self.last()["account_state_known"])
        self.assertEqual(self.last()["unknown_order_ids"], ["one"])

    def test_order_reconciliation_cannot_clear_missing_price_fault(self):
        bad = context(self.book)
        bad["quotes"] = {}
        with self.assertRaises(ValueError):
            self.value(packet=bad)
        snap = self.book.snapshot()
        self.book.reconcile(snapshot_id="complete", expected_sequence=snap["sequence"], cash=snap["cash"],
            positions=snap["positions"], orders={})
        self.assertTrue(self.book.snapshot()["paused"])
        self.value()
        self.assertFalse(self.book.snapshot()["paused"])

    def test_loss_stop_and_peak_survive_rebound_and_restart(self):
        self.value("4.2")
        self.value("3.4", now=NOW + timedelta(seconds=1))
        self.book.close()
        self.book = OfflineOrderJournal(self.path)
        self.value("4", now=NOW + timedelta(seconds=2))
        self.assertTrue(self.book.snapshot()["risk_session"]["risk_stop"])
        self.assertEqual(Decimal(self.last()["book_equity_peak"]), 3020)
        self.assertEqual(Decimal(self.last()["book_peak_drawdown"]), 20)
        self.assertEqual(Decimal(self.last()["opening_equity"]), 3000)

    def test_pending_cash_is_not_subtracted_from_book_equity(self):
        self.book.admit(intent(), context(self.book), clock=lambda: NOW)
        self.value()
        self.assertEqual(Decimal(self.last()["book_equity"]), 3000)
        self.assertEqual(Decimal(self.last()["pending_cost_bound"]), 5)
        self.assertEqual(Decimal(self.last()["projected_daily_loss"]), 5)
        self.assertEqual(Decimal(self.last()["gross_committed_exposure"]), 800)
        self.assertEqual(Decimal(self.book.snapshot()["reserved_cash"]), 405)

    def test_partial_fill_fee_is_not_charged_again_in_pending_cost_bound(self):
        self.book.admit(intent(), context(self.book), clock=lambda: NOW)
        self.book.fill("one", "part", 40, "4")
        self.value()
        self.assertEqual(Decimal(self.last()["book_equity"]), 2995)
        self.assertEqual(Decimal(self.last()["pending_cost_bound"]), 0)
        self.assertEqual(Decimal(self.last()["projected_daily_loss"]), 5)
        self.assertEqual(Decimal(self.book.snapshot()["reserved_cash"]), 240)

    def test_pending_order_cost_can_trigger_loss_stop_before_any_fill(self):
        self.book.admit(intent(code=OTHER), context(self.book), clock=lambda: NOW)
        self.value("3.45")
        self.assertEqual(Decimal(self.last()["book_loss_from_open"]), 55)
        self.assertEqual(Decimal(self.last()["projected_daily_loss"]), 60)
        self.assertTrue(self.book.snapshot()["risk_session"]["risk_stop"])

    def test_monitoring_uses_fresh_quotes_outside_order_submission_windows(self):
        lunch = NOW.replace(hour=12)
        self.value("3.9", now=lunch)
        self.assertEqual(Decimal(self.last()["book_equity"]), 2990)
        with self.assertRaisesRegex(ValueError, "outside"):
            self.book.admit(intent(now=lunch), context(self.book, lunch), clock=lambda: lunch)

    def test_missing_quote_for_an_active_unheld_order_blocks_complete_risk_valuation(self):
        self.book.admit(intent(code=OTHER), context(self.book), clock=lambda: NOW)
        packet = context(self.book)
        del packet["quotes"][OTHER]
        with self.assertRaisesRegex(ValueError, "missing quote"):
            self.value(packet=packet)
        self.assertIsNone(self.last())

    def test_invalid_halted_crossed_and_stale_quotes_do_not_create_a_new_value(self):
        self.value()
        before = self.last()
        for changes in ({"trade_status": "HALTED"}, {"bid": "4.1", "ask": "4"},
                {"timestamp": (NOW - timedelta(seconds=31)).isoformat()}, {"ask": "4.1"}):
            packet = context(self.book)
            packet["quotes"][SYMBOL].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.value(packet=packet)
        self.assertEqual(before, self.last())
        self.assertTrue(self.book.snapshot()["paused"])

    def test_regressive_quote_timestamp_is_not_accepted_even_inside_age_limit(self):
        later = NOW + timedelta(seconds=10)
        self.value(now=later)
        packet = context(self.book, later + timedelta(seconds=1))
        packet["quotes"][SYMBOL]["timestamp"] = (NOW + timedelta(seconds=5)).isoformat()
        with self.assertRaisesRegex(ValueError, "regressed"):
            self.value(now=later + timedelta(seconds=1), packet=packet)

    def test_stale_anchor_does_not_masquerade_as_market_data_failure(self):
        self.value()
        stale = context(self.book)
        self.book.set_kill_switch(True, reason="change journal")
        with self.assertRaisesRegex(ValueError, "stale journal anchor"):
            self.value(packet=stale)
        self.assertFalse(self.book.snapshot()["portfolio_valuation"]["unavailable"])
        self.assertEqual(self.book.snapshot()["faults"], [])

    def test_old_valuation_is_labelled_after_account_or_order_state_changes(self):
        self.value()
        self.assertTrue(self.book.snapshot()["portfolio_valuation"]["matches_current_journal"])
        self.book.admit(intent(), context(self.book), clock=lambda: NOW)
        self.assertFalse(self.book.snapshot()["portfolio_valuation"]["matches_current_journal"])
        self.value()
        self.assertTrue(self.book.snapshot()["portfolio_valuation"]["matches_current_journal"])

    def test_malformed_packet_is_audited_without_logging_arbitrary_values(self):
        packet = context(self.book)
        packet.pop("as_of")
        packet["untrusted_secret"] = object()
        with self.assertRaises(ValueError):
            self.value(packet=packet)
        snap = self.book.snapshot()
        rejected = snap["portfolio_valuation"]["last_rejection"]["rejected_request"]
        self.assertNotIn("untrusted_secret", str(rejected))
        self.assertTrue(snap["portfolio_valuation"]["unavailable"])

    def test_new_session_with_valid_opening_quotes_can_resolve_prior_data_fault(self):
        packet = context(self.book)
        packet["quotes"] = {}
        with self.assertRaises(ValueError):
            self.value(packet=packet)
        tomorrow = NOW + timedelta(days=1)
        self.start(tomorrow)
        self.assertFalse(self.book.snapshot()["paused"])
        self.assertIsNone(self.last())
        self.value(now=tomorrow)
        self.assertEqual(Decimal(self.last()["opening_equity"]), 3000)

    def test_new_session_cannot_clear_operator_stop_with_fresh_quotes(self):
        self.book.set_kill_switch(True, reason="operator")
        with self.assertRaisesRegex(ValueError, "paused"):
            self.start(NOW + timedelta(days=1))
        self.assertTrue(self.book.snapshot()["kill_switch"])

    def test_new_session_cannot_clear_quote_fault_with_unsupported_halted_marks(self):
        packet = context(self.book)
        packet["quotes"] = {}
        with self.assertRaises(ValueError):
            self.value(packet=packet)
        tomorrow = NOW + timedelta(days=1)
        packet = context(self.book, tomorrow)
        packet.update(instruments={s: instrument(s) for s in (SYMBOL, OTHER)}, sellable_positions={SYMBOL: 100})
        packet["quotes"][SYMBOL]["trade_status"] = "HALTED"
        with self.assertRaisesRegex(ValueError, "non-trading"):
            self.book.begin_session(packet, clock=lambda: tomorrow)
        snap = self.book.snapshot()
        self.assertTrue(snap["portfolio_valuation"]["unavailable"])
        self.assertEqual(snap["risk_session"]["session_date"], NOW.date().isoformat())

    def test_new_order_cannot_value_another_held_instrument_using_halted_quotes(self):
        packet = context(self.book)
        packet["quotes"][SYMBOL]["trade_status"] = "HALTED"
        with self.assertRaisesRegex(ValueError, "non-trading"):
            self.book.admit(intent(code=OTHER), packet, clock=lambda: NOW)
        self.assertFalse(self.book.snapshot()["orders"])

    def test_session_mismatch_and_backward_clock_preserve_valid_history(self):
        self.value(now=NOW + timedelta(seconds=10))
        before = self.last()
        with self.assertRaisesRegex(ValueError, "backward"):
            self.value(now=NOW)
        with self.assertRaisesRegex(ValueError, "session"):
            self.value(now=NOW + timedelta(days=1))
        self.assertEqual(self.last(), before)
        self.assertFalse(self.book.snapshot()["portfolio_valuation"]["unavailable"])

    def test_new_exposure_breach_stops_without_submitting_a_new_order(self):
        self.value("10.01")
        self.assertIn("single_position", self.last()["breaches"])
        self.assertTrue(self.book.snapshot()["risk_session"]["risk_stop"])
        self.assertEqual(self.book.snapshot()["orders"], {})

    def test_cash_only_account_can_be_valued_without_invented_quotes(self):
        with OfflineOrderJournal.create(self.path.parent / "cash.sqlite", initial_cash="3000", initial_positions={},
                commission_bps="0.5", minimum_commission="5", admission_policy=policy()) as cash:
            packet = context(cash)
            packet.update(instruments={s: instrument(s) for s in (SYMBOL, OTHER)}, sellable_positions={})
            cash.begin_session(packet, clock=lambda: NOW)
            packet = context(cash)
            packet["quotes"] = {}
            cash.record_valuation(packet, clock=lambda: NOW)
            self.assertEqual(Decimal(cash.snapshot()["portfolio_valuation"]["last_valid"]["book_equity"]), 3000)

    def test_order_checks_cannot_use_quotes_older_than_latest_valuation(self):
        later = NOW + timedelta(seconds=10)
        self.value(now=later)
        packet = context(self.book, later + timedelta(seconds=1))
        packet["quotes"][SYMBOL]["timestamp"] = NOW.isoformat()
        with self.assertRaisesRegex(ValueError, "valuation"):
            self.book.admit(intent(now=later), packet, clock=lambda: later + timedelta(seconds=1))

    def test_order_clock_cannot_go_back_before_latest_valuation(self):
        self.value(now=NOW + timedelta(seconds=10))
        with self.assertRaisesRegex(ValueError, "valuation"):
            self.book.admit(intent(), context(self.book), clock=lambda: NOW)


if __name__ == "__main__":
    unittest.main()
