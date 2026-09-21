import sqlite3
from contextlib import closing
import tempfile
import unittest
from decimal import Decimal, localcontext
from pathlib import Path

from quant_robot.execution.offline_journal import OfflineOrderJournal


class OfflineOrderJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "orders.sqlite"
        self.book = OfflineOrderJournal.create(self.path, initial_cash="10000",
            initial_positions={"510300.SH": 1000}, commission_bps="5", minimum_commission="5")
        self.addCleanup(lambda: self.book.close())

    def order(self, order_id="o1", key="k1", side="BUY", quantity=200, price="10"):
        return self.book.register(order_id=order_id, idempotency_key=key, symbol="510300.SH",
            side=side, quantity=quantity, limit_price=price)

    def reconcile(self, snapshot_id="s1", overrides=None):
        state = self.book.snapshot()
        evidence = {"cash": state["cash"], "positions": state["positions"],
            "orders": {key: {field: row[field] for field in
                ("status", "filled_quantity", "filled_notional", "commission")} for key, row in state["orders"].items()}}
        if overrides:
            overrides(evidence)
        return self.book.reconcile(snapshot_id=snapshot_id, expected_sequence=state["sequence"], **evidence)

    def test_partial_fills_charge_one_cumulative_minimum_and_dedupe(self):
        self.order()
        self.assertTrue(self.book.fill("o1", "f2", 100, "9.9"))
        self.assertTrue(self.book.fill("o1", "f1", 100, "10"))
        self.assertFalse(self.book.fill("o1", "f2", 100, "9.9"))
        state = self.book.snapshot()
        self.assertEqual(Decimal(state["cash"]), Decimal("8005"))
        self.assertEqual(state["positions"]["510300.SH"], 1200)
        self.assertEqual(Decimal(state["orders"]["o1"]["commission"]), Decimal("5"))
        self.assertEqual(state["orders"]["o1"]["status"], "FILLED")

    def test_cumulative_fee_can_cross_minimum_without_charging_it_again(self):
        self.order(quantity=2000, price="4")
        self.book.fill("o1", "f1", 1000, "4")
        self.book.fill("o1", "f2", 1000, "4")
        self.assertEqual(Decimal(self.book.snapshot()["orders"]["o1"]["commission"]), Decimal("5"))
        self.order("sell", "ks", "SELL", 3000, "4")
        self.book.fill("sell", "f3", 2000, "4")
        self.book.fill("sell", "f4", 1000, "4")
        self.assertEqual(Decimal(self.book.snapshot()["orders"]["sell"]["commission"]), Decimal("6"))

    def test_zero_fill_cancel_charges_nothing_and_releases_reservation(self):
        self.order()
        self.book.request_cancel("o1")
        self.assertEqual(Decimal(self.book.snapshot()["reserved_cash"]), Decimal("2005"))
        self.book.report_status("o1", "c1", "CANCELLED", 0)
        self.assertEqual(Decimal(self.book.snapshot()["cash"]), Decimal("10000"))
        self.assertEqual(Decimal(self.book.snapshot()["reserved_cash"]), 0)

    def test_restart_blocks_resubmission_and_recovers_durable_fills(self):
        self.order()
        self.book.fill("o1", "f1", 100, "10")
        self.book.close()
        self.book = OfflineOrderJournal(self.path)
        state = self.book.snapshot()
        self.assertTrue(state["paused"])
        self.assertEqual(state["orders"]["o1"]["status"], "UNKNOWN")
        with self.assertRaisesRegex(ValueError, "idempotency"):
            self.order()
        with self.assertRaisesRegex(ValueError, "paused"):
            self.order("o2", "k2")
        self.assertFalse(self.book.fill("o1", "f1", 100, "10"))
        self.reconcile(overrides=lambda e: e["orders"]["o1"].update(status="PARTIAL"))
        self.assertFalse(self.book.snapshot()["paused"])
        self.assertEqual(Decimal(self.book.snapshot()["cash"]), Decimal("8995"))

    def test_pending_intent_on_restart_is_unknown_never_automatically_resent(self):
        self.order()
        self.book.close()
        self.book = OfflineOrderJournal(self.path)
        self.assertEqual(self.book.snapshot()["orders"]["o1"]["status"], "UNKNOWN")
        self.reconcile(overrides=lambda e: e["orders"]["o1"].update(status="REJECTED"))
        self.assertEqual(Decimal(self.book.snapshot()["reserved_cash"]), 0)

    def test_duplicate_identity_with_changed_payload_quarantines_persistently(self):
        self.order()
        self.book.fill("o1", "f1", 100, "10")
        with self.assertRaisesRegex(ValueError, "conflicting"):
            self.book.fill("o1", "f1", 100, "9")
        self.assertTrue(self.book.snapshot()["paused"])
        self.book.close()
        self.book = OfflineOrderJournal(self.path)
        self.assertTrue(self.book.snapshot()["paused"])
        self.assertEqual(Decimal(self.book.snapshot()["cash"]), Decimal("8995"))

    def test_cash_and_positions_are_reserved_across_pending_orders(self):
        self.order(quantity=900)
        with self.assertRaisesRegex(ValueError, "cash"):
            self.order("o2", "k2")
        self.order("s1", "ks1", "SELL", 700)
        with self.assertRaisesRegex(ValueError, "position"):
            self.order("s2", "ks2", "SELL", 400)

    def test_sell_commission_shortfall_is_reserved(self):
        other = Path(self.tmp.name) / "small.sqlite"
        with OfflineOrderJournal.create(other, initial_cash="5", initial_positions={"510300.SH": 2},
                commission_bps="0", minimum_commission="5") as book:
            book.register(order_id="s1", idempotency_key="k1", symbol="510300.SH", side="SELL", quantity=1, limit_price="1")
            self.assertEqual(Decimal(book.snapshot()["reserved_cash"]), Decimal("4"))
            with self.assertRaisesRegex(ValueError, "cash"):
                book.register(order_id="s2", idempotency_key="k2", symbol="510300.SH", side="SELL", quantity=1, limit_price="1")

    def test_cancel_fill_race_keeps_fill_and_cumulative_fee(self):
        self.order()
        self.book.request_cancel("o1")
        self.book.fill("o1", "f1", 100, "10")
        self.assertEqual(self.book.snapshot()["orders"]["o1"]["status"], "CANCEL_PENDING")
        self.book.report_status("o1", "c1", "CANCELLED", 100)
        self.assertEqual(Decimal(self.book.snapshot()["orders"]["o1"]["commission"]), 5)
        self.assertEqual(Decimal(self.book.snapshot()["reserved_cash"]), 0)

    def test_late_fill_after_cancel_is_accounted_and_pauses_for_reconciliation(self):
        self.order()
        self.book.report_status("o1", "c1", "CANCELLED", 0)
        self.book.fill("o1", "late", 100, "10")
        state = self.book.snapshot()
        self.assertEqual(Decimal(state["cash"]), Decimal("8995"))
        self.assertTrue(state["paused"])
        self.assertEqual(state["orders"]["o1"]["status"], "CANCELLED")

    def test_stale_ack_does_not_regress_terminal_order(self):
        self.order()
        self.book.fill("o1", "f1", 200, "10")
        self.book.report_status("o1", "a1", "ACCEPTED", 0)
        self.assertEqual(self.book.snapshot()["orders"]["o1"]["status"], "FILLED")

    def test_report_with_missing_fills_pauses_without_fabricating_cash(self):
        self.order()
        with self.assertRaisesRegex(ValueError, "missing fill"):
            self.book.report_status("o1", "c1", "CANCELLED", 100)
        self.assertTrue(self.book.snapshot()["paused"])
        self.assertEqual(Decimal(self.book.snapshot()["cash"]), Decimal("10000"))

    def test_limit_violation_is_recorded_as_fact_and_pauses(self):
        self.order()
        self.book.fill("o1", "bad_price", 100, "11")
        self.assertTrue(self.book.snapshot()["paused"])
        self.assertEqual(Decimal(self.book.snapshot()["cash"]), Decimal("8895"))

    def test_reconciliation_requires_complete_orders_and_exact_balances(self):
        self.order()
        self.book.report_status("o1", "a1", "ACCEPTED", 0)
        for change in (lambda e: e.update(cash="10001"), lambda e: e.update(positions={}),
                       lambda e: e.update(orders={}),
                       lambda e: e["orders"]["o1"].update(filled_quantity=1)):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "reconciliation"):
                self.reconcile(overrides=change)
            self.assertTrue(self.book.snapshot()["paused"])
        self.reconcile()
        self.assertFalse(self.book.snapshot()["paused"])

    def test_stale_reconciliation_cannot_clear_new_fault(self):
        state = self.book.snapshot()
        self.book.set_kill_switch(True, reason="operator pause")
        with self.assertRaisesRegex(ValueError, "stale"):
            self.book.reconcile(snapshot_id="old", expected_sequence=state["sequence"],
                cash=state["cash"], positions=state["positions"], orders={})
        self.assertTrue(self.book.snapshot()["paused"])

    def test_reconciliation_does_not_clear_operator_kill_switch(self):
        self.book.set_kill_switch(True, reason="operator pause")
        self.reconcile()
        self.assertTrue(self.book.snapshot()["paused"])
        self.book.set_kill_switch(False, reason="operator release")
        self.assertFalse(self.book.snapshot()["paused"])

    def test_invalid_intents_are_atomic_and_cannot_overwrite_journal(self):
        sequence = self.book.snapshot()["sequence"]
        for quantity, price in ((True, "10"), (0, "10"), (100, "NaN"), (100, "0")):
            with self.subTest(quantity=quantity, price=price), self.assertRaises(ValueError):
                self.order(quantity=quantity, price=price)
        self.assertEqual(self.book.snapshot()["sequence"], sequence)
        with self.assertRaises(FileExistsError):
            OfflineOrderJournal.create(self.path, initial_cash="0", initial_positions={}, commission_bps="0", minimum_commission="0")

    def test_events_are_append_only_and_never_enable_execution(self):
        self.order()
        state = self.book.snapshot()
        self.assertEqual(state["mode"], "offline_fixture_only")
        self.assertFalse(state["executable"])
        with closing(sqlite3.connect(self.path)) as conn:
            for sql in ("DELETE FROM events", "UPDATE events SET payload = '{}' WHERE sequence = 1"):
                with self.assertRaises(sqlite3.IntegrityError):
                    conn.execute(sql)

    def test_equivalent_numeric_receipt_is_a_duplicate(self):
        self.order()
        self.book.fill("o1", "f1", 100, "10")
        self.assertFalse(self.book.fill("o1", "f1", 100, "10.0000"))

    def test_late_fill_after_rejection_can_be_reconciled(self):
        self.order()
        self.book.report_status("o1", "r1", "REJECTED", 0)
        self.book.fill("o1", "f1", 100, "10")
        self.assertTrue(self.book.snapshot()["paused"])
        self.reconcile(overrides=lambda e: e["orders"]["o1"].update(status="PARTIAL"))
        self.assertFalse(self.book.snapshot()["paused"])

    def test_terminal_status_conflict_does_not_rewrite_history(self):
        self.order()
        self.book.report_status("o1", "r1", "REJECTED", 0)
        with self.assertRaisesRegex(ValueError, "terminal"):
            self.book.report_status("o1", "c1", "CANCELLED", 0)
        self.assertEqual(self.book.snapshot()["orders"]["o1"]["status"], "REJECTED")

    def test_sell_reserves_fee_shortfall_of_smallest_partial_fill(self):
        other = Path(self.tmp.name) / "partial_fee.sqlite"
        with OfflineOrderJournal.create(other, initial_cash="0", initial_positions={"510300.SH": 1000},
                commission_bps="0", minimum_commission="5") as book:
            with self.assertRaisesRegex(ValueError, "cash"):
                book.register(order_id="s1", idempotency_key="k1", symbol="510300.SH", side="SELL", quantity=1000, limit_price="0.01")

    def test_cumulative_cash_can_exceed_initial_input_cap_and_reconcile(self):
        other = Path(self.tmp.name) / "large_balance.sqlite"
        with OfflineOrderJournal.create(other, initial_cash="1000000000000", initial_positions={"510300.SH": 1},
                commission_bps="0", minimum_commission="0") as book:
            book.register(order_id="sell", idempotency_key="key", symbol="510300.SH", side="SELL", quantity=1, limit_price="1")
            book.fill("sell", "fill", 1, "1")
            book.report_status("sell", "unknown", "UNKNOWN", 1)
            state = book.snapshot()
            self.assertEqual(Decimal(state["cash"]), Decimal("1000000000001"))
            book.reconcile(snapshot_id="s1", expected_sequence=state["sequence"], cash=state["cash"], positions={},
                orders={"sell": {"status": "FILLED", "filled_quantity": 1, "filled_notional": "1", "commission": "0"}})
            self.assertFalse(book.snapshot()["paused"])

    def test_rejected_receipt_is_retained_with_fault_for_diagnosis(self):
        self.order()
        self.book.fill("o1", "f1", 100, "10")
        with self.assertRaises(ValueError):
            self.book.fill("o1", "f1", 100, "9")
        import json
        with closing(sqlite3.connect(self.path)) as conn:
            fault = json.loads(conn.execute("SELECT payload FROM events ORDER BY sequence DESC LIMIT 1").fetchone()[0])
        self.assertEqual(fault["kind"], "FAULT")
        self.assertEqual(fault["data"]["rejected_request"]["fill_id"], "f1")
        self.assertEqual(Decimal(fault["data"]["rejected_request"]["price"]), 9)

    def test_sell_reservation_covers_cumulative_fee_rounding_jump(self):
        other = Path(self.tmp.name) / "rounding.sqlite"
        with OfflineOrderJournal.create(other, initial_cash="0", initial_positions={"510300.SH": 100000},
                commission_bps="9999", minimum_commission="0") as book:
            with self.assertRaisesRegex(ValueError, "cash"):
                book.register(order_id="s1", idempotency_key="k1", symbol="510300.SH", side="SELL", quantity=100000, limit_price="0.000001")

    def test_accounting_is_independent_of_callers_decimal_precision(self):
        self.order()
        with localcontext() as context:
            context.prec = 6
            self.book.fill("o1", "f1", 200, "9.876543")
            state = self.book.snapshot()
        self.assertEqual(Decimal(state["cash"]), Decimal("8019.6914"))
        self.assertEqual(Decimal(state["orders"]["o1"]["filled_notional"]), Decimal("1975.3086"))

    def test_cumulative_notional_and_positions_do_not_use_single_order_caps(self):
        cases = [("large_notional", "0", 2, "SELL", 2, "1000000000000"),
                 ("large_position", "10", 1000000000, "BUY", 1, "1")]
        for name, cash, holding, side, quantity, price in cases:
            with self.subTest(name=name), OfflineOrderJournal.create(Path(self.tmp.name) / (name + ".sqlite"),
                    initial_cash=cash, initial_positions={"510300.SH": holding},
                    commission_bps="0", minimum_commission="0") as book:
                book.register(order_id="o1", idempotency_key="k1", symbol="510300.SH", side=side, quantity=quantity, limit_price=price)
                book.fill("o1", "f1", quantity, price)
                state = book.snapshot()
                book.reconcile(snapshot_id="s1", expected_sequence=state["sequence"], cash=state["cash"], positions=state["positions"],
                    orders={"o1": {field: state["orders"]["o1"][field] for field in
                        ("status", "filled_quantity", "filled_notional", "commission")}})
                self.assertFalse(book.snapshot()["paused"])

    def test_partial_fee_rounding_buffer_deducts_rounding_already_paid(self):
        other = Path(self.tmp.name) / "paid_rounding.sqlite"
        with OfflineOrderJournal.create(other, initial_cash="0.01", initial_positions={"510300.SH": 100000},
                commission_bps="9999", minimum_commission="0") as book:
            book.register(order_id="sell", idempotency_key="key", symbol="510300.SH", side="SELL", quantity=100000, limit_price="0.000001")
            for index, quantity in enumerate((5001, 1, 10000, 84998)):
                book.fill("sell", "f" + str(index), quantity, "0.000001")
                state = book.snapshot()
                self.assertFalse(state["paused"], state["faults"])
                self.assertGreaterEqual(Decimal(state["cash"]), Decimal(state["reserved_cash"]))
                book.reconcile(snapshot_id="s" + str(index), expected_sequence=state["sequence"],
                    cash=state["cash"], positions=state["positions"], orders={"sell": {
                        field: state["orders"]["sell"][field] for field in
                        ("status", "filled_quantity", "filled_notional", "commission")}})


if __name__ == "__main__":
    unittest.main()
