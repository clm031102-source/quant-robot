from datetime import datetime, timedelta
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal

NOW = datetime.fromisoformat("2026-09-14T10:00:00+08:00")
SYMBOL = "510300.SH"
OTHER = "159915.SZ"


def policy():
    return {"schema_version": 1, "mode": "offline_fixture_only", "policy_id": "fixture-policy-v1",
        "strategy_id": "fixture", "strategy_version": "1", "allowed_symbols": [SYMBOL, OTHER],
        "capital_limit_cny": "3000", "max_position_cny": "1000", "max_daily_loss_cny": "60",
        "max_adv_participation": "0.01", "max_slippage_bps": "10", "max_spread_bps": "20",
        "max_quote_age_seconds": 30, "max_context_age_seconds": 30, "max_signal_age_seconds": 300,
        "max_adv_age_days": 7, "session_dates": ["2026-09-14", "2026-09-15"],
        "trading_windows": [["09:30", "11:30"], ["13:00", "14:57"]]}


def instrument(code=SYMBOL, settlement="T1"):
    return {"symbol": code, "exchange": "SSE" if code.endswith("SH") else "SZSE", "instrument_type": "ETF",
        "lot_size": 100, "price_tick": "0.001", "settlement": settlement, "odd_lot_sell_allowed": True,
        "adv_shares": "100000", "adv_as_of": "2026-09-11", "valid_from": "2026-09-11", "valid_until": "2026-09-15",
        "source_ref": "synthetic-instrument-master"}


def quote(code=SYMBOL, now=NOW, price="4"):
    return {"symbol": code, "exchange": "SSE" if code.endswith("SH") else "SZSE", "timestamp": now.isoformat(),
        "bid": price, "ask": price, "trade_status": "TRADING", "source_ref": "synthetic-quote"}


def context(book, now=NOW):
    state = book.snapshot()
    return {"schema_version": 1, "mode": "offline_fixture_only", "snapshot_id": "context-" + str(state["sequence"]),
        "source_ref": "synthetic-context", "as_of": now.isoformat(), "session_date": now.date().isoformat(),
        "journal_sequence": state["sequence"], "journal_hash": state["journal_hash"],
        "quotes": {code: quote(code, now) for code in (SYMBOL, OTHER)}}


def intent(key="one", *, side="BUY", quantity=100, price="4", code=SYMBOL, now=NOW):
    return {"schema_version": 1, "client_intent_id": key, "idempotency_key": "key-" + key,
        "strategy_id": "fixture", "strategy_version": "1", "signal_timestamp": now.isoformat(),
        "symbol": code, "exchange": "SSE" if code.endswith("SH") else "SZSE", "side": side,
        "quantity": quantity, "order_type": "LIMIT", "limit_price": price, "time_in_force": "DAY",
        "max_slippage_bps": "10", "expires_at": (now + timedelta(minutes=2)).isoformat()}


class OfflineAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "guarded.sqlite"
        self.book = OfflineOrderJournal.create(self.path, initial_cash="3000", initial_positions={},
            commission_bps="0.5", minimum_commission="5", admission_policy=policy())
        self.addCleanup(lambda: self.book.close())
        self.start()

    def start(self, now=NOW, sellable=None, metadata=None):
        packet = context(self.book, now)
        packet.update(instruments=metadata or {s: instrument(s) for s in (SYMBOL, OTHER)},
            sellable_positions=sellable if sellable is not None else self.book.snapshot()["positions"])
        self.book.begin_session(packet, clock=lambda: now)

    def admit(self, order=None, packet=None, now=NOW):
        return self.book.admit(order or intent(), packet or context(self.book, now), clock=lambda: now)

    def test_full_intent_is_atomically_bound_to_policy_and_order(self):
        self.admit()
        state = self.book.snapshot()
        row = state["orders"]["one"]
        self.assertEqual(row["admission"]["intent"]["strategy_version"], "1")
        self.assertEqual(row["admission"]["policy_fingerprint"], state["admission_policy_fingerprint"])
        self.assertEqual(Decimal(state["reserved_cash"]), 405)
        self.assertFalse(state["executable"])

    def test_direct_registration_cannot_bypass_guarded_mode(self):
        with self.assertRaisesRegex(ValueError, "admission"):
            self.book.register(order_id="raw", idempotency_key="raw", symbol=SYMBOL, side="BUY", quantity=100, limit_price="4")

    def test_strategy_version_and_required_schema_are_enforced(self):
        for index, change in enumerate((lambda o: o.update(strategy_version="2"),
                lambda o: o.pop("signal_timestamp"), lambda o: o.update(order_type="MARKET"),
                lambda o: o.update(time_in_force="GTC"), lambda o: o.update(executable=True))):
            order = intent(str(index))
            change(order)
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.admit(order)
        self.assertEqual(self.book.snapshot()["orders"], {})

    def test_future_naive_and_expired_signal_times_fail(self):
        cases = [{"signal_timestamp": (NOW + timedelta(seconds=1)).isoformat()},
                 {"signal_timestamp": "2026-09-14T10:00:00"},
                 {"signal_timestamp": (NOW - timedelta(seconds=301)).isoformat()},
                 {"expires_at": NOW.isoformat()}, {"expires_at": "2026-09-15T10:00:00+08:00"}]
        for index, changes in enumerate(cases):
            order = intent(str(index))
            order.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.admit(order)

    def test_quote_context_freshness_and_journal_anchor_are_required(self):
        changes = [lambda p: p["quotes"][SYMBOL].update(timestamp=(NOW - timedelta(seconds=31)).isoformat()),
                   lambda p: p["quotes"][SYMBOL].update(timestamp=(NOW + timedelta(seconds=1)).isoformat()),
                   lambda p: p.update(as_of=(NOW - timedelta(seconds=31)).isoformat()),
                   lambda p: p.update(journal_sequence=0), lambda p: p.update(journal_hash="0" * 64)]
        for index, change in enumerate(changes):
            packet = context(self.book)
            change(packet)
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.admit(intent(str(index)), packet)

    def test_lot_tick_halt_spread_and_slippage_checks(self):
        cases = [(intent("lot", quantity=101), None), (intent("tick", price="4.0001"), None),
                 (intent("slip", price="4.005"), None)]
        for order, packet in cases:
            with self.subTest(key=order["client_intent_id"]), self.assertRaises(ValueError):
                self.admit(order, packet)
        for index, change in enumerate((lambda q: q.update(trade_status="HALTED"),
                lambda q: q.update(ask="4.1"), lambda q: q.update(bid="4.1", ask="4"),
                lambda q: q.update(exchange="SZSE"))):
            packet = context(self.book)
            change(packet["quotes"][SYMBOL])
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.admit(intent("quote-" + str(index)), packet)

    def test_rejected_intent_is_audited_and_cannot_be_repriced_under_same_key(self):
        with self.assertRaises(ValueError):
            self.admit(intent(quantity=101))
        with self.assertRaisesRegex(ValueError, "identity|idempotency"):
            self.admit(intent())
        connection = sqlite3.connect(self.path)
        try:
            events = [json.loads(r[0]) for r in connection.execute("SELECT payload FROM events")]
        finally:
            connection.close()
        self.assertTrue(any(e["kind"] == "ADMISSION_DENIED" for e in events))
        self.assertFalse(self.book.snapshot()["paused"])

    def test_pending_buys_count_toward_position_cap_before_any_fill(self):
        self.admit(intent("first", quantity=200))
        with self.assertRaisesRegex(ValueError, "position"):
            self.admit(intent("second"))
        self.assertEqual(len(self.book.snapshot()["orders"]), 1)

    def test_t1_bought_shares_are_locked_until_next_session(self):
        self.admit()
        self.book.fill("one", "f1", 100, "4")
        with self.assertRaisesRegex(ValueError, "sellable"):
            self.admit(intent("sell", side="SELL"))
        tomorrow = NOW + timedelta(days=1)
        self.start(tomorrow)
        self.admit(intent("tomorrow-sell", side="SELL", now=tomorrow), now=tomorrow)

    def test_explicit_t0_metadata_makes_new_fills_sellable(self):
        self.book.close()
        p = Path(self.tmp.name) / "t0.sqlite"
        self.book = OfflineOrderJournal.create(p, initial_cash="3000", initial_positions={},
            commission_bps="0.5", minimum_commission="5", admission_policy=policy())
        self.start(metadata={s: instrument(s, "T0") for s in (SYMBOL, OTHER)})
        self.admit()
        self.book.fill("one", "f1", 100, "4")
        self.admit(intent("sell", side="SELL"))

    def test_restart_and_reconciliation_do_not_unlock_t1_or_reset_session_baseline(self):
        self.admit()
        self.book.fill("one", "f1", 100, "4")
        original = self.book.snapshot()["risk_session"]["opening_equity"]
        self.book.close()
        self.book = OfflineOrderJournal(self.path)
        state = self.book.snapshot()
        self.book.reconcile(snapshot_id="recheck", expected_sequence=state["sequence"], cash=state["cash"], positions=state["positions"],
            orders={key: {field: row[field] for field in ("status", "filled_quantity", "filled_notional", "commission")}
                for key, row in state["orders"].items()})
        with self.assertRaisesRegex(ValueError, "sellable"):
            self.admit(intent("sell", side="SELL"))
        with self.assertRaisesRegex(ValueError, "session"):
            self.start()
        self.assertEqual(self.book.snapshot()["risk_session"]["opening_equity"], original)

    def test_daily_loss_includes_pending_fees_and_latches_for_session(self):
        self.book.close()
        self.book = OfflineOrderJournal.create(Path(self.tmp.name) / "loss.sqlite", initial_cash="2000", initial_positions={SYMBOL: 100},
            commission_bps="0.5", minimum_commission="5", admission_policy=policy())
        self.start()
        packet = context(self.book)
        packet["quotes"][SYMBOL].update(bid="3.45", ask="3.45")
        with self.assertRaisesRegex(ValueError, "daily loss"):
            self.admit(intent("loss", code=OTHER), packet)
        self.assertTrue(self.book.snapshot()["risk_session"]["risk_stop"])
        with self.assertRaisesRegex(ValueError, "risk stop"):
            self.admit(intent("rebound", code=OTHER))

    def test_missing_price_for_any_holding_blocks_equity_risk_check(self):
        self.admit()
        self.book.fill("one", "f1", 100, "4")
        packet = context(self.book)
        del packet["quotes"][SYMBOL]
        with self.assertRaisesRegex(ValueError, "quote"):
            self.admit(intent("other", code=OTHER), packet)

    def test_day_volume_budget_counts_cancelled_partial_fills(self):
        self.book.close()
        self.book = OfflineOrderJournal.create(Path(self.tmp.name) / "volume.sqlite", initial_cash="3000", initial_positions={},
            commission_bps="0.5", minimum_commission="5", admission_policy=policy())
        metadata = {s: instrument(s) for s in (SYMBOL, OTHER)}
        metadata[SYMBOL]["adv_shares"] = "10000"
        self.start(metadata=metadata)
        self.admit()
        self.book.fill("one", "f1", 50, "4")
        self.book.report_status("one", "cancel", "CANCELLED", 50)
        with self.assertRaisesRegex(ValueError, "participation"):
            self.admit(intent("second"))

    def test_session_roll_refuses_unfinished_day_orders(self):
        self.admit()
        with self.assertRaisesRegex(ValueError, "unfinished"):
            self.start(NOW + timedelta(days=1))

    def test_lunch_break_and_unlisted_session_fail(self):
        for now in (NOW.replace(hour=12), NOW + timedelta(days=2)):
            with self.subTest(now=now), self.assertRaises(ValueError):
                self.admit(intent(str(now), now=now), now=now)

    def test_locked_odd_lot_sale_can_only_clear_all_unreserved_sellable_shares(self):
        self.book.close()
        self.book = OfflineOrderJournal.create(Path(self.tmp.name) / "oddlot.sqlite", initial_cash="2000", initial_positions={SYMBOL: 150},
            commission_bps="0.5", minimum_commission="5", admission_policy=policy())
        self.start(sellable={SYMBOL: 80})
        with self.assertRaisesRegex(ValueError, "odd-lot"):
            self.admit(intent("split", side="SELL", quantity=50))
        self.admit(intent("all-sellable", side="SELL", quantity=80))
        self.assertEqual(self.book.snapshot()["reserved_positions"], {SYMBOL: 80})
        with self.assertRaisesRegex(ValueError, "sellable"):
            self.admit(intent("locked", side="SELL", quantity=1))

    def test_risk_stop_survives_restart_reconciliation_and_operator_switch(self):
        self.book.close()
        self.path = Path(self.tmp.name) / "riskstop.sqlite"
        self.book = OfflineOrderJournal.create(self.path, initial_cash="2000", initial_positions={SYMBOL: 100},
            commission_bps="0.5", minimum_commission="5", admission_policy=policy())
        self.start()
        packet = context(self.book)
        packet["quotes"][SYMBOL].update(bid="3.45", ask="3.45")
        with self.assertRaisesRegex(ValueError, "daily loss"):
            self.admit(intent("loss", code=OTHER), packet)
        self.book.close()
        self.book = OfflineOrderJournal(self.path)
        state = self.book.snapshot()
        self.book.reconcile(snapshot_id="correct", expected_sequence=state["sequence"], cash=state["cash"], positions=state["positions"], orders={})
        self.book.set_kill_switch(False, reason="fixture operator release")
        self.assertTrue(self.book.snapshot()["paused"])
        with self.assertRaisesRegex(ValueError, "risk stop"):
            self.admit(intent("rebound", code=OTHER))

    def test_reducing_sell_is_allowed_when_market_move_puts_position_above_cap(self):
        self.book.close()
        self.book = OfflineOrderJournal.create(Path(self.tmp.name) / "reduce.sqlite", initial_cash="1000", initial_positions={SYMBOL: 300},
            commission_bps="0.5", minimum_commission="5", admission_policy=policy())
        self.start()
        self.admit(intent("reduce", side="SELL"))
        self.assertEqual(self.book.snapshot()["orders"]["reduce"]["quantity"], 100)

    def test_daily_fees_cannot_be_hidden_by_alternating_buys_and_sells(self):
        self.book.close()
        self.book = OfflineOrderJournal.create(Path(self.tmp.name) / "fees.sqlite", initial_cash="3000", initial_positions={},
            commission_bps="0.5", minimum_commission="5", admission_policy=policy())
        self.start(metadata={s: instrument(s, "T0") for s in (SYMBOL, OTHER)})
        for index in range(11):
            key = "trade-" + str(index)
            self.admit(intent(key, side="BUY" if index % 2 == 0 else "SELL"))
            self.book.fill(key, key, 100, "4")
        with self.assertRaisesRegex(ValueError, "daily loss"):
            self.admit(intent("twelfth", side="SELL"))
        self.assertEqual(Decimal(self.book.snapshot()["cash"]), Decimal("2545"))

    def test_expired_or_future_metadata_never_initializes_session(self):
        for label, field, value in (("expired", "valid_until", "2026-09-11"),
                ("future", "adv_as_of", "2026-09-14"), ("old", "adv_as_of", "2026-08-01")):
            self.book.close()
            self.book = OfflineOrderJournal.create(Path(self.tmp.name) / (label + ".sqlite"), initial_cash="3000", initial_positions={},
                commission_bps="0.5", minimum_commission="5", admission_policy=policy())
            metadata = {s: instrument(s) for s in (SYMBOL, OTHER)}
            metadata[SYMBOL][field] = value
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.start(metadata=metadata)
            self.assertIsNone(self.book.snapshot()["risk_session"])

    def test_policy_is_frozen_even_when_callers_original_mapping_changes(self):
        self.book.close()
        p = policy()
        self.book = OfflineOrderJournal.create(Path(self.tmp.name) / "frozen.sqlite", initial_cash="3000", initial_positions={},
            commission_bps="0.5", minimum_commission="5", admission_policy=p)
        p["max_position_cny"] = "3000"
        self.start()
        with self.assertRaisesRegex(ValueError, "position"):
            self.admit(intent(quantity=300))

    def test_parse_rejection_burns_valid_identity_and_is_audited(self):
        sequence = self.book.snapshot()["sequence"]
        with self.assertRaises(ValueError):
            self.admit(intent(price="4.0000001"))
        self.assertGreater(self.book.snapshot()["sequence"], sequence)
        with self.assertRaisesRegex(ValueError, "identity|idempotency"):
            self.admit(intent())

    def test_cross_session_late_fill_consumes_current_conservative_adv_budget(self):
        self.book.close()
        self.book = OfflineOrderJournal.create(Path(self.tmp.name) / "latevolume.sqlite", initial_cash="3000", initial_positions={},
            commission_bps="0.5", minimum_commission="5", admission_policy=policy())
        metadata = {s: instrument(s) for s in (SYMBOL, OTHER)}
        metadata[SYMBOL]["adv_shares"] = "10000"
        self.start(metadata=metadata)
        self.admit()
        self.book.report_status("one", "cancel", "CANCELLED", 0)
        tomorrow = NOW + timedelta(days=1)
        self.start(tomorrow, metadata=metadata)
        self.book.fill("one", "late", 100, "4")
        state = self.book.snapshot()
        self.book.reconcile(snapshot_id="late-check", expected_sequence=state["sequence"], cash=state["cash"], positions=state["positions"],
            orders={"one": {field: state["orders"]["one"][field] for field in
                ("status", "filled_quantity", "filled_notional", "commission")}})
        with self.assertRaisesRegex(ValueError, "participation"):
            self.admit(intent("again", now=tomorrow), now=tomorrow)

    def test_old_day_order_cannot_reopen_across_sessions_after_late_fill(self):
        self.admit(intent(quantity=200))
        self.book.report_status("one", "rejected", "REJECTED", 0)
        tomorrow = NOW + timedelta(days=1)
        self.start(tomorrow)
        self.book.fill("one", "late", 100, "4")
        state = self.book.snapshot()
        with self.assertRaisesRegex(ValueError, "expired DAY"):
            self.book.reconcile(snapshot_id="bad-reopen", expected_sequence=state["sequence"], cash=state["cash"], positions=state["positions"],
                orders={"one": {"status": "PARTIAL", "filled_quantity": 100, "filled_notional": "400", "commission": "5"}})
        self.assertTrue(self.book.snapshot()["paused"])


if __name__ == "__main__":
    unittest.main()
