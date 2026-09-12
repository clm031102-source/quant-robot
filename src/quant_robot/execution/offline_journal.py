"""Durable OFFLINE FIXTURE order lifecycle, with no transport or live capability.

All commands append events in one SQLite transaction; account/order state is
replayed from those events. Opening an existing journal quarantines open orders.
The caller must reconcile a complete synthetic snapshot before new registrations.
Registration only reserves cash/shares. It is not full pretrade approval and can
never produce an executable request. See the scope document before integration.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3

from .offline_order_state import (
    ACTIVE, TERMINAL, AdmissionRejected, amount, apply_event, identity, positions, public_snapshot,
    reservations, risk_deficit, units,
)


class _Quarantine(ValueError):
    """Persist a fault before exposing the rejected receipt to the caller."""


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _event(kind, data, receipt_key=None):
    return {"kind": kind, "data": data, **({"receipt_key": receipt_key} if receipt_key else {})}


class OfflineOrderJournal:
    @classmethod
    def create(cls, path, *, initial_cash, initial_positions, commission_bps, minimum_commission,
            admission_policy=None, timeout_policy=None, dividend_policy=None, conversion_policy=None):
        genesis = {"initial_cash": str(amount(initial_cash)), "initial_positions": positions(initial_positions),
            "commission_bps": str(amount(commission_bps)), "minimum_commission": str(amount(minimum_commission))}
        if Decimal(genesis["commission_bps"]) >= 10000:
            raise ValueError("commission_bps must be below 10000")
        if admission_policy is not None:
            from .offline_intent_contract import fingerprint, normalize_policy
            policy = normalize_policy(admission_policy)
            if Decimal(genesis["initial_cash"]) > Decimal(policy["capital_limit_cny"]):
                raise ValueError("initial cash exceeds admission capital limit")
            genesis.update(admission_policy=policy, admission_policy_fingerprint=fingerprint(policy))
        if timeout_policy is not None:
            if admission_policy is None:
                raise ValueError("timeouts require a guarded admission policy")
            from .offline_timeouts import normalize_timeout_policy
            timeouts = normalize_timeout_policy(timeout_policy, genesis["admission_policy"])
            genesis.update(timeout_policy=timeouts, timeout_policy_fingerprint=fingerprint(timeouts))
        if dividend_policy is not None:
            if admission_policy is None:
                raise ValueError("dividends require a guarded admission policy")
            from .offline_dividends import normalize_dividend_policy
            dividends = normalize_dividend_policy(dividend_policy, genesis["admission_policy"])
            genesis.update(dividend_policy=dividends, dividend_policy_fingerprint=fingerprint(dividends))
        if conversion_policy is not None:
            if admission_policy is None:
                raise ValueError("conversions require a guarded admission policy")
            from .offline_conversions import normalize_conversion_policy
            conversions = normalize_conversion_policy(conversion_policy, genesis["admission_policy"])
            genesis.update(conversion_policy=conversions, conversion_policy_fingerprint=fingerprint(conversions))
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents accidentally replacing an existing account.
        with path.open("xb"):
            pass
        book = cls.__new__(cls)
        try:
            book._connect(path)
            book._db.executescript("""
                PRAGMA user_version = 1;
                CREATE TABLE events (sequence INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
                    payload TEXT NOT NULL, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL);
                CREATE TRIGGER events_no_update BEFORE UPDATE ON events
                    BEGIN SELECT RAISE(ABORT, 'append-only journal'); END;
                CREATE TRIGGER events_no_delete BEFORE DELETE ON events
                    BEGIN SELECT RAISE(ABORT, 'append-only journal'); END;
            """)
            book._db.execute("BEGIN IMMEDIATE")
            book._append({"sequence": 0, "journal_hash": "0" * 64}, _event("GENESIS", genesis))
            book._db.commit()
            return book
        except BaseException:
            book.close()
            raise

    def __init__(self, path):
        if not Path(path).is_file():
            raise FileNotFoundError(path)
        try:
            self._connect(path)
            if self._db.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise ValueError("unsupported offline journal schema")
            if self._db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("offline journal integrity check failed")
            self._run(self._recovery_event)
        except BaseException:
            self.close()
            raise

    def _connect(self, path):
        self._db = sqlite3.connect(str(path), isolation_level=None, timeout=5)
        self._db.execute("PRAGMA journal_mode = WAL")
        self._db.execute("PRAGMA synchronous = FULL")

    def close(self):
        connection = getattr(self, "_db", None)
        if connection is not None:
            connection.close()
            self._db = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()

    def _read(self):
        state = {"sequence": 0, "journal_hash": "0" * 64}
        for sequence, created, payload, previous, digest in self._db.execute(
                "SELECT sequence, created_at, payload, previous_hash, event_hash FROM events ORDER BY sequence"):
            expected = hashlib.sha256(_json([sequence, created, previous, payload]).encode()).hexdigest()
            if sequence != state["sequence"] + 1 or previous != state["journal_hash"] or digest != expected:
                raise ValueError("offline journal hash or sequence mismatch")
            event = json.loads(payload)
            if (sequence == 1) != (event["kind"] == "GENESIS"):
                raise ValueError("offline journal invalid genesis")
            apply_event(state, event)
            state.update(sequence=sequence, journal_hash=digest)
        if state["sequence"] == 0:
            raise ValueError("offline journal is empty")
        return state

    def _append(self, state, event):
        sequence = state["sequence"] + 1
        created = datetime.now(timezone.utc).isoformat()
        previous, payload = state["journal_hash"], _json(event)
        digest = hashlib.sha256(_json([sequence, created, previous, payload]).encode()).hexdigest()
        self._db.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?)", (sequence, created, payload, previous, digest))
        apply_event(state, event)
        state.update(sequence=sequence, journal_hash=digest)

    def _run(self, build, rejected_request=None, *, rejection_kind="ADMISSION_DENIED"):
        self._db.execute("BEGIN IMMEDIATE")
        fault = None
        try:
            state = self._read()
            try:
                event = build(state)
            except _Quarantine as exc:
                fault = exc
                event = _event("FAULT", {"reason": str(exc), "rejected_request": rejected_request})
            except AdmissionRejected as exc:
                fault = exc
                event = _event(rejection_kind, {"reason": str(exc), "risk_stop": exc.risk_stop,
                    "rejected_request": rejected_request})
                if rejection_kind == "VALUATION_REJECTED":
                    event["data"]["valuation_unavailable"] = getattr(exc, "valuation_unavailable", True)
            if event is not None:
                self._append(state, event)
            self._db.commit()
        except BaseException:
            self._db.rollback()
            raise
        if fault:
            raise ValueError(str(fault))
        return event is not None

    @staticmethod
    def _recovery_event(state):
        keys = [key for key, row in state["orders"].items() if row["status"] in ACTIVE]
        if keys and (any(state["orders"][key]["status"] != "UNKNOWN" for key in keys)
                or "restart_requires_reconciliation" not in state["faults"]):
            return _event("RECOVERY", {"order_ids": keys})
        return None

    def snapshot(self):
        return public_snapshot(self._read())

    @staticmethod
    def _order(state, key):
        if key not in state["orders"]:
            raise _Quarantine("unknown order identity")
        return state["orders"][key]

    @staticmethod
    def _duplicate(state, receipt_key, data):
        if receipt_key in state["receipts"]:
            if data != state["receipts"][receipt_key]:
                raise _Quarantine("conflicting receipt identity: " + receipt_key)
            return True
        return False

    def register(self, *, order_id, idempotency_key, symbol: str, side, quantity, limit_price):
        from .offline_order_state import symbol as validate_symbol
        data = {"order_id": identity(order_id), "idempotency_key": identity(idempotency_key),
            "symbol": validate_symbol(symbol), "side": side, "quantity": units(quantity, positive=True),
            "limit_price": str(amount(limit_price, positive=True))}
        if not isinstance(side, str) or side not in {"BUY", "SELL"}:
            raise ValueError("unsupported side")

        return self._run(lambda state: self._registration_event(state, data), data)

    @staticmethod
    def _registration_event(state, data, *, guarded=False):
        if state["admission_policy"] is not None and not guarded:
            raise ValueError("guarded journal requires full intent admission")
        if data["order_id"] in state["orders"] or any(row["idempotency_key"] == data["idempotency_key"] for row in state["orders"].values()):
            raise ValueError("duplicate order or idempotency key")
        if state["faults"] or state["kill_switch"]:
            raise ValueError("offline journal paused; reconcile before registering orders")
        event = _event("REGISTER", data)
        candidate = {**state, "orders": dict(state["orders"]),
            "attempted_intent_ids": set(state["attempted_intent_ids"]),
            "attempted_idempotency_keys": set(state["attempted_idempotency_keys"])}
        apply_event(candidate, event)
        cash, shares = reservations(candidate)
        if state["cash"] < cash:
            raise ValueError("insufficient unreserved cash")
        if any(qty > state["positions"].get(key, 0) for key, qty in shares.items()):
            raise ValueError("insufficient unreserved position")
        if risk_deficit(candidate):
            raise ValueError("insufficient unreserved sellable position")
        return event

    def begin_session(self, context, *, clock=None):
        from .offline_admission import begin_session_event
        from .offline_intent_contract import normalize_packet
        packet = normalize_packet(context, opening=True)
        clock = clock or (lambda: datetime.now(timezone.utc))
        return self._run(lambda state: begin_session_event(state, packet, clock()), {"context": packet})

    def admit(self, intent, context, *, clock=None):
        from .offline_admission import admission_event
        from .offline_intent_contract import normalize_intent, normalize_packet, rejection_evidence
        try:
            order, packet = normalize_intent(intent), normalize_packet(context)
        except ValueError as exc:
            message = str(exc)
            def reject(_state):
                raise AdmissionRejected(message)
            return self._run(reject, rejection_evidence(intent, exc))
        clock = clock or (lambda: datetime.now(timezone.utc))

        def build(state):
            event = admission_event(state, order, packet, clock())
            try:
                return self._registration_event(state, event["data"], guarded=True)
            except ValueError as exc:
                raise AdmissionRejected(str(exc)) from exc
        return self._run(build, {"intent": order, "context": packet})

    def prepare_dispatch(self, order_id, attempt_id, context, *, clock=None):
        """Record a single offline send-decision check; never emit a live request."""
        from .offline_dispatch import dispatch_event
        from .offline_intent_contract import normalize_packet
        request = {"order_id": identity(order_id), "attempt_id": identity(attempt_id)}
        try:
            packet = normalize_packet(context)
        except ValueError as exc:
            message = str(exc)
            def reject(_state):
                raise AdmissionRejected(message)
            return self._run(reject, request, rejection_kind="DISPATCH_DENIED")
        clock = clock or (lambda: datetime.now(timezone.utc))
        return self._run(lambda state: dispatch_event(state, order_id, attempt_id, packet, clock()),
            {**request, "context": packet}, rejection_kind="DISPATCH_DENIED")

    def fill(self, order_id, fill_id, quantity, price):
        data = {"order_id": identity(order_id), "fill_id": identity(fill_id),
            "quantity": units(quantity, positive=True), "price": str(amount(price, positive=True))}
        receipt = "fill:" + fill_id

        def build(state):
            if self._duplicate(state, receipt, data):
                return None
            order = self._order(state, order_id)
            deferred = sum(row["quantity"] for row in state["conversions"]["unapplied_fills"].values() if row["order_id"] == order_id)
            if order["filled_quantity"] + deferred + quantity > order["quantity"]:
                raise _Quarantine("fill exceeds order quantity")
            from .offline_conversions import has_converted_order_basis
            if has_converted_order_basis(state, order):
                return _event("CONVERSION_UNAPPLIED_FILL", data, receipt)
            return _event("FILL", data, receipt)
        return self._run(build, data)

    def request_cancel(self, order_id, *, clock=None):
        identity(order_id)
        clock = clock or (lambda: datetime.now(timezone.utc))

        def build(state):
            order = self._order(state, order_id)
            if order["status"] == "CANCEL_PENDING":
                return None
            if order["status"] not in {"PENDING", "ACCEPTED", "PARTIAL"}:
                raise ValueError("cannot cancel order in current state")
            from .offline_timeouts import cancel_timing
            return _event("CANCEL_REQUEST", {"order_id": order_id, **cancel_timing(state, order, clock())})
        return self._run(build, {"order_id": order_id, "kind": "cancel_request"})

    def monitor_timeouts(self, *, clock=None):
        """Quarantine overdue offline orders without inventing execution receipts."""
        from .offline_timeouts import timeout_event
        clock = clock or (lambda: datetime.now(timezone.utc))
        return self._run(lambda state: timeout_event(state, clock()))

    def record_valuation(self, context, *, clock=None):
        """Record supplied synthetic marks independently of order submissions."""
        from .offline_intent_contract import instant, normalize_packet
        from .offline_valuation import ValuationRejected, valuation_event
        message = None
        try:
            packet = normalize_packet(context)
            request = {"context": packet}
        except ValueError as exc:
            message = str(exc)
            request = {"parse_failure": message, "provided_context_metadata": {
                key: context[key][:2000] for key in ("snapshot_id", "source_ref", "as_of")
                if isinstance(context, dict) and isinstance(context.get(key), str)}}
        clock = clock or (lambda: datetime.now(timezone.utc))

        def build(state):
            now = instant(clock())
            request["decision_at"] = now.isoformat()
            if message is not None:
                raise ValuationRejected(message, unavailable=True)
            return valuation_event(state, packet, now)
        return self._run(build, request, rejection_kind="VALUATION_REJECTED")

    def record_dividend_entitlements(self, *, clock=None):
        from .offline_dividends import entitlement_event
        return self._run_corporate(entitlement_event, {"operation": "entitlement"}, clock, "DIVIDEND_REJECTED")

    def accrue_dividends(self, *, clock=None):
        from .offline_dividends import accrual_event
        return self._run_corporate(accrual_event, {"operation": "accrual"}, clock, "DIVIDEND_REJECTED")

    def record_dividend_cash_credit(self, event_id, receipt_id, cash_amount, *, clock=None):
        from .offline_dividends import credit_event
        event_id, receipt_id, cash_amount = identity(event_id), identity(receipt_id), amount(cash_amount)
        return self._run_corporate(lambda state, now: credit_event(state, event_id, receipt_id, cash_amount, now),
            {"operation": "cash_credit", "event_id": event_id, "receipt_id": receipt_id, "cash_amount": str(cash_amount)}, clock, "DIVIDEND_REJECTED")

    def record_conversion_entitlements(self, *, clock=None):
        from .offline_conversions import entitlement_event
        return self._run_corporate(entitlement_event, {"operation": "conversion_entitlement"}, clock, "CONVERSION_REJECTED")

    def apply_share_conversions(self, *, clock=None):
        from .offline_conversions import conversion_event
        return self._run_corporate(conversion_event, {"operation": "share_conversion"}, clock, "CONVERSION_REJECTED")

    def _run_corporate(self, builder, request, clock, rejection_kind):
        from .offline_intent_contract import instant
        clock = clock or (lambda: datetime.now(timezone.utc))

        def build(state):
            now = instant(clock())
            request["decision_at"] = now.isoformat()
            return builder(state, now)
        return self._run(build, request, rejection_kind=rejection_kind)

    def report_status(self, order_id, report_id, status, cumulative_quantity):
        if not isinstance(status, str) or status not in {"ACCEPTED", "CANCELLED", "REJECTED", "UNKNOWN"}:
            raise ValueError("unsupported status report")
        data = {"order_id": identity(order_id), "report_id": identity(report_id), "status": status,
            "cumulative_quantity": units(cumulative_quantity)}
        receipt = "status:" + report_id

        def build(state):
            if self._duplicate(state, receipt, data):
                return None
            order = self._order(state, order_id)
            if cumulative_quantity > order["filled_quantity"]:
                raise _Quarantine("status report references missing fill evidence")
            if status in {"CANCELLED", "REJECTED"} and cumulative_quantity != order["filled_quantity"]:
                raise _Quarantine("terminal status disagrees with recorded fills")
            if status == "REJECTED" and order["filled_quantity"]:
                raise _Quarantine("rejected status conflicts with filled order")
            if (order["status"] in {"CANCELLED", "REJECTED"} and status in TERMINAL
                    and status != order["status"]):
                raise _Quarantine("conflicting terminal order status")
            return _event("STATUS", data, receipt)
        return self._run(build, data)

    def set_kill_switch(self, enabled, *, reason):
        if type(enabled) is not bool:
            raise ValueError("kill switch must be boolean")
        identity(reason)

        def build(state):
            if not enabled and (state["faults"] or any(o["status"] == "UNKNOWN" for o in state["orders"].values())):
                raise ValueError("reconciliation required before releasing kill switch")
            return _event("KILL_SWITCH", {"enabled": enabled, "reason": reason})
        return self._run(build)

    def reconcile(self, *, snapshot_id, expected_sequence, cash, positions: dict, orders: dict):
        from .offline_order_state import positions as validate_positions
        data = {"snapshot_id": identity(snapshot_id), "expected_sequence": units(expected_sequence),
            "cash": str(amount(cash, bounded=False)), "positions": validate_positions(positions, bounded=False), "orders": {}}
        if not isinstance(orders, dict):
            raise ValueError("orders must be a complete mapping")
        for key, row in orders.items():
            if not isinstance(row, dict) or set(row) != {"status", "filled_quantity", "filled_notional", "commission"}:
                raise ValueError("invalid reconciliation order evidence")
            data["orders"][identity(key)] = {"status": row["status"], "filled_quantity": units(row["filled_quantity"]),
                "filled_notional": str(amount(row["filled_notional"], bounded=False)),
                "commission": str(amount(row["commission"], bounded=False))}
        receipt = "snapshot:" + snapshot_id

        def build(state):
            if self._duplicate(state, receipt, data):
                return None
            if expected_sequence != state["sequence"]:
                raise _Quarantine("stale reconciliation snapshot")
            self._check_reconciliation(state, data)
            return _event("RECONCILE", data, receipt)
        return self._run(build, data)

    @staticmethod
    def _check_reconciliation(state, data):
        if (Decimal(data["cash"]) != state["cash"] or data["positions"] != {k: v for k, v in state["positions"].items() if v}
                or set(data["orders"]) != set(state["orders"])):
            raise _Quarantine("reconciliation cash, positions or order coverage mismatch")
        for key, row in data["orders"].items():
            order = state["orders"][key]
            status, filled = row["status"], row["filled_quantity"]
            if (status in ACTIVE and order.get("timeout", {}).get("reason") in
                    {"day_order_expired", "cancel_confirmation_timeout", "unprepared_intent_expired"}):
                raise _Quarantine("timed-out order requires a terminal reconciliation result")
            if (state["risk_session"] is not None and status in ACTIVE
                    and order.get("admission", {}).get("session_date", "") < state["risk_session"]["session_date"]):
                raise _Quarantine("expired DAY order cannot reopen across sessions")
            legal = ((status in {"ACCEPTED", "REJECTED"} and filled == 0)
                or (status == "PARTIAL" and 0 < filled < order["quantity"])
                or (status in {"CANCEL_PENDING", "CANCELLED"} and filled < order["quantity"])
                or (status == "FILLED" and filled == order["quantity"]))
            if (not legal or filled != order["filled_quantity"]
                    or Decimal(row["filled_notional"]) != order["filled_notional"]
                    or Decimal(row["commission"]) != order["commission"]
                    or (order["status"] in TERMINAL and status != order["status"])):
                raise _Quarantine("reconciliation order status or fill totals mismatch")
        # Apply the proposed statuses to a disposable projection before clearing faults.
        for key, row in data["orders"].items():
            state["orders"][key]["status"] = row["status"]
        if risk_deficit(state):
            raise _Quarantine("reconciliation leaves an account or reservation deficit")
