from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal
from quant_robot.execution.offline_intent_contract import fingerprint, normalize_policy
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, intent, policy
from tests.unit.test_offline_target_compiler import target


class OfflineExposureStopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.index = 0

    def book(self, *, reduce_only=True, sellable=200, cash="9010", shares=200):
        self.index += 1
        path = Path(self.temp.name) / f"exposure-{self.index}.sqlite"
        cfg = {**policy(), "schema_version": 2, "max_drawdown": ".08", "capital_limit_cny": "10000"}
        if reduce_only:
            cfg["exposure_stop_action"] = "reduce_only"
        book = OfflineOrderJournal.create(path, initial_cash=cash, initial_positions={SYMBOL: shares},
            commission_bps="5", minimum_commission="5", admission_policy=cfg)
        self.addCleanup(book.close)
        packet = self.packet(book, "4.95", NOW)
        packet.update(instruments={code: instrument(code) for code in (SYMBOL, OTHER)},
            sellable_positions={SYMBOL: sellable} if sellable else {})
        book.begin_session(packet, clock=lambda: NOW)
        return book

    @staticmethod
    def packet(book, price="5.01", now=NOW + timedelta(seconds=1)):
        packet = context(book, now)
        packet["quotes"][SYMBOL].update(bid=price, ask=price)
        return packet

    def drift(self, book):
        return book.record_valuation(self.packet(book), clock=lambda: NOW + timedelta(seconds=1))

    def test_explicit_exposure_stop_allows_target_reduction_and_dispatch_without_resetting_pause(self):
        book = self.book()
        self.drift(book)
        self.assertEqual(book.snapshot()["risk_session"]["risk_stop_causes"], ["single_position"])
        request = target(book, target_notional_cny="0", limit_price="5.01")
        book.admit_target(request, self.packet(book), clock=lambda: NOW + timedelta(seconds=1))
        order = book.snapshot()["orders"]["target-one"]
        self.assertEqual((order["side"], order["quantity"]), ("SELL", 200))
        self.assertEqual(order["admission"]["risk"]["exposure_stop_reduction"]["stop_causes"], ["single_position"])
        book.prepare_dispatch("target-one", "reduction-dispatch", self.packet(book), clock=lambda: NOW + timedelta(seconds=1))
        book.fill("target-one", "synthetic-fill", 200, "5.01")
        snap = book.snapshot()
        self.assertEqual(snap["positions"], {})
        self.assertEqual(Decimal(snap["cash"]), Decimal("10007"))
        self.assertTrue(snap["paused"])
        self.assertFalse(snap["executable"])

    def test_existing_policy_keeps_full_stop(self):
        book = self.book(reduce_only=False)
        self.drift(book)
        with self.assertRaisesRegex(ValueError, "session risk stop"):
            book.admit(intent(side="SELL", price="5.01"), self.packet(book), clock=lambda: NOW + timedelta(seconds=1))

    def test_new_policy_is_explicit_and_changes_fingerprint_without_rewriting_old_defaults(self):
        cfg = {**policy(), "schema_version": 2, "max_drawdown": ".08"}
        old = normalize_policy(cfg)
        self.assertNotIn("exposure_stop_action", old)
        opt_in = normalize_policy({**cfg, "exposure_stop_action": "reduce_only"})
        self.assertNotEqual(fingerprint(old), fingerprint(opt_in))
        self.assertEqual(normalize_policy({**cfg, "exposure_stop_action": "halt_all"})["exposure_stop_action"], "halt_all")
        for bad in (None, True, [], "allow_all", "REDUCE_ONLY"):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                normalize_policy({**cfg, "exposure_stop_action": bad})
        with self.assertRaises(ValueError):
            normalize_policy({**policy(), "exposure_stop_action": "reduce_only"})

    def test_new_buys_and_oversells_remain_rejected(self):
        book = self.book()
        self.drift(book)
        for request in (intent("buy", code=OTHER), intent("oversell", side="SELL", quantity=300, price="5.01")):
            with self.subTest(side=request["side"]), self.assertRaises(ValueError):
                book.admit(request, self.packet(book), clock=lambda: NOW + timedelta(seconds=1))
        self.assertEqual(book.snapshot()["orders"], {})

    def test_pending_buys_must_be_resolved_and_pending_sells_do_not_release_exposure(self):
        book = self.book()
        book.admit(intent("buy", code=OTHER), self.packet(book, "4.95", NOW), clock=lambda: NOW)
        self.drift(book)
        with self.assertRaisesRegex(ValueError, "pending buys"):
            book.admit(intent("sell-denied", side="SELL", price="5.01"), self.packet(book), clock=lambda: NOW + timedelta(seconds=1))
        book.report_status("buy", "cancel", "CANCELLED", 0)
        book.admit(intent("sell", side="SELL", price="5.01"), self.packet(book), clock=lambda: NOW + timedelta(seconds=1))
        risk = book.snapshot()["orders"]["sell"]["admission"]["risk"]
        self.assertEqual(Decimal(risk["gross_committed_exposure"]), 1002)
        self.assertEqual(book.snapshot()["available_positions"][SYMBOL], 100)
        with self.assertRaisesRegex(ValueError, "sellable"):
            book.admit(intent("second", side="SELL", quantity=200, price="5.01"), self.packet(book), clock=lambda: NOW + timedelta(seconds=1))

    def test_t1_sellable_lock_is_still_enforced(self):
        book = self.book(sellable=0)
        self.drift(book)
        with self.assertRaisesRegex(ValueError, "sellable"):
            book.admit_target(target(book, target_notional_cny="0", limit_price="5.01"), self.packet(book), clock=lambda: NOW + timedelta(seconds=1))
        self.assertEqual(book.snapshot()["orders"], {})

    def test_prior_daily_loss_is_not_erased_by_later_price_recovery(self):
        book = self.book()
        book.record_valuation(self.packet(book, "4.60", NOW), clock=lambda: NOW)
        self.drift(book)
        self.assertEqual(book.snapshot()["risk_session"]["risk_stop_causes"], ["daily_loss", "single_position"])
        with self.assertRaisesRegex(ValueError, "session risk stop"):
            book.admit_target(target(book, target_notional_cny="0", limit_price="5.01"), self.packet(book), clock=lambda: NOW + timedelta(seconds=1))

    def test_reduction_fee_can_trigger_daily_limit_and_the_denial_cause_is_durable(self):
        book = self.book()
        self.drift(book)
        with self.assertRaisesRegex(ValueError, "daily loss"):
            book.admit(intent(side="SELL", price="4.675"), self.packet(book, "4.675"), clock=lambda: NOW + timedelta(seconds=1))
        self.drift(book)
        before = book.snapshot()["risk_session"]["risk_stop_causes"]
        self.assertEqual(before, ["daily_loss", "single_position"])
        path = Path(self.temp.name) / f"exposure-{self.index}.sqlite"
        book.close()
        with OfflineOrderJournal(path) as reopened:
            self.assertEqual(reopened.snapshot()["risk_session"]["risk_stop_causes"], before)
            with self.assertRaisesRegex(ValueError, "session risk stop"):
                reopened.admit(intent("again", side="SELL", price="5.01"), self.packet(reopened), clock=lambda: NOW + timedelta(seconds=1))

    def test_dispatch_rechecks_new_losses_after_reduction_admission(self):
        book = self.book()
        self.drift(book)
        book.admit(intent(side="SELL", price="5.01"), self.packet(book), clock=lambda: NOW + timedelta(seconds=1))
        with self.assertRaisesRegex(ValueError, "daily loss"):
            book.prepare_dispatch("one", "changed-loss", self.packet(book, "4.675"), clock=lambda: NOW + timedelta(seconds=1))
        snap = book.snapshot()
        self.assertNotIn("dispatch", snap["orders"]["one"])
        self.assertIn("daily_loss", snap["risk_session"]["risk_stop_causes"])
        self.assertEqual(snap["reserved_positions"][SYMBOL], 100)

    def test_prior_drawdown_persists_across_recovery_and_session_roll(self):
        book = self.book()
        book.record_valuation(self.packet(book, ".50", NOW), clock=lambda: NOW)
        self.drift(book)
        self.assertIn("cumulative_drawdown", book.snapshot()["risk_session"]["risk_stop_causes"])
        tomorrow = NOW + timedelta(days=1)
        packet = self.packet(book, "5.01", tomorrow)
        packet.update(instruments={code: instrument(code) for code in (SYMBOL, OTHER)}, sellable_positions={SYMBOL: 200})
        book.begin_session(packet, clock=lambda: tomorrow)
        self.assertEqual(book.snapshot()["risk_session"]["risk_stop_causes"], ["cumulative_drawdown"])
        with self.assertRaisesRegex(ValueError, "session risk stop"):
            book.admit(intent(side="SELL", price="5.01", now=tomorrow), self.packet(book, now=tomorrow), clock=lambda: tomorrow)

    def test_legacy_unclassified_stop_cannot_be_reclassified_by_new_valuation(self):
        book = self.book()
        book._run(lambda state: {"kind": "ADMISSION_DENIED", "data": {
            "reason": "legacy synthetic stop without typed cause", "risk_stop": True, "rejected_request": {}}})
        self.drift(book)
        self.assertEqual(book.snapshot()["risk_session"]["risk_stop_causes"], ["single_position", "unclassified"])
        with self.assertRaisesRegex(ValueError, "session risk stop"):
            book.admit(intent(side="SELL", price="5.01"), self.packet(book), clock=lambda: NOW + timedelta(seconds=1))

    def test_operator_and_quote_guards_still_block_reductions(self):
        book = self.book()
        self.drift(book)
        book.set_kill_switch(True, reason="synthetic operator review")
        with self.assertRaisesRegex(ValueError, "paused"):
            book.admit(intent("operator", side="SELL", price="5.01"), self.packet(book), clock=lambda: NOW + timedelta(seconds=1))
        book.set_kill_switch(False, reason="synthetic review complete")
        stale = self.packet(book, now=NOW + timedelta(seconds=33))
        stale["quotes"][SYMBOL]["timestamp"] = (NOW + timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(ValueError, "stale"):
            book.admit(intent("stale", side="SELL", price="5.01"), stale, clock=lambda: NOW + timedelta(seconds=33))
        halted = self.packet(book)
        halted["quotes"][SYMBOL]["trade_status"] = "HALTED"
        with self.assertRaisesRegex(ValueError, "not trading"):
            book.admit(intent("halt", side="SELL", price="5.01"), halted, clock=lambda: NOW + timedelta(seconds=1))
        self.assertTrue(book.snapshot()["risk_session"]["risk_stop"])

    def test_unknown_order_and_account_fault_still_require_reconciliation(self):
        book = self.book()
        self.drift(book)
        book.admit(intent(side="SELL", price="5.01"), self.packet(book), clock=lambda: NOW + timedelta(seconds=1))
        book.report_status("one", "unknown", "UNKNOWN", 0)
        with self.assertRaisesRegex(ValueError, "paused"):
            book.admit(intent("two", side="SELL", price="5.01"), self.packet(book), clock=lambda: NOW + timedelta(seconds=1))
        self.assertEqual(len(book.snapshot()["orders"]), 1)

    def test_total_exposure_stop_can_only_reduce_a_preexisting_oversized_book(self):
        book = self.book(cash="100", shares=2000, sellable=2000)
        self.drift(book)
        self.assertEqual(book.snapshot()["risk_session"]["risk_stop_causes"], ["capital_exposure", "single_position"])
        with self.assertRaisesRegex(ValueError, "ADV participation"):
            book.admit_target(target(book, target_notional_cny="0", limit_price="5.01"), self.packet(book), clock=lambda: NOW + timedelta(seconds=1))
        book.admit(intent("partial", side="SELL", quantity=1000, price="5.01"), self.packet(book), clock=lambda: NOW + timedelta(seconds=1))
        self.assertEqual(book.snapshot()["orders"]["partial"]["quantity"], 1000)
        self.assertEqual(Decimal(book.snapshot()["orders"]["partial"]["admission"]["risk"]["gross_committed_exposure"]), 10020)

    def test_unrecognized_stop_causes_fail_closed(self):
        for cause in ([], None, ["unknown_risk"], ["single_position", 1]):
            with self.subTest(cause=cause):
                book = self.book()
                book._run(lambda state: {"kind": "ADMISSION_DENIED", "data": {
                    "reason": "synthetic compatibility record", "risk_stop": True,
                    "risk_stop_causes": cause, "rejected_request": {}}})
                self.drift(book)
                with self.assertRaisesRegex(ValueError, "session risk stop"):
                    book.admit(intent(side="SELL", price="5.01"), self.packet(book), clock=lambda: NOW + timedelta(seconds=1))


if __name__ == "__main__":
    unittest.main()
