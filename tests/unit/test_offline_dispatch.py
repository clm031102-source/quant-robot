from datetime import timedelta
from contextlib import closing
from decimal import Decimal
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, intent, policy


class OfflineDispatchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "dispatch.sqlite"
        self.book = OfflineOrderJournal.create(self.path, initial_cash="3000", initial_positions={},
            commission_bps="0.5", minimum_commission="5", admission_policy=policy())
        self.addCleanup(lambda: self.book.close())
        packet = context(self.book)
        packet.update(instruments={s: instrument(s) for s in (SYMBOL, OTHER)}, sellable_positions={})
        self.book.begin_session(packet, clock=lambda: NOW)

    def admit(self, order=None):
        return self.book.admit(order or intent(), context(self.book), clock=lambda: NOW)

    def prepare(self, order_id="one", attempt_id="dispatch-one", packet=None, now=NOW):
        return self.book.prepare_dispatch(order_id, attempt_id, packet or context(self.book, now), clock=lambda: now)

    def test_fresh_preparation_keeps_reservation_and_records_offline_evidence(self):
        self.admit(intent(quantity=200))
        before = self.book.snapshot()
        self.assertTrue(self.prepare())
        after = self.book.snapshot()
        self.assertEqual(Decimal(after["reserved_cash"]), Decimal(before["reserved_cash"]))
        self.assertEqual(after["orders"]["one"]["dispatch"]["risk"]["one_way_committed_shares"], 200)
        self.assertEqual(Decimal(after["orders"]["one"]["dispatch"]["risk"]["gross_committed_exposure"]), 800)
        self.assertFalse(after["executable"])
        self.assertEqual(after["orders"]["one"]["filled_quantity"], 0)

    def test_quote_that_expired_after_admission_blocks_preparation(self):
        self.admit()
        before = self.book.snapshot()
        packet = context(self.book)
        packet["as_of"] = (NOW + timedelta(seconds=31)).isoformat()
        with self.assertRaisesRegex(ValueError, "stale"):
            self.prepare(packet=packet, now=NOW + timedelta(seconds=31))
        after = self.book.snapshot()
        self.assertNotIn("dispatch", after["orders"]["one"])
        self.assertEqual(after["reserved_cash"], before["reserved_cash"])

    def test_new_daily_loss_stops_dispatch_and_survives_recovery(self):
        self.admit(intent("holding", quantity=200))
        self.book.fill("holding", "holding-fill", 200, "4")
        self.admit(intent(code=OTHER))
        packet = context(self.book)
        packet["quotes"][SYMBOL].update(bid="3.7", ask="3.7")
        with self.assertRaisesRegex(ValueError, "daily loss"):
            self.prepare(packet=packet)
        self.assertTrue(self.book.snapshot()["risk_session"]["risk_stop"])
        self.book.close()
        self.book = OfflineOrderJournal(self.path)
        self.assertTrue(self.book.snapshot()["risk_session"]["risk_stop"])

    def test_fresh_journal_anchor_is_required_after_another_order_changes_state(self):
        self.admit()
        stale = context(self.book)
        self.admit(intent("two", code=OTHER))
        with self.assertRaisesRegex(ValueError, "stale journal anchor"):
            self.prepare(packet=stale)
        self.assertTrue(self.prepare(attempt_id="fresh"))

    def test_updated_halt_spread_or_slippage_blocks_reserved_order(self):
        self.admit()
        for index, changes in enumerate(({"trade_status": "HALTED"}, {"ask": "4.1"}, {"bid": "3.9", "ask": "3.9"})):
            packet = context(self.book)
            packet["quotes"][SYMBOL].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.prepare(attempt_id=str(index), packet=packet)
        self.assertNotIn("dispatch", self.book.snapshot()["orders"]["one"])

    def test_expired_original_signal_cannot_be_refreshed_by_a_new_quote(self):
        self.admit()
        with self.assertRaisesRegex(ValueError, "expired"):
            self.prepare(now=NOW + timedelta(minutes=2))

    def test_preparation_cannot_roll_clock_back_before_admission(self):
        later = NOW + timedelta(seconds=10)
        self.book.admit(intent(), context(self.book, later), clock=lambda: later)
        with self.assertRaisesRegex(ValueError, "clock precedes"):
            self.prepare()

    def test_operator_stop_after_admission_blocks_preparation(self):
        self.admit()
        self.book.set_kill_switch(True, reason="fixture operator stop")
        with self.assertRaisesRegex(ValueError, "paused"):
            self.prepare()

    def test_prepared_order_cannot_be_prepared_twice_even_after_reconciliation(self):
        self.admit()
        self.prepare()
        self.book.close()
        self.book = OfflineOrderJournal(self.path)
        snap = self.book.snapshot()
        self.book.reconcile(snapshot_id="complete", expected_sequence=snap["sequence"], cash=snap["cash"],
            positions=snap["positions"], orders={"one": {"status": "ACCEPTED", "filled_quantity": 0,
                "filled_notional": "0", "commission": "0"}})
        with self.assertRaisesRegex(ValueError, "never-prepared"):
            self.prepare(attempt_id="second")
        self.assertFalse(self.book.snapshot()["executable"])
        self.assertEqual(self.book.snapshot()["orders"]["one"]["dispatch"]["attempt_id"], "dispatch-one")

    def test_failed_attempt_identity_is_consumed_but_new_attempt_can_recheck(self):
        self.admit()
        bad = context(self.book)
        bad["quotes"][SYMBOL]["trade_status"] = "HALTED"
        with self.assertRaises(ValueError):
            self.prepare(packet=bad)
        with self.assertRaisesRegex(ValueError, "consumed"):
            self.prepare()
        self.assertTrue(self.prepare(attempt_id="retry-with-new-evidence"))

    def test_attempt_identity_cannot_be_reused_for_another_order(self):
        self.admit()
        self.admit(intent("two", code=OTHER))
        self.prepare()
        with self.assertRaisesRegex(ValueError, "consumed"):
            self.prepare(order_id="two")

    def test_malformed_context_is_durably_denied_without_releasing_cash(self):
        self.admit()
        packet = context(self.book)
        packet.pop("as_of")
        with self.assertRaises(ValueError):
            self.prepare(packet=packet)
        with closing(sqlite3.connect(self.path)) as connection:
            event = json.loads(connection.execute("SELECT payload FROM events ORDER BY sequence DESC LIMIT 1").fetchone()[0])
        self.assertEqual(event["kind"], "DISPATCH_DENIED")
        self.assertEqual(event["data"]["rejected_request"]["attempt_id"], "dispatch-one")
        self.assertEqual(Decimal(self.book.snapshot()["reserved_cash"]), 405)
        with self.assertRaisesRegex(ValueError, "consumed"):
            self.prepare()

    def test_cancel_pending_accepted_partial_and_unknown_orders_cannot_be_prepared(self):
        for index in range(4):
            self.admit(intent(str(index), code=OTHER if index % 2 else SYMBOL))
        self.book.request_cancel("0")
        self.book.report_status("1", "ack", "ACCEPTED", 0)
        self.book.fill("2", "fill", 1, "4")
        self.book.report_status("3", "unknown", "UNKNOWN", 0)
        for index in range(4):
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "never-prepared"):
                self.prepare(order_id=str(index), attempt_id=str(index))

    def test_sell_revalidation_does_not_subtract_its_own_reserved_shares_twice(self):
        self.admit(intent("buy"))
        self.book.fill("buy", "buy-fill", 100, "4")
        tomorrow = NOW + timedelta(days=1)
        packet = context(self.book, tomorrow)
        packet.update(instruments={s: instrument(s) for s in (SYMBOL, OTHER)}, sellable_positions={SYMBOL: 100})
        self.book.begin_session(packet, clock=lambda: tomorrow)
        self.book.admit(intent(side="SELL", now=tomorrow), context(self.book, tomorrow), clock=lambda: tomorrow)
        self.assertTrue(self.prepare(now=tomorrow))
        self.assertEqual(self.book.snapshot()["reserved_positions"], {SYMBOL: 100})

    def test_new_portfolio_exposure_blocks_otherwise_fresh_buy(self):
        self.admit(intent("holding", quantity=200))
        self.book.fill("holding", "holding-fill", 200, "4")
        self.admit(intent(code=OTHER))
        packet = context(self.book)
        packet["quotes"][SYMBOL].update(bid="5.1", ask="5.1")
        with self.assertRaisesRegex(ValueError, "single position"):
            self.prepare(packet=packet)

    def test_missing_portfolio_quote_blocks_dispatch(self):
        self.admit(intent("holding", code=OTHER))
        self.book.fill("holding", "holding-fill", 100, "4")
        self.admit()
        packet = context(self.book)
        del packet["quotes"][OTHER]
        with self.assertRaisesRegex(ValueError, "missing quote"):
            self.prepare(packet=packet)

    def test_a_new_attempt_cannot_prepare_a_still_pending_order_twice(self):
        self.admit()
        self.prepare()
        with self.assertRaisesRegex(ValueError, "never-prepared"):
            self.prepare(attempt_id="second")
        self.assertEqual(self.book.snapshot()["orders"]["one"]["dispatch"]["attempt_id"], "dispatch-one")

    def test_old_unguarded_journal_cannot_create_dispatch_evidence(self):
        with OfflineOrderJournal.create(self.path.parent / "legacy.sqlite", initial_cash="3000", initial_positions={},
                commission_bps="0.5", minimum_commission="5") as legacy:
            legacy.register(order_id="raw", idempotency_key="raw", symbol=SYMBOL, side="BUY", quantity=100, limit_price="4")
            with self.assertRaisesRegex(ValueError, "guarded admission"):
                legacy.prepare_dispatch("raw", "raw-attempt", context(legacy), clock=lambda: NOW)

    def test_terminal_order_cannot_be_prepared(self):
        for index, status in enumerate(["CANCELLED", "REJECTED"]):
            key = str(index)
            self.admit(intent(key))
            self.book.report_status(key, "report-" + key, status, 0)
            with self.subTest(status=status), self.assertRaisesRegex(ValueError, "never-prepared"):
                self.prepare(order_id=key, attempt_id=key)

    def test_cancel_and_fill_facts_remain_recordable_after_preparation(self):
        self.admit()
        self.prepare()
        self.book.request_cancel("one")
        self.book.fill("one", "late-fill", 100, "4")
        snap = self.book.snapshot()
        self.assertEqual(snap["orders"]["one"]["status"], "FILLED")
        self.assertEqual(snap["positions"], {SYMBOL: 100})
        self.assertEqual(Decimal(snap["reserved_cash"]), 0)

    def test_unknown_order_denial_consumes_attempt_identity(self):
        with self.assertRaisesRegex(ValueError, "unknown dispatch"):
            self.prepare()
        self.admit()
        with self.assertRaisesRegex(ValueError, "consumed"):
            self.prepare()


if __name__ == "__main__":
    unittest.main()
