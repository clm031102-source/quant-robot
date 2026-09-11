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
    ACTIVE, TERMINAL, amount, apply_event, identity, positions, public_snapshot,
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
    def create(cls, path, *, initial_cash, initial_positions, commission_bps, minimum_commission):
        genesis = {"initial_cash": str(amount(initial_cash)), "initial_positions": positions(initial_positions),
            "commission_bps": str(amount(commission_bps)), "minimum_commission": str(amount(minimum_commission))}
        if Decimal(genesis["commission_bps"]) >= 10000:
            raise ValueError("commission_bps must be below 10000")
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

    def _run(self, build, rejected_request=None):
        self._db.execute("BEGIN IMMEDIATE")
        fault = None
        try:
            state = self._read()
            try:
                event = build(state)
            except _Quarantine as exc:
                fault = exc
                event = _event("FAULT", {"reason": str(exc), "rejected_request": rejected_request})
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

        def build(state):
            if order_id in state["orders"] or any(row["idempotency_key"] == idempotency_key for row in state["orders"].values()):
                raise ValueError("duplicate order or idempotency key")
            if state["faults"] or state["kill_switch"]:
                raise ValueError("offline journal paused; reconcile before registering orders")
            event = _event("REGISTER", data)
            apply_event(state, event)
            cash, shares = reservations(state)
            if state["cash"] < cash:
                raise ValueError("insufficient unreserved cash")
            if any(qty > state["positions"].get(key, 0) for key, qty in shares.items()):
                raise ValueError("insufficient unreserved position")
            return event
        return self._run(build, data)

    def fill(self, order_id, fill_id, quantity, price):
        data = {"order_id": identity(order_id), "fill_id": identity(fill_id),
            "quantity": units(quantity, positive=True), "price": str(amount(price, positive=True))}
        receipt = "fill:" + fill_id

        def build(state):
            if self._duplicate(state, receipt, data):
                return None
            order = self._order(state, order_id)
            if order["filled_quantity"] + quantity > order["quantity"]:
                raise _Quarantine("fill exceeds order quantity")
            return _event("FILL", data, receipt)
        return self._run(build, data)

    def request_cancel(self, order_id):
        identity(order_id)

        def build(state):
            order = self._order(state, order_id)
            if order["status"] == "CANCEL_PENDING":
                return None
            if order["status"] not in {"PENDING", "ACCEPTED", "PARTIAL"}:
                raise ValueError("cannot cancel order in current state")
            return _event("CANCEL_REQUEST", {"order_id": order_id})
        return self._run(build, {"order_id": order_id, "kind": "cancel_request"})

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
