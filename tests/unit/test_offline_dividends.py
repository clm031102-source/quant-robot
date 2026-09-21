from datetime import timedelta
from decimal import Decimal, localcontext
from pathlib import Path
import tempfile
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, intent, policy


def dividend_policy():
    return {"schema_version": 1, "mode": "offline_fixture_only", "source_ref": "synthetic-dividend-schedule",
        "coverage_start": "2026-09-14", "coverage_end": "2026-09-16", "record_cutoff": "15:00",
        "events": [{"event_id": "div-one", "symbol": SYMBOL, "announced_at": "2026-09-11T12:00:00+08:00",
            "record_date": "2026-09-14", "ex_date": "2026-09-15", "pay_date": "2026-09-16",
            "net_cash_per_share": "0.6", "cash_rounding": "half_up_cent_per_holder"}]}


def extended_policy():
    value = policy()
    value["session_dates"].append("2026-09-16")
    return value


def start(book, now, price="4", basis=None):
    packet = context(book, now)
    packet["quotes"][SYMBOL].update(bid=price, ask=price)
    if basis:
        packet["quotes"][SYMBOL]["price_basis_id"] = basis
    metadata = {s: {**instrument(s), "valid_until": "2026-09-16"} for s in (SYMBOL, OTHER)}
    packet.update(instruments=metadata, sellable_positions=book.snapshot()["positions"])
    book.begin_session(packet, clock=lambda: now)


class OfflineDividendTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)/"dividends.sqlite"
        self.book = OfflineOrderJournal.create(self.path, initial_cash="2600", initial_positions={SYMBOL: 100},
            commission_bps="0.5", minimum_commission="5", admission_policy=extended_policy(),
            dividend_policy=dividend_policy())
        start(self.book, NOW)

    def tearDown(self):
        self.book.close()
        self.directory.cleanup()

    def capture(self):
        return self.book.record_dividend_entitlements(clock=lambda: NOW.replace(hour=15, minute=0))

    def accrue(self):
        return self.book.accrue_dividends(clock=lambda: (NOW + timedelta(days=1)).replace(hour=9, minute=0))

    def ex_packet(self, now=None, book=None):
        now, book = now or NOW + timedelta(days=1), book or self.book
        packet = context(book, now)
        packet["quotes"][SYMBOL].update(bid="3.4", ask="3.4", price_basis_id="cash_dividend:div-one")
        return packet

    def open_ex(self):
        self.capture()
        self.accrue()
        start(self.book, NOW + timedelta(days=1), "3.4", "cash_dividend:div-one")

    def test_entitlement_receivable_and_cash_are_distinct_and_total_value_is_preserved(self):
        self.capture()
        snap = self.book.snapshot()
        self.assertEqual(Decimal(snap["cash"]), 2600)
        self.assertEqual(Decimal(snap["dividends"]["receivable_total"]), 0)
        self.assertEqual(snap["dividends"]["entitlements"]["div-one"]["quantity"], 100)
        self.accrue()
        tomorrow = NOW + timedelta(days=1)
        start(self.book, tomorrow, "3.4", "cash_dividend:div-one")
        snap = self.book.snapshot()
        self.assertEqual(Decimal(snap["risk_session"]["opening_equity"]), 3000)
        self.assertEqual(Decimal(snap["dividends"]["receivable_total"]), 60)
        self.assertEqual(Decimal(snap["cash"]), 2600)
        pay = NOW + timedelta(days=2)
        self.book.record_dividend_cash_credit("div-one", "credit-one", "60", clock=lambda: pay)
        snap = self.book.snapshot()
        self.assertEqual(Decimal(snap["cash"]), 2660)
        self.assertEqual(Decimal(snap["dividends"]["receivable_total"]), 0)

    def test_ex_date_session_cannot_open_before_accrual_or_with_old_price_basis(self):
        self.capture()
        tomorrow = NOW + timedelta(days=1)
        with self.assertRaisesRegex(ValueError, "accrual"):
            start(self.book, tomorrow, "3.4")
        self.accrue()
        with self.assertRaisesRegex(ValueError, "price basis"):
            start(self.book, tomorrow, "3.4")
        start(self.book, tomorrow, "3.4", "cash_dividend:div-one")

    def test_missing_record_date_entitlement_cannot_be_inferred_from_ex_date_holdings(self):
        with self.assertRaisesRegex(ValueError, "entitlement"):
            self.accrue()
        self.assertEqual(Decimal(self.book.snapshot()["dividends"]["receivable_total"]), 0)

    def test_open_orders_block_record_date_entitlement(self):
        self.book.admit(intent(), context(self.book), clock=lambda: NOW)
        with self.assertRaisesRegex(ValueError, "unresolved"):
            self.capture()
        self.assertEqual(self.book.snapshot()["dividends"]["entitlements"], {})

    def test_cash_credit_is_never_inferred_from_pay_date_and_cannot_be_duplicated(self):
        self.capture()
        self.accrue()
        pay = NOW + timedelta(days=2)
        self.book.accrue_dividends(clock=lambda: pay)
        self.assertEqual(Decimal(self.book.snapshot()["cash"]), 2600)
        self.assertTrue(self.book.record_dividend_cash_credit("div-one", "one", "60", clock=lambda: pay))
        self.assertFalse(self.book.record_dividend_cash_credit("div-one", "one", "60", clock=lambda: pay + timedelta(seconds=1)))
        with self.assertRaises(ValueError):
            self.book.record_dividend_cash_credit("div-one", "two", "60", clock=lambda: pay)
        self.assertEqual(Decimal(self.book.snapshot()["cash"]), 2660)

    def test_record_capture_before_cutoff_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "cutoff"):
            self.book.record_dividend_entitlements(clock=lambda: NOW)
        self.assertEqual(self.book.snapshot()["dividends"]["entitlements"], {})

    def test_capture_and_accrual_replay_are_idempotent(self):
        self.assertTrue(self.capture())
        sequence = self.book.snapshot()["sequence"]
        self.assertFalse(self.capture())
        self.assertEqual(self.book.snapshot()["sequence"], sequence)
        self.assertTrue(self.accrue())
        sequence = self.book.snapshot()["sequence"]
        self.assertFalse(self.accrue())
        self.assertEqual(self.book.snapshot()["sequence"], sequence)

    def test_credit_before_pay_date_or_with_wrong_amount_preserves_receivable(self):
        self.open_ex()
        for date, amount in [(NOW + timedelta(days=1), "60"), (NOW + timedelta(days=2), "59.99")]:
            with self.assertRaises(ValueError):
                self.book.record_dividend_cash_credit("div-one", "bad", amount, clock=lambda: date)
        self.assertEqual(Decimal(self.book.snapshot()["cash"]), 2600)
        self.assertEqual(Decimal(self.book.snapshot()["dividends"]["receivable_total"]), 60)

    def test_valuation_includes_receivable_once_and_reports_it_separately(self):
        self.open_ex()
        self.book.record_valuation(self.ex_packet(), clock=lambda: NOW + timedelta(days=1))
        value = self.book.snapshot()["portfolio_valuation"]["last_valid"]
        self.assertEqual(Decimal(value["book_equity"]), 3000)
        self.assertEqual(Decimal(value["dividend_receivable"]), 60)
        self.assertEqual(value["breaches"], [])

    def test_receivable_is_not_spendable_cash(self):
        with OfflineOrderJournal.create(self.path.parent/"low-cash.sqlite", initial_cash="350", initial_positions={SYMBOL: 100},
                commission_bps="0.5", minimum_commission="5", admission_policy=extended_policy(), dividend_policy=dividend_policy()) as book:
            start(book, NOW)
            book.record_dividend_entitlements(clock=lambda: NOW.replace(hour=15))
            tomorrow = NOW + timedelta(days=1)
            book.accrue_dividends(clock=lambda: tomorrow.replace(hour=9))
            start(book, tomorrow, "3.4", "cash_dividend:div-one")
            with self.assertRaisesRegex(ValueError, "cash"):
                book.admit(intent(code=OTHER, now=tomorrow), self.ex_packet(book=book), clock=lambda: tomorrow)
            self.assertEqual(Decimal(book.snapshot()["cash"]), 350)
            self.assertEqual(Decimal(book.snapshot()["dividends"]["receivable_total"]), 60)

    def test_selling_after_record_date_does_not_remove_the_existing_entitlement(self):
        self.open_ex()
        tomorrow = NOW + timedelta(days=1)
        self.book.admit(intent(side="SELL", price="3.4", now=tomorrow), self.ex_packet(), clock=lambda: tomorrow)
        self.book.fill("one", "sell", 100, "3.4")
        self.book.record_valuation(self.ex_packet(), clock=lambda: tomorrow)
        snap = self.book.snapshot()
        self.assertEqual(Decimal(snap["portfolio_valuation"]["last_valid"]["book_equity"]), 2995)
        self.assertEqual(snap["dividends"]["entitlements"]["div-one"]["quantity"], 100)
        self.assertEqual(Decimal(snap["dividends"]["receivable_total"]), 60)
        self.assertNotIn("dividend_entitlement_requires_review", snap["faults"])

    def test_old_basis_blocks_new_order_and_dispatch_even_with_fresh_quote_time(self):
        self.open_ex()
        tomorrow = NOW + timedelta(days=1)
        old = self.ex_packet()
        old["quotes"][SYMBOL].pop("price_basis_id")
        with self.assertRaisesRegex(ValueError, "price basis"):
            self.book.admit(intent("old", code=OTHER, now=tomorrow), old, clock=lambda: tomorrow)
        self.book.admit(intent(code=OTHER, now=tomorrow), self.ex_packet(), clock=lambda: tomorrow)
        old = self.ex_packet()
        old["quotes"][SYMBOL].pop("price_basis_id")
        with self.assertRaisesRegex(ValueError, "price basis"):
            self.book.prepare_dispatch("one", "old-send", old, clock=lambda: tomorrow)
        self.assertEqual(Decimal(self.book.snapshot()["reserved_cash"]), 405)

    def test_late_fill_after_record_capture_invalidates_entitlement_without_rewriting_it(self):
        self.book.admit(intent(), context(self.book), clock=lambda: NOW)
        self.book.report_status("one", "cancel", "CANCELLED", 0)
        self.capture()
        self.book.fill("one", "late", 40, "4")
        snap = self.book.snapshot()
        self.assertIn("dividend_entitlement_requires_review", snap["faults"])
        self.assertEqual(snap["dividends"]["entitlements"]["div-one"]["quantity"], 100)
        with self.assertRaisesRegex(ValueError, "review"):
            self.accrue()
        order = snap["orders"]["one"]
        fields = ("status", "filled_quantity", "filled_notional", "commission")
        snap = self.book.snapshot()
        self.book.reconcile(snapshot_id="complete", expected_sequence=snap["sequence"], cash=snap["cash"], positions=snap["positions"],
            orders={"one": {key: order[key] for key in fields}})
        self.assertIn("dividend_entitlement_requires_review", self.book.snapshot()["faults"])

    def test_restart_preserves_receivable_policy_and_basis(self):
        self.open_ex()
        before = self.book.snapshot()
        self.book.close()
        self.book = OfflineOrderJournal(self.path)
        after = self.book.snapshot()
        self.assertEqual(before["dividends"], after["dividends"])
        self.assertEqual(before["dividend_policy_fingerprint"], after["dividend_policy_fingerprint"])

    def test_operator_stop_does_not_prevent_accounting_but_is_not_cleared(self):
        self.book.set_kill_switch(True, reason="operator")
        self.capture()
        self.accrue()
        pay = NOW + timedelta(days=2)
        self.book.record_dividend_cash_credit("div-one", "credit", "60", clock=lambda: pay)
        self.assertTrue(self.book.snapshot()["kill_switch"])
        self.assertEqual(Decimal(self.book.snapshot()["cash"]), 2660)

    def test_duplicate_economic_event_and_incomplete_coverage_are_rejected_before_creation(self):
        for name in ("duplicate", "coverage", "future", "rounding", "basis-identity"):
            cfg = dividend_policy()
            if name == "duplicate": cfg["events"].append({**cfg["events"][0], "event_id": "different-id"})
            elif name == "coverage": cfg["coverage_end"] = "2026-09-15"
            elif name == "future": cfg["events"][0]["announced_at"] = "2026-09-15T12:00:00+08:00"
            elif name == "rounding": cfg["events"][0]["cash_rounding"] = "inferred"
            else: cfg["events"][0]["event_id"] = "x"*200
            path = self.path.parent/(name + ".sqlite")
            with self.subTest(name=name), self.assertRaises(ValueError):
                OfflineOrderJournal.create(path, initial_cash="2600", initial_positions={SYMBOL: 100}, commission_bps="0.5",
                    minimum_commission="5", admission_policy=extended_policy(), dividend_policy=cfg)
            self.assertFalse(path.exists())

    def test_zero_position_records_zero_entitlement_without_inventing_cash(self):
        with OfflineOrderJournal.create(self.path.parent/"zero.sqlite", initial_cash="2600", initial_positions={}, commission_bps="0.5",
                minimum_commission="5", admission_policy=extended_policy(), dividend_policy=dividend_policy()) as book:
            start(book, NOW)
            book.record_dividend_entitlements(clock=lambda: NOW.replace(hour=15))
            book.accrue_dividends(clock=lambda: NOW + timedelta(days=1))
            self.assertEqual(book.snapshot()["dividends"]["entitlements"]["div-one"]["quantity"], 0)
            self.assertEqual(Decimal(book.snapshot()["cash"]), 2600)

    def test_credit_receipt_identity_conflict_cannot_change_cash(self):
        self.capture()
        self.accrue()
        pay = NOW + timedelta(days=2)
        self.book.record_dividend_cash_credit("div-one", "credit", "60", clock=lambda: pay)
        with self.assertRaisesRegex(ValueError, "conflicting"):
            self.book.record_dividend_cash_credit("div-one", "credit", "61", clock=lambda: pay)
        self.assertEqual(Decimal(self.book.snapshot()["cash"]), 2660)

    def test_clock_cannot_roll_back_after_an_accounting_transition(self):
        self.capture()
        with self.assertRaisesRegex(ValueError, "backward"):
            self.book.accrue_dividends(clock=lambda: NOW)

    def test_frozen_holder_rounding_is_exact_even_under_low_caller_precision(self):
        cfg = dividend_policy()
        cfg["events"][0]["net_cash_per_share"] = "0.005"
        with OfflineOrderJournal.create(self.path.parent/"rounding.sqlite", initial_cash="2600", initial_positions={SYMBOL: 101},
                commission_bps="0.5", minimum_commission="5", admission_policy=extended_policy(), dividend_policy=cfg) as book:
            cfg["events"][0]["net_cash_per_share"] = "100"
            start(book, NOW)
            with localcontext() as precision:
                precision.prec = 2
                book.record_dividend_entitlements(clock=lambda: NOW.replace(hour=15))
                book.accrue_dividends(clock=lambda: NOW + timedelta(days=1))
                self.assertEqual(Decimal(book.snapshot()["dividends"]["receivable_total"]), Decimal("0.51"))

    def test_empty_schedule_is_explicit_and_does_not_create_cash_or_entitlements(self):
        cfg = dividend_policy()
        cfg["events"] = []
        with OfflineOrderJournal.create(self.path.parent/"empty.sqlite", initial_cash="2600", initial_positions={},
                commission_bps="0.5", minimum_commission="5", admission_policy=extended_policy(), dividend_policy=cfg) as book:
            start(book, NOW)
            self.assertFalse(book.record_dividend_entitlements(clock=lambda: NOW.replace(hour=15)))
            self.assertFalse(book.accrue_dividends(clock=lambda: NOW + timedelta(days=1)))
            self.assertEqual(Decimal(book.snapshot()["cash"]), 2600)

    def test_price_outage_does_not_prevent_known_share_entitlement_capture(self):
        packet = context(self.book)
        packet["quotes"] = {}
        with self.assertRaises(ValueError):
            self.book.record_valuation(packet, clock=lambda: NOW)
        self.assertTrue(self.capture())
        self.assertEqual(self.book.snapshot()["dividends"]["entitlements"]["div-one"]["quantity"], 100)
        self.assertIn("portfolio_valuation_unavailable", self.book.snapshot()["faults"])

    def test_record_cutoff_cannot_overlap_the_inclusive_submission_window(self):
        cfg = dividend_policy()
        cfg["record_cutoff"] = "14:57"
        with self.assertRaisesRegex(ValueError, "cutoff"):
            with OfflineOrderJournal.create(self.path.parent/"overlap.sqlite", initial_cash="2600", initial_positions={SYMBOL: 100},
                    commission_bps="0.5", minimum_commission="5", admission_policy=extended_policy(), dividend_policy=cfg):
                pass


if __name__ == "__main__":
    unittest.main()
