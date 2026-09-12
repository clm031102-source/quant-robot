from datetime import timedelta
from decimal import Decimal, localcontext
from pathlib import Path
import tempfile
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal
from tests.unit.test_offline_dividends import dividend_policy, extended_policy
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, intent


def conversion_policy():
    return {"schema_version": 1, "mode": "offline_fixture_only", "source_ref": "synthetic-share-conversion",
        "coverage_start": "2026-09-14", "coverage_end": "2026-09-16", "record_cutoff": "15:00",
        "events": [{"event_id": "merge-one", "symbol": SYMBOL, "announced_at": "2026-09-11T12:00:00+08:00",
            "record_date": "2026-09-14", "suspension_date": "2026-09-15", "conversion_date": "2026-09-15", "tradable_date": "2026-09-16",
            "share_ratio": "0.5", "share_rounding": "ceil_per_holder", "fractional_disposition": "holder_share_credit"}]}


def start(book, now=NOW, *, price="4", sellable=None):
    packet = context(book, now)
    packet["quotes"][SYMBOL].update(bid=price, ask=price)
    basis = book.snapshot()["price_basis"].get(SYMBOL)
    if basis:
        packet["quotes"][SYMBOL]["price_basis_id"] = basis
    packet.update(instruments={s: {**instrument(s), "valid_until": "2026-09-16"} for s in (SYMBOL, OTHER)},
        sellable_positions=book.snapshot()["positions"] if sellable is None else sellable)
    book.begin_session(packet, clock=lambda: now)


class OfflineConversionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)/"conversion.sqlite"
        self.book = OfflineOrderJournal.create(self.path, initial_cash="2600", initial_positions={SYMBOL: 100},
            commission_bps="0.5", minimum_commission="5", admission_policy=extended_policy(), conversion_policy=conversion_policy())
        start(self.book)

    def tearDown(self):
        self.book.close()
        self.directory.cleanup()

    def capture(self):
        return self.book.record_conversion_entitlements(clock=lambda: NOW.replace(hour=15))

    def convert(self):
        return self.book.apply_share_conversions(clock=lambda: (NOW + timedelta(days=1)).replace(hour=9))

    def test_conversion_changes_inventory_and_basis_atomically_without_cash_or_order_mutation(self):
        self.capture()
        self.convert()
        snap = self.book.snapshot()
        self.assertEqual(snap["positions"], {SYMBOL: 50})
        self.assertEqual(snap["sellable_positions"].get(SYMBOL, 0), 0)
        self.assertEqual(Decimal(snap["cash"]), 2600)
        self.assertEqual(snap["orders"], {})
        self.assertEqual(snap["price_basis"][SYMBOL], "share_conversion:merge-one")

    def test_opening_packet_cannot_unlock_converted_shares_before_tradable_date(self):
        self.capture()
        self.convert()
        with self.assertRaisesRegex(ValueError, "locked"):
            start(self.book, NOW + timedelta(days=1), price="8")
        self.assertEqual(self.book.snapshot()["sellable_positions"].get(SYMBOL, 0), 0)

    def test_no_supported_mark_is_invented_during_conversion_halt(self):
        self.capture()
        self.convert()
        with self.assertRaisesRegex(ValueError, "tradable|valuation"):
            start(self.book, NOW + timedelta(days=1), price="8", sellable={})
        self.assertIsNone(self.book.snapshot()["portfolio_valuation"]["last_valid"])

    def test_tradable_session_requires_explicit_opening_shares_and_allows_full_odd_lot_sale(self):
        self.capture()
        self.convert()
        resume = NOW + timedelta(days=2)
        start(self.book, resume, price="8")
        snap = self.book.snapshot()
        self.assertEqual(snap["sellable_positions"], {SYMBOL: 50})
        self.assertEqual(Decimal(snap["risk_session"]["opening_equity"]), 3000)
        packet = context(self.book, resume)
        packet["quotes"][SYMBOL].update(bid="8", ask="8", price_basis_id=snap["price_basis"][SYMBOL])
        self.book.admit(intent(side="SELL", quantity=50, price="8", now=resume), packet, clock=lambda: resume)
        self.book.fill("one", "sale", 50, "8")
        self.assertEqual(Decimal(self.book.snapshot()["cash"]), 2995)

    def test_unresolved_orders_block_record_capture_without_resizing_them(self):
        self.book.admit(intent(side="SELL"), context(self.book), clock=lambda: NOW)
        before = self.book.snapshot()["orders"]
        with self.assertRaisesRegex(ValueError, "unresolved"):
            self.capture()
        self.assertEqual(self.book.snapshot()["orders"], before)

    def test_missing_record_holdings_are_not_inferred_at_conversion(self):
        with self.assertRaisesRegex(ValueError, "entitlement"):
            self.convert()
        self.assertEqual(self.book.snapshot()["positions"], {SYMBOL: 100})

    def test_capture_and_conversion_replay_do_not_apply_the_ratio_twice(self):
        self.assertTrue(self.capture())
        self.assertFalse(self.capture())
        self.assertTrue(self.convert())
        sequence = self.book.snapshot()["sequence"]
        self.assertFalse(self.convert())
        self.assertEqual(self.book.snapshot()["sequence"], sequence)
        self.assertEqual(self.book.snapshot()["positions"], {SYMBOL: 50})

    def test_record_cutoff_and_conversion_date_cannot_be_advanced(self):
        with self.assertRaisesRegex(ValueError, "cutoff"):
            self.book.record_conversion_entitlements(clock=lambda: NOW)
        self.capture()
        self.assertFalse(self.book.apply_share_conversions(clock=lambda: NOW.replace(hour=15)))
        self.assertEqual(self.book.snapshot()["positions"], {SYMBOL: 100})

    def test_open_orders_cannot_be_rewritten_or_automatically_cancelled_by_conversion(self):
        self.book.admit(intent(), context(self.book), clock=lambda: NOW)
        order = self.book.snapshot()["orders"]["one"]
        with self.assertRaises(ValueError):
            self.convert()
        self.assertEqual(self.book.snapshot()["orders"]["one"], order)
        self.assertEqual(Decimal(self.book.snapshot()["reserved_cash"]), 405)

    def test_rounding_is_applied_once_per_holder_with_no_implicit_cash(self):
        for name, disposition, expected, adjustment in (("ceil_per_holder", "holder_share_credit", 51, ".5"),
                ("floor_per_holder", "fund_assets", 50, "-.5")):
            cfg = conversion_policy()
            cfg["events"][0].update(share_rounding=name, fractional_disposition=disposition)
            with self.subTest(rounding=name), OfflineOrderJournal.create(self.path.parent/(name + ".sqlite"),
                    initial_cash="2600", initial_positions={SYMBOL: 101}, commission_bps="0.5", minimum_commission="5",
                    admission_policy=extended_policy(), conversion_policy=cfg) as book:
                start(book)
                book.record_conversion_entitlements(clock=lambda: NOW.replace(hour=15))
                with localcontext() as precision:
                    precision.prec = 2
                    book.apply_share_conversions(clock=lambda: NOW + timedelta(days=1))
                    snap = book.snapshot()
                self.assertEqual(snap["positions"], {SYMBOL: expected})
                self.assertEqual(Decimal(snap["cash"]), 2600)
                self.assertEqual(Decimal(snap["conversions"]["applied"]["merge-one"]["rounding_share_adjustment"]), Decimal(adjustment))

    def test_fractional_rejection_leaves_inventory_and_basis_untouched(self):
        cfg = conversion_policy()
        cfg["events"][0].update(share_rounding="reject_fractional", fractional_disposition="none")
        with OfflineOrderJournal.create(self.path.parent/"fraction.sqlite", initial_cash="2600", initial_positions={SYMBOL: 101},
                commission_bps="0.5", minimum_commission="5", admission_policy=extended_policy(), conversion_policy=cfg) as book:
            start(book)
            book.record_conversion_entitlements(clock=lambda: NOW.replace(hour=15))
            with self.assertRaisesRegex(ValueError, "fractional"):
                book.apply_share_conversions(clock=lambda: NOW + timedelta(days=1))
            self.assertEqual(book.snapshot()["positions"], {SYMBOL: 101})
            self.assertEqual(book.snapshot()["price_basis"], {})

    def test_realistic_eight_decimal_ratio_is_not_truncated_to_money_precision(self):
        cfg = conversion_policy()
        cfg["events"][0]["share_ratio"] = "0.83788015"
        with OfflineOrderJournal.create(self.path.parent/"precise.sqlite", initial_cash="2600", initial_positions={SYMBOL: 100},
                commission_bps="0.5", minimum_commission="5", admission_policy=extended_policy(), conversion_policy=cfg) as book:
            start(book)
            book.record_conversion_entitlements(clock=lambda: NOW.replace(hour=15))
            book.apply_share_conversions(clock=lambda: NOW + timedelta(days=1))
            row = book.snapshot()["conversions"]["applied"]["merge-one"]
            self.assertEqual(row["new_quantity"], 84)
            self.assertEqual(Decimal(row["unrounded_quantity"]), Decimal("83.78801500"))

    def test_late_fill_before_conversion_invalidates_record_holdings_and_is_not_overwritten(self):
        self.book.admit(intent(), context(self.book), clock=lambda: NOW)
        self.book.report_status("one", "cancel", "CANCELLED", 0)
        self.capture()
        self.book.fill("one", "late", 40, "4")
        with self.assertRaisesRegex(ValueError, "review"):
            self.convert()
        self.assertEqual(self.book.snapshot()["positions"], {SYMBOL: 140})
        self.assertIn("share_conversion_requires_review", self.book.snapshot()["faults"])

    def test_late_old_basis_fill_after_conversion_is_retained_without_mixing_share_units(self):
        self.book.admit(intent(), context(self.book), clock=lambda: NOW)
        self.book.report_status("one", "cancel", "CANCELLED", 0)
        self.capture()
        self.convert()
        before = self.book.snapshot()
        self.assertTrue(self.book.fill("one", "late", 40, "4"))
        self.assertFalse(self.book.fill("one", "late", 40, "4"))
        snap = self.book.snapshot()
        self.assertEqual(snap["positions"], {SYMBOL: 50})
        self.assertEqual(snap["cash"], before["cash"])
        self.assertEqual(snap["orders"], before["orders"])
        self.assertEqual(snap["conversions"]["unapplied_fills"]["late"]["quantity"], 40)
        self.assertIn("share_conversion_requires_review", snap["faults"])

    def test_deferred_fill_quantities_still_obey_original_order_total(self):
        self.book.admit(intent(), context(self.book), clock=lambda: NOW)
        self.book.report_status("one", "cancel", "CANCELLED", 0)
        self.capture(); self.convert()
        self.book.fill("one", "late-a", 60, "4")
        with self.assertRaisesRegex(ValueError, "exceeds"):
            self.book.fill("one", "late-b", 41, "4")
        self.assertEqual(len(self.book.snapshot()["conversions"]["unapplied_fills"]), 1)

    def test_order_reconciliation_cannot_clear_unresolved_share_basis(self):
        self.book.admit(intent(), context(self.book), clock=lambda: NOW)
        self.book.report_status("one", "cancel", "CANCELLED", 0)
        self.capture(); self.convert()
        self.book.fill("one", "late", 40, "4")
        snap = self.book.snapshot()
        fields = ("status", "filled_quantity", "filled_notional", "commission")
        self.book.reconcile(snapshot_id="complete", expected_sequence=snap["sequence"], cash=snap["cash"], positions=snap["positions"],
            orders={"one": {key: snap["orders"]["one"][key] for key in fields}})
        self.assertIn("share_conversion_requires_review", self.book.snapshot()["faults"])

    def test_restart_preserves_locks_and_cannot_make_shares_available(self):
        self.capture(); self.convert()
        before = self.book.snapshot()
        self.book.close()
        self.book = OfflineOrderJournal(self.path)
        snap = self.book.snapshot()
        self.assertEqual(snap["conversions"], before["conversions"])
        self.assertEqual(snap["available_positions"], {SYMBOL: 0})

    def test_operator_stop_survives_conversion_and_does_not_block_accounting(self):
        self.book.set_kill_switch(True, reason="operator")
        self.capture(); self.convert()
        self.assertTrue(self.book.snapshot()["kill_switch"])
        self.assertEqual(self.book.snapshot()["positions"], {SYMBOL: 50})

    def test_price_outage_does_not_prevent_capture_or_conversion(self):
        packet = context(self.book)
        packet["quotes"] = {}
        with self.assertRaises(ValueError):
            self.book.record_valuation(packet, clock=lambda: NOW)
        self.capture(); self.convert()
        self.assertEqual(self.book.snapshot()["positions"], {SYMBOL: 50})
        self.assertIn("portfolio_valuation_unavailable", self.book.snapshot()["faults"])

    def test_declared_suspension_blocks_false_trading_quotes_before_conversion(self):
        cfg = conversion_policy()
        cfg["events"][0]["conversion_date"] = "2026-09-16"
        with OfflineOrderJournal.create(self.path.parent/"suspended.sqlite", initial_cash="2600", initial_positions={SYMBOL: 100},
                commission_bps="0.5", minimum_commission="5", admission_policy=extended_policy(), conversion_policy=cfg) as book:
            start(book)
            book.record_conversion_entitlements(clock=lambda: NOW.replace(hour=15))
            with self.assertRaisesRegex(ValueError, "tradable"):
                start(book, NOW + timedelta(days=1))

    def test_zero_holder_cannot_buy_during_known_conversion_suspension(self):
        with OfflineOrderJournal.create(self.path.parent/"zero.sqlite", initial_cash="2600", initial_positions={}, commission_bps="0.5",
                minimum_commission="5", admission_policy=extended_policy(), conversion_policy=conversion_policy()) as book:
            start(book)
            book.record_conversion_entitlements(clock=lambda: NOW.replace(hour=15))
            tomorrow = NOW + timedelta(days=1)
            book.apply_share_conversions(clock=lambda: tomorrow.replace(hour=9))
            start(book, tomorrow, price="8")
            packet = context(book, tomorrow)
            packet["quotes"][SYMBOL].update(bid="8", ask="8", price_basis_id=book.snapshot()["price_basis"][SYMBOL])
            with self.assertRaisesRegex(ValueError, "tradable|locked"):
                book.admit(intent(price="8", now=tomorrow), packet, clock=lambda: tomorrow)

    def test_dividend_entitlement_survives_conversion_and_combined_basis_does_not_roll_back(self):
        with OfflineOrderJournal.create(self.path.parent/"combined.sqlite", initial_cash="2600", initial_positions={SYMBOL: 100},
                commission_bps="0.5", minimum_commission="5", admission_policy=extended_policy(), conversion_policy=conversion_policy(),
                dividend_policy=dividend_policy()) as book:
            start(book)
            record = NOW.replace(hour=15)
            book.record_conversion_entitlements(clock=lambda: record)
            book.record_dividend_entitlements(clock=lambda: record)
            tomorrow = NOW + timedelta(days=1)
            book.apply_share_conversions(clock=lambda: tomorrow.replace(hour=9))
            split_basis = book.snapshot()["price_basis"][SYMBOL]
            book.accrue_dividends(clock=lambda: tomorrow.replace(hour=9))
            snap = book.snapshot()
            self.assertEqual(snap["positions"], {SYMBOL: 50})
            self.assertEqual(Decimal(snap["dividends"]["receivable_total"]), 60)
            self.assertNotIn(snap["price_basis"][SYMBOL], (split_basis, "cash_dividend:div-one"))
            resume = NOW + timedelta(days=2)
            start(book, resume, price="6.8")
            self.assertEqual(Decimal(book.snapshot()["risk_session"]["opening_equity"]), 3000)
            packet = context(book, resume)
            packet["quotes"][SYMBOL].update(bid="6.8", ask="6.8", price_basis_id=split_basis)
            with self.assertRaisesRegex(ValueError, "price basis"):
                book.record_valuation(packet, clock=lambda: resume)

    def test_invalid_rounding_ratios_dates_and_duplicate_events_are_rejected_before_creation(self):
        for case in ("float", "precision", "disposition", "rounding_type", "chronology", "duplicate", "cutoff"):
            cfg = conversion_policy()
            row = cfg["events"][0]
            if case == "float": row["share_ratio"] = 0.5
            elif case == "precision": row["share_ratio"] = "0.0000000000001"
            elif case == "disposition": row["fractional_disposition"] = "cash_in_lieu"
            elif case == "rounding_type": row["share_rounding"] = []
            elif case == "chronology": row["record_date"] = "2026-09-16"
            elif case == "duplicate": cfg["events"].append({**row, "event_id": "second-id"})
            else: cfg["record_cutoff"] = "14:57"
            path = self.path.parent/(case + ".sqlite")
            with self.subTest(case=case), self.assertRaises(ValueError):
                with OfflineOrderJournal.create(path, initial_cash="2600", initial_positions={SYMBOL: 100}, commission_bps="0.5",
                        minimum_commission="5", admission_policy=extended_policy(), conversion_policy=cfg):
                    pass
            self.assertFalse(path.exists())

    def test_failed_second_asset_conversion_does_not_partially_change_the_first(self):
        cfg = conversion_policy()
        cfg["events"].append({**cfg["events"][0], "event_id": "other", "symbol": OTHER, "share_ratio": "0.333",
            "share_rounding": "reject_fractional", "fractional_disposition": "none"})
        with OfflineOrderJournal.create(self.path.parent/"batch.sqlite", initial_cash="2200", initial_positions={SYMBOL: 100, OTHER: 100},
                commission_bps="0.5", minimum_commission="5", admission_policy=extended_policy(), conversion_policy=cfg) as book:
            start(book)
            book.record_conversion_entitlements(clock=lambda: NOW.replace(hour=15))
            with self.assertRaisesRegex(ValueError, "fractional"):
                book.apply_share_conversions(clock=lambda: NOW + timedelta(days=1))
            self.assertEqual(book.snapshot()["positions"], {SYMBOL: 100, OTHER: 100})
            self.assertEqual(book.snapshot()["price_basis"], {})

    def test_combined_price_basis_is_independent_of_same_date_processing_order(self):
        bases = []
        for first in ("dividend", "conversion"):
            with OfflineOrderJournal.create(self.path.parent/("combined-" + first + ".sqlite"), initial_cash="2600", initial_positions={SYMBOL: 100},
                    commission_bps="0.5", minimum_commission="5", admission_policy=extended_policy(), conversion_policy=conversion_policy(),
                    dividend_policy=dividend_policy()) as book:
                start(book)
                record = NOW.replace(hour=15)
                book.record_conversion_entitlements(clock=lambda: record)
                book.record_dividend_entitlements(clock=lambda: record)
                methods = [book.accrue_dividends, book.apply_share_conversions]
                if first == "conversion": methods.reverse()
                for method in methods: method(clock=lambda: NOW + timedelta(days=1))
                bases.append(book.snapshot()["price_basis"])
        self.assertEqual(bases[0], bases[1])

    def test_tradable_date_does_not_override_zero_available_shares_in_opening_evidence(self):
        self.capture(); self.convert()
        resume = NOW + timedelta(days=2)
        start(self.book, resume, price="8", sellable={})
        self.assertEqual(self.book.snapshot()["available_positions"], {SYMBOL: 0})
        packet = context(self.book, resume)
        packet["quotes"][SYMBOL].update(bid="8", ask="8", price_basis_id=self.book.snapshot()["price_basis"][SYMBOL])
        with self.assertRaisesRegex(ValueError, "sellable"):
            self.book.admit(intent(side="SELL", quantity=50, price="8", now=resume), packet, clock=lambda: resume)

    def test_conversion_preserves_prior_risk_stop_and_marks_the_old_valuation_as_outdated(self):
        packet = context(self.book)
        packet["quotes"][SYMBOL].update(bid="3.4", ask="3.4")
        self.book.record_valuation(packet, clock=lambda: NOW)
        previous = self.book.snapshot()["portfolio_valuation"]["last_valid"]
        self.capture(); self.convert()
        snap = self.book.snapshot()
        self.assertTrue(snap["risk_session"]["risk_stop"])
        self.assertEqual(snap["portfolio_valuation"]["last_valid"], previous)
        self.assertFalse(snap["portfolio_valuation"]["matches_current_journal"])


if __name__ == "__main__":
    unittest.main()
