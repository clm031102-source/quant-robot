"""Pure projection for the synthetic, single-currency order journal.

This is not a broker adapter or a security-master/pretrade eligibility check.
Money uses Decimal; the explicitly supplied synthetic commission is rounded to
cents on cumulative order notional. No fees are charged for an unfilled order.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from functools import wraps
import re

ACTIVE = {"PENDING", "ACCEPTED", "PARTIAL", "CANCEL_PENDING", "UNKNOWN"}
TERMINAL = {"FILLED", "CANCELLED", "REJECTED"}
STATUSES = ACTIVE | TERMINAL
ZERO = Decimal("0")


class AdmissionRejected(ValueError):
    def __init__(self, message, *, risk_stop=False):
        super().__init__(message)
        self.risk_stop = risk_stop


def money_context(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with localcontext() as context:
            context.prec = 50
            return function(*args, **kwargs)
    return wrapped


@money_context
def amount(value, *, positive=False, bounded=True) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("invalid finite amount") from None
    if (isinstance(value, bool) or not number.is_finite() or number < 0
            or (bounded and number > Decimal("1000000000000")) or number.as_tuple().exponent < -6
            or len(number.as_tuple().digits) > 50
            or (positive and number == 0)):
        raise ValueError("invalid finite amount")
    return number.normalize()


def units(value, *, positive=False, bounded=True) -> int:
    if type(value) is not int or value < int(positive) or (bounded and value > 1_000_000_000):
        raise ValueError("quantity must be a bounded integer")
    return value


def identity(value) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > 200:
        raise ValueError("invalid identity")
    return value


def symbol(value) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{6}\.(SH|SZ)", value) is None:
        raise ValueError("invalid CN instrument symbol")
    return value


def positions(value, *, bounded=True) -> dict[str, int]:
    if not isinstance(value, dict):
        raise ValueError("positions must be a mapping")
    validated = {symbol(key): units(qty, bounded=bounded) for key, qty in value.items()}
    return {key: qty for key, qty in validated.items() if qty}


@money_context
def commission(state, notional: Decimal) -> Decimal:
    if notional == 0:
        return ZERO
    return max(state["minimum_commission"], notional * state["commission_bps"] / 10000).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP)


@money_context
def reservations(state):
    cash = ZERO
    shares: dict[str, int] = {}
    for order in state["orders"].values():
        if order["status"] not in ACTIVE:
            continue
        remaining = order["quantity"] - order["filled_quantity"]
        value = remaining * order["limit_price"]
        extra_fee = max(ZERO, commission(state, order["filled_notional"] + value) - order["commission"])
        if order["side"] == "BUY":
            cash += value + extra_fee
        else:
            shares[order["symbol"]] = shares.get(order["symbol"], 0) + remaining
            # A small first partial fill must also be able to pay the minimum.
            # The fixture journal's smallest share unit is 1. Bound the next
            # rounded fee using the cumulative unrounded fee minus what has
            # already been paid; do not reserve the same rounding cost twice.
            first_value = order["limit_price"] if remaining else ZERO
            first_fee = commission(state, order["filled_notional"] + first_value) - order["commission"]
            rate = state["commission_bps"] / 10000
            rounding_buffer = (order["filled_notional"] * rate + Decimal("0.005")
                - order["commission"] - first_value * (1 - rate)
                if remaining and state["commission_bps"] else ZERO)
            cash += max(ZERO, extra_fee - value, first_fee - first_value, rounding_buffer)
    return cash, shares


def risk_deficit(state) -> bool:
    cash, shares = reservations(state)
    return (state["cash"] < cash or any(qty < 0 for qty in state["positions"].values())
        or any(qty > state["positions"].get(key, 0) for key, qty in shares.items())
        or (state.get("risk_session") is not None and (any(qty < 0 for qty in state["sellable_positions"].values())
            or any(qty > state["sellable_positions"].get(key, 0) for key, qty in shares.items()))))


@money_context
def apply_event(state, event):
    kind, data = event["kind"], event["data"]
    if kind == "GENESIS":
        state.update(cash=Decimal(data["initial_cash"]), positions=dict(data["initial_positions"]),
            commission_bps=Decimal(data["commission_bps"]), minimum_commission=Decimal(data["minimum_commission"]),
            orders={}, receipts={}, faults=set(), kill_switch=False,
            admission_policy=data.get("admission_policy"), admission_policy_fingerprint=data.get("admission_policy_fingerprint"),
            risk_session=None, sellable_positions={}, attempted_intent_ids=set(), attempted_idempotency_keys=set(),
            attempted_dispatch_ids=set())
    elif kind == "REGISTER":
        state["orders"][data["order_id"]] = {**data, "limit_price": Decimal(data["limit_price"]),
            "status": "PENDING", "filled_quantity": 0, "filled_notional": ZERO, "commission": ZERO}
        if "admission" in data:
            state["attempted_intent_ids"].add(data["order_id"])
            state["attempted_idempotency_keys"].add(data["idempotency_key"])
    elif kind == "RISK_SESSION":
        state["risk_session"] = dict(data)
        state["sellable_positions"] = dict(data["sellable_positions"])
    elif kind in {"ADMISSION_DENIED", "DISPATCH_DENIED"}:
        request = data["rejected_request"] or {}
        if kind == "DISPATCH_DENIED" and "attempt_id" in request:
            state["attempted_dispatch_ids"].add(request["attempt_id"])
        if "intent" in request:
            if "client_intent_id" in request["intent"]:
                state["attempted_intent_ids"].add(request["intent"]["client_intent_id"])
            if "idempotency_key" in request["intent"]:
                state["attempted_idempotency_keys"].add(request["intent"]["idempotency_key"])
        if data["risk_stop"] and state["risk_session"] is not None:
            state["risk_session"]["risk_stop"] = True
    elif kind == "DISPATCH_PREPARED":
        state["orders"][data["order_id"]]["dispatch"] = dict(data)
        state["attempted_dispatch_ids"].add(data["attempt_id"])
    elif kind == "FILL":
        _apply_fill(state, data)
    elif kind == "STATUS":
        order = state["orders"][data["order_id"]]
        status = data["status"]
        if status == "UNKNOWN":
            order["status"] = status
            state["faults"].add("unknown_order_state")
        elif status == "ACCEPTED":
            if order["status"] == "PENDING":
                order["status"] = status
        elif order["status"] != "FILLED":
            order["status"] = status
    elif kind == "CANCEL_REQUEST":
        state["orders"][data["order_id"]]["status"] = "CANCEL_PENDING"
    elif kind == "RECOVERY":
        for key in data["order_ids"]:
            state["orders"][key]["status"] = "UNKNOWN"
        state["faults"].add("restart_requires_reconciliation")
    elif kind == "FAULT":
        state["faults"].add(data["reason"])
    elif kind == "RECONCILE":
        for key, order in data["orders"].items():
            state["orders"][key]["status"] = order["status"]
        state["faults"].clear()
    elif kind == "KILL_SWITCH":
        state["kill_switch"] = data["enabled"]
    else:
        raise ValueError("unknown journal event")
    if "receipt_key" in event:
        state["receipts"][event["receipt_key"]] = data


def _apply_fill(state, data):
    order = state["orders"][data["order_id"]]
    old_status = order["status"]
    qty, price = data["quantity"], Decimal(data["price"])
    value = qty * price
    fee = commission(state, order["filled_notional"] + value)
    extra_fee = fee - order["commission"]
    direction = 1 if order["side"] == "BUY" else -1
    state["cash"] -= direction * value + extra_fee
    key = order["symbol"]
    state["positions"][key] = state["positions"].get(key, 0) + direction * qty
    if state["risk_session"] is not None:
        metadata = state["risk_session"]["instruments"][key]
        if direction < 0 or metadata["settlement"] == "T0":
            state["sellable_positions"][key] = state["sellable_positions"].get(key, 0) + direction * qty
        if order["admission"]["session_date"] != state["risk_session"]["session_date"]:
            # Without a trade-date transport contract, conservatively consume
            # the receipt session's budget. Reconciliation cannot erase this.
            carryover = state["risk_session"]["carryover_fill_shares"].setdefault(key, {})
            carryover[order["side"]] = carryover.get(order["side"], 0) + qty
    order["filled_quantity"] += qty
    order["filled_notional"] += value
    order["commission"] = fee
    if order["filled_quantity"] == order["quantity"]:
        order["status"] = "FILLED"
    elif old_status == "REJECTED":
        order["status"] = "UNKNOWN"
    elif old_status not in {"CANCEL_PENDING", "UNKNOWN", "CANCELLED", "REJECTED"}:
        order["status"] = "PARTIAL"
    if old_status in TERMINAL:
        state["faults"].add("fill_after_terminal_status")
    if direction * (price - order["limit_price"]) > 0:
        state["faults"].add("fill_outside_limit")
    if risk_deficit(state):
        state["faults"].add("account_or_reservation_deficit")


@money_context
def public_snapshot(state):
    cash, shares = reservations(state)
    sellable = state["sellable_positions"] if state["risk_session"] is not None else state["positions"]
    return {"schema_version": 1, "mode": "offline_fixture_only", "executable": False,
        "sequence": state["sequence"], "journal_hash": state["journal_hash"],
        "cash": str(state["cash"]), "reserved_cash": str(cash),
        "available_cash": str(max(ZERO, state["cash"] - cash)),
        "positions": {key: qty for key, qty in state["positions"].items() if qty},
        "reserved_positions": shares,
        "available_positions": {key: max(0, min(qty, sellable.get(key, 0)) - shares.get(key, 0)) for key, qty in state["positions"].items() if qty},
        "sellable_positions": {key: qty for key, qty in sellable.items() if qty},
        "admission_policy_fingerprint": state["admission_policy_fingerprint"],
        "risk_session": state["risk_session"],
        "paused": bool(state["kill_switch"] or state["faults"] or (state["risk_session"] or {}).get("risk_stop")), "kill_switch": state["kill_switch"],
        "faults": sorted(state["faults"]),
        "orders": {key: {name: str(value) if isinstance(value, Decimal) else value for name, value in row.items()}
            for key, row in state["orders"].items()}}
