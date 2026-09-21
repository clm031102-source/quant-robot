from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal
from quant_robot.execution.offline_intent_contract import fingerprint, normalize_policy
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, intent, policy


class OfflineSessionBaselineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "daily-baseline.sqlite"
        cfg = {**policy(), "schema_version": 2, "max_drawdown": ".08", "capital_limit_cny": "10000",
            "daily_loss_basis": "previous_session_close_v1", "exposure_stop_action": "reduce_only"}
        self.book = OfflineOrderJournal.create(self.path, initial_cash="9010", initial_positions={SYMBOL: 200},
            commission_bps="5", minimum_commission="5", admission_policy=cfg)
        self.addCleanup(lambda: self.book.close())
        self.start(NOW, "4.95")

    def packet(self, now, price):
        packet = context(self.book, now)
        packet["quotes"][SYMBOL].update(bid=price, ask=price)
        return packet

    def start(self, now, price):
        packet = self.packet(now, price)
        packet.update(instruments={code: instrument(code) for code in (SYMBOL, OTHER)}, sellable_positions={SYMBOL: 200})
        return self.book.begin_session(packet, clock=lambda: now)

    def close_mark(self, price="4.95", seconds=0):
        now = NOW.replace(hour=15, minute=0) + timedelta(seconds=seconds)
        return self.book.record_valuation(self.packet(now, price), clock=lambda: now)

    def test_overnight_loss_stops_at_opening_and_is_not_erased_by_intraday_recovery(self):
        self.close_mark()
        tomorrow = NOW + timedelta(days=1)
        self.start(tomorrow, "4.455")
        self.book.record_valuation(self.packet(tomorrow, "4.455"), clock=lambda: tomorrow)
        snap = self.book.snapshot()
        valuation = snap["portfolio_valuation"]["last_valid"]
        self.assertEqual(Decimal(valuation["book_loss_from_open"]), 0)
        self.assertEqual(Decimal(valuation["projected_daily_loss"]), 99)
        self.assertEqual(snap["risk_session"]["risk_stop_causes"], ["daily_loss"])
        self.book.record_valuation(self.packet(tomorrow, "5.01"), clock=lambda: tomorrow)
        with self.assertRaisesRegex(ValueError, "session risk stop"):
            self.book.admit(intent(side="SELL", price="5.01", now=tomorrow), self.packet(tomorrow, "5.01"), clock=lambda: tomorrow)

    def test_missing_previous_close_blocks_opening_instead_of_rebasing(self):
        with self.assertRaisesRegex(ValueError, "previous.*close"):
            self.start(NOW + timedelta(days=1), "4.455")
        self.assertEqual(self.book.snapshot()["risk_session"]["session_date"], NOW.date().isoformat())

    def test_only_first_usable_observation_in_the_fixed_closing_window_is_retained(self):
        early = NOW.replace(hour=14, minute=59, second=59)
        self.book.record_valuation(self.packet(early, "4.95"), clock=lambda: early)
        self.assertIsNone(self.book.snapshot()["last_session_close"])
        self.close_mark("4.95")
        original = self.book.snapshot()["last_session_close"]
        self.close_mark("5.01", seconds=1)
        self.assertEqual(self.book.snapshot()["last_session_close"], original)
        self.assertEqual(Decimal(original["book_equity"]), 10000)
        self.assertFalse(original["official_exchange_close_verified"])

    def test_late_or_prestamped_feed_cannot_create_a_close(self):
        now = NOW.replace(hour=15, minute=0)
        packet = self.packet(now, "4.95")
        packet["as_of"] = (now - timedelta(seconds=1)).isoformat()
        for quote in packet["quotes"].values():
            quote["timestamp"] = packet["as_of"]
        self.book.record_valuation(packet, clock=lambda: now)
        self.assertIsNone(self.book.snapshot()["last_session_close"])
        self.close_mark(seconds=31)
        self.assertIsNone(self.book.snapshot()["last_session_close"])
        with self.assertRaisesRegex(ValueError, "previous.*close"):
            self.start(NOW + timedelta(days=1), "4.455")

    def test_stale_quote_or_unresolved_orders_prevent_close_qualification(self):
        self.book.admit(intent(side="SELL", price="4.95"), self.packet(NOW, "4.95"), clock=lambda: NOW)
        self.close_mark()
        self.assertIsNone(self.book.snapshot()["last_session_close"])
        self.book.report_status("one", "cancel", "CANCELLED", 0)
        now = NOW.replace(hour=15, minute=0, second=1)
        packet = self.packet(now, "4.95")
        for quote in packet["quotes"].values():
            quote["timestamp"] = (now - timedelta(seconds=31)).isoformat()
        with self.assertRaises(ValueError):
            self.book.record_valuation(packet, clock=lambda: now)
        self.assertIsNone(self.book.snapshot()["last_session_close"])
        self.close_mark(seconds=2)
        self.assertIsNotNone(self.book.snapshot()["last_session_close"])

    def test_closing_reference_survives_reopen_and_cannot_be_edited_through_a_snapshot(self):
        self.close_mark()
        snap = self.book.snapshot()
        snap["last_session_close"]["book_equity"] = "1"
        self.book.close()
        self.book = OfflineOrderJournal(self.path)
        self.assertEqual(Decimal(self.book.snapshot()["last_session_close"]["book_equity"]), 10000)
        tomorrow = NOW + timedelta(days=1)
        self.start(tomorrow, "4.455")
        self.assertEqual(self.book.snapshot()["risk_session"]["risk_stop_causes"], ["daily_loss"])

    def test_opening_cannot_skip_a_configured_session_using_an_older_close(self):
        self.close_mark()
        # Extend a separate frozen calendar; never mutate the original journal policy.
        path = Path(self.temp.name) / "calendar-gap.sqlite"
        cfg = OfflineOrderJournal.inspect_configuration(self.path)["admission_policy"]
        cfg["session_dates"].append("2026-09-16")
        with OfflineOrderJournal.create(path, initial_cash="10000", initial_positions={}, commission_bps="5",
                minimum_commission="5", admission_policy=cfg) as other:
            for now in (NOW, NOW.replace(hour=15, minute=0)):
                packet = context(other, now)
                if now == NOW:
                    packet.update(instruments={code: instrument(code) for code in (SYMBOL, OTHER)}, sellable_positions={})
                    other.begin_session(packet, clock=lambda: now)
                else:
                    other.record_valuation(packet, clock=lambda: now)
            day3 = NOW + timedelta(days=2)
            packet = context(other, day3)
            packet.update(instruments={code: {**instrument(code), "valid_until": "2026-09-16"} for code in (SYMBOL, OTHER)}, sellable_positions={})
            with self.assertRaisesRegex(ValueError, "previous.*close"):
                other.begin_session(packet, clock=lambda: day3)

    def test_pending_commission_is_added_to_overnight_loss_before_admission(self):
        self.close_mark()
        tomorrow = NOW + timedelta(days=1)
        self.start(tomorrow, "4.675")
        self.assertFalse(self.book.snapshot()["paused"])
        with self.assertRaisesRegex(ValueError, "daily loss"):
            self.book.admit(intent(side="SELL", price="4.675", now=tomorrow), self.packet(tomorrow, "4.675"), clock=lambda: tomorrow)
        self.assertEqual(self.book.snapshot()["risk_session"]["risk_stop_causes"], ["daily_loss"])

    def test_intraday_gains_do_not_move_the_previous_close_loss_reference(self):
        self.close_mark()
        tomorrow = NOW + timedelta(days=1)
        self.start(tomorrow, "4.95")
        self.book.record_valuation(self.packet(tomorrow, "4.99"), clock=lambda: tomorrow)
        later = tomorrow + timedelta(seconds=1)
        self.book.record_valuation(self.packet(later, "4.70"), clock=lambda: later)
        snap = self.book.snapshot()
        self.assertEqual(Decimal(snap["portfolio_valuation"]["last_valid"]["projected_daily_loss"]), 50)
        self.assertEqual(Decimal(snap["risk_session"]["daily_loss_reference_equity"]), 10000)
        self.assertFalse(snap["paused"])

    def test_baseline_mode_requires_explicit_versioned_policy_and_bounded_quote_age(self):
        cfg = {**policy(), "schema_version": 2, "max_drawdown": ".08"}
        old = normalize_policy(cfg)
        self.assertNotIn("daily_loss_basis", old)
        new = normalize_policy({**cfg, "daily_loss_basis": "previous_session_close_v1"})
        self.assertNotEqual(fingerprint(old), fingerprint(new))
        for change in ({"daily_loss_basis": None}, {"daily_loss_basis": True}, {"daily_loss_basis": "previous_close"},
                {"max_quote_age_seconds": 31}, {"max_context_age_seconds": 31}, {"trading_windows": [["09:30", "15:01"]]},
                {"schema_version": 1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                normalize_policy({**new, **change})


if __name__ == "__main__":
    unittest.main()
