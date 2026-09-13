"""Pure projection for the synthetic, single-currency order journal.

This is not a broker adapter or a security-master/pretrade eligibility check.
Money uses Decimal; the explicitly supplied synthetic commission is rounded to
cents on cumulative order notional. No fees are charged for an unfilled order.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from functools import wraps
import hashlib
import json
import re

from .offline_history import mutable_order

ACTIVE = {"PENDING", "ACCEPTED", "PARTIAL", "CANCEL_PENDING", "UNKNOWN"}
TERMINAL = {"FILLED", "CANCELLED", "REJECTED"}
STATUSES = ACTIVE | TERMINAL
ZERO = Decimal("0")
VALUATION_UNAVAILABLE = "portfolio_valuation_unavailable"
DIVIDEND_ENTITLEMENT_UNCERTAIN = "dividend_entitlement_requires_review"
CONVERSION_UNCERTAIN = "share_conversion_requires_review"


class AdmissionRejected(ValueError):
    def __init__(self, message, *, risk_stop=False, drawdown_guard=None, risk_stop_causes=None):
        super().__init__(message)
        self.risk_stop = risk_stop
        self.drawdown_guard = drawdown_guard
        self.risk_stop_causes = risk_stop_causes


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


@money_context
def risk_deficit(state) -> bool:
    cash, shares = reservations(state)
    return (state["cash"] < cash + dividend_payable(state) or any(qty < 0 for qty in state["positions"].values())
        or any(qty > state["positions"].get(key, 0) for key, qty in shares.items())
        or (state.get("risk_session") is not None and (any(qty < 0 for qty in state["sellable_positions"].values())
            or any(qty > state["sellable_positions"].get(key, 0) for key, qty in shares.items()))))


@money_context
def dividend_receivable(state):
    return sum((Decimal(value) for value in state["dividends"]["receivables"].values()), ZERO)


@money_context
def dividend_payable(state):
    return sum((Decimal(value) for value in state["dividends"].get("payables", {}).values()), ZERO)


def effective_dividend_entitlement(state, action_id):
    return state["dividends"]["revisions"].get(action_id, state["dividends"]["entitlements"][action_id])


def _refresh_dividend_balance(state, action_id):
    dividends = state["dividends"]
    if action_id not in dividends["accrued"]:
        return
    remaining = Decimal(effective_dividend_entitlement(state, action_id)["net_amount"]) - Decimal(dividends["settled_net"].get(action_id, "0"))
    dividends["receivables"].pop(action_id, None); dividends["payables"].pop(action_id, None)
    dividends["paid"].discard(action_id)
    if remaining > 0:
        dividends["receivables"][action_id] = str(remaining)
    elif remaining < 0:
        dividends["payables"][action_id] = str(-remaining)
    elif action_id in dividends["settled_net"]:
        dividends["paid"].add(action_id)


def _apply_dividend_revision(state, data):
    dividends, action_id = state["dividends"], data["event_id"]
    dividends["revisions"][action_id] = {key: data[key] for key in ("revision_id", "symbol", "quantity", "net_amount",
        "net_adjustment", "posted_adjustment", "facts_fingerprint", "decision_at")}
    dividends["reviewed_receipts"][action_id] = dict(data["reviewed_receipts"])
    dividends["posted_adjustment_total"] = str(Decimal(dividends["posted_adjustment_total"]) + Decimal(data["posted_adjustment"]))
    _refresh_dividend_balance(state, action_id)
    dividends["last_transition_at"] = data["decision_at"]
    if data["clears_dividend_review_fault"]:
        state["faults"].discard(DIVIDEND_ENTITLEMENT_UNCERTAIN)
    if risk_deficit(state):
        state["faults"].add("account_or_reservation_deficit")


def _record_price_basis(state, code, event_ref):
    history = state["price_basis_events"].setdefault(code, [])
    if event_ref not in history:
        history.append(event_ref)
    state["price_basis"][code] = (history[0] if len(history) == 1 else "corporate_actions:" +
        hashlib.sha256(json.dumps(sorted(history), separators=(",", ":")).encode()).hexdigest())


def _mark_entitlement_uncertainty(state, order):
    for policy_key, state_key, fault in (("dividend_policy", "dividends", DIVIDEND_ENTITLEMENT_UNCERTAIN),
            ("conversion_policy", "conversions", CONVERSION_UNCERTAIN)):
        for event in (state.get(policy_key) or {}).get("events", []):
            if (event["symbol"] == order["symbol"] and event["event_id"] in state[state_key]["entitlements"]
                    and order["admission"]["session_date"] <= event["record_date"]):
                state["faults"].add(fault)


@money_context
def apply_event(state, event):
    kind, data = event["kind"], event["data"]
    if kind == "GENESIS":
        state.update(cash=Decimal(data["initial_cash"]), positions=dict(data["initial_positions"]),
            commission_bps=Decimal(data["commission_bps"]), minimum_commission=Decimal(data["minimum_commission"]),
            orders={}, receipts={}, faults=set(), kill_switch=False,
            admission_policy=data.get("admission_policy"), admission_policy_fingerprint=data.get("admission_policy_fingerprint"),
            timeout_policy=data.get("timeout_policy"), timeout_policy_fingerprint=data.get("timeout_policy_fingerprint"),
            last_timeout_at=None,
            portfolio_valuation={"last_valid": None, "last_rejection": None, "unavailable": False},
            dividend_policy=data.get("dividend_policy"), dividend_policy_fingerprint=data.get("dividend_policy_fingerprint"),
            dividends={"entitlements": {}, "receivables": {}, "accrued": set(), "paid": set(), "price_basis": {},
                "last_transition_at": None, "last_rejection": None, "revisions": {}, "settled_net": {},
                "payables": {}, "reviewed_receipts": {}, "posted_adjustment_total": "0"},
            conversion_policy=data.get("conversion_policy"), conversion_policy_fingerprint=data.get("conversion_policy_fingerprint"),
            conversions={"entitlements": {}, "applied": {}, "locks": {}, "released": set(), "unapplied_fills": {},
                "last_transition_at": None, "last_rejection": None, "revisions": {}, "accounted_fills": {}, "participation": {}},
            price_basis={}, price_basis_events={}, corporate_last_transition_at=None,
            risk_session=None, drawdown_guard=None, sellable_positions={}, attempted_intent_ids=set(), attempted_idempotency_keys=set(),
            attempted_dispatch_ids=set())
    elif kind == "REGISTER":
        state["orders"][data["order_id"]] = {**data, "limit_price": Decimal(data["limit_price"]),
            "status": "PENDING", "filled_quantity": 0, "filled_notional": ZERO, "commission": ZERO}
        if "admission" in data:
            state["attempted_intent_ids"].add(data["order_id"])
            state["attempted_idempotency_keys"].add(data["idempotency_key"])
    elif kind == "RISK_SESSION":
        state["risk_session"] = dict(data)
        from .offline_exposure_stop import latch_stop
        if data["risk_stop"]:
            latch_stop(state, data.get("risk_stop_causes"))
        state["sellable_positions"] = dict(data["sellable_positions"])
        state["portfolio_valuation"] = {"last_valid": None, "last_rejection": None, "unavailable": False}
        state["faults"].discard(VALUATION_UNAVAILABLE)
        for code in data.get("released_conversion_locks", []):
            lock = state["conversions"]["locks"].pop(code)
            state["conversions"]["released"].add(lock["event_id"])
        for key in data.get("consumed_conversion_participation", []):
            state["conversions"]["participation"][key]["consumed_session"] = data["session_date"]
    elif kind == "PORTFOLIO_VALUATION":
        state["portfolio_valuation"].update(last_valid={**data, "event_sequence": state["sequence"] + 1}, unavailable=False)
        state["risk_session"]["valuation_peak_equity"] = data["book_equity_peak"]
        if data["risk_stop_required"]:
            from .offline_exposure_stop import latch_stop
            latch_stop(state, data.get("breaches"))
        state["faults"].discard(VALUATION_UNAVAILABLE)
    elif kind == "VALUATION_REJECTED":
        state["portfolio_valuation"]["last_rejection"] = dict(data)
        if data["valuation_unavailable"] and state["risk_session"] is not None:
            state["portfolio_valuation"]["unavailable"] = True
            state["faults"].add(VALUATION_UNAVAILABLE)
    elif kind == "DIVIDEND_ENTITLEMENTS":
        state["dividends"]["entitlements"].update(data["entitlements"])
        state["dividends"]["last_transition_at"] = data["decision_at"]
    elif kind == "DIVIDEND_ACCRUAL":
        for key in data["event_ids"]:
            entitlement = effective_dividend_entitlement(state, key)
            state["dividends"]["receivables"][key] = entitlement["net_amount"]
            state["dividends"]["accrued"].add(key)
            state["dividends"]["price_basis"][entitlement["symbol"]] = "cash_dividend:" + key
            _record_price_basis(state, entitlement["symbol"], "cash_dividend:" + key)
        state["dividends"]["last_transition_at"] = data["decision_at"]
    elif kind in {"DIVIDEND_CASH_CREDIT", "DIVIDEND_CASH_INSTALLMENT", "DIVIDEND_CASH_REFUND"}:
        state["cash"] += Decimal(data["cash_amount"])
        settled = state["dividends"]["settled_net"]
        settled[data["event_id"]] = str(Decimal(settled.get(data["event_id"], "0")) + Decimal(data["cash_amount"]))
        _refresh_dividend_balance(state, data["event_id"])
        state["dividends"]["last_transition_at"] = data["decision_at"]
        if kind == "DIVIDEND_CASH_REFUND" and risk_deficit(state):
            state["faults"].add("account_or_reservation_deficit")
    elif kind == "DIVIDEND_ENTITLEMENT_REVISION":
        _apply_dividend_revision(state, data)
    elif kind == "DIVIDEND_REJECTED":
        state["dividends"]["last_rejection"] = dict(data)
    elif kind == "CONVERSION_ENTITLEMENTS":
        state["conversions"]["entitlements"].update(data["entitlements"])
        state["conversions"]["last_transition_at"] = data["decision_at"]
    elif kind == "SHARE_CONVERSIONS":
        for key, row in data["conversions"].items():
            code = row["symbol"]
            state["positions"][code] = row["new_quantity"]
            state["sellable_positions"][code] = 0
            state["conversions"]["applied"][key] = dict(row)
            state["conversions"]["locks"][code] = {"event_id": key, "quantity": row["new_quantity"], "tradable_date": row["tradable_date"]}
            _record_price_basis(state, code, "share_conversion:" + key)
        state["conversions"]["last_transition_at"] = data["decision_at"]
    elif kind == "CONVERSION_UNAPPLIED_FILL":
        state["conversions"]["unapplied_fills"][data["fill_id"]] = dict(data)
        state["faults"].add(CONVERSION_UNCERTAIN)
        _mark_entitlement_uncertainty(state, state["orders"][data["order_id"]])
    elif kind == "CONVERSION_FILL_RESOLUTION":
        from .offline_conversion_revisions import apply_resolution
        apply_resolution(state, data)
    elif kind == "CONVERSION_REJECTED":
        state["conversions"]["last_rejection"] = dict(data)
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
            from .offline_exposure_stop import latch_stop
            latch_stop(state, data.get("risk_stop_causes"))
    elif kind == "DISPATCH_PREPARED":
        mutable_order(state, data["order_id"])["dispatch"] = dict(data)
        state["attempted_dispatch_ids"].add(data["attempt_id"])
    elif kind == "FILL":
        _apply_fill(state, data)
    elif kind == "STATUS":
        order = mutable_order(state, data["order_id"])
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
        mutable_order(state, data["order_id"])["status"] = "CANCEL_PENDING"
        if "confirmation_deadline" in data:
            state["orders"][data["order_id"]]["cancel_request"] = dict(data)
    elif kind == "ORDER_TIMEOUT":
        for row in data["orders"]:
            order = mutable_order(state, row["order_id"])
            order["status"], order["timeout"] = "UNKNOWN", dict(row)
        state["last_timeout_at"] = data["observed_at"]
        state["faults"].add("order_timeout_requires_reconciliation")
    elif kind == "RECOVERY":
        for key in data["order_ids"]:
            mutable_order(state, key)["status"] = "UNKNOWN"
        state["faults"].add("restart_requires_reconciliation")
    elif kind == "FAULT":
        state["faults"].add(data["reason"])
    elif kind == "RECONCILE":
        for key, order in data["orders"].items():
            mutable_order(state, key)["status"] = order["status"]
        state["faults"].intersection_update({VALUATION_UNAVAILABLE, DIVIDEND_ENTITLEMENT_UNCERTAIN, CONVERSION_UNCERTAIN})
    elif kind == "KILL_SWITCH":
        state["kill_switch"] = data["enabled"]
    else:
        raise ValueError("unknown journal event")
    from .offline_drawdown import apply_drawdown_evidence
    apply_drawdown_evidence(state, event)
    if "receipt_key" in event:
        state["receipts"][event["receipt_key"]] = data
    if kind in {"DIVIDEND_ENTITLEMENTS", "DIVIDEND_ACCRUAL", "DIVIDEND_CASH_CREDIT", "DIVIDEND_CASH_INSTALLMENT",
            "DIVIDEND_CASH_REFUND", "DIVIDEND_ENTITLEMENT_REVISION", "CONVERSION_ENTITLEMENTS", "SHARE_CONVERSIONS", "CONVERSION_FILL_RESOLUTION"}:
        state["corporate_last_transition_at"] = data["decision_at"]


def _apply_fill(state, data):
    order = mutable_order(state, data["order_id"])
    old_status = order["status"]
    qty, price = data["quantity"], Decimal(data["price"])
    value = qty * price
    fee = commission(state, order["filled_notional"] + value)
    extra_fee = fee - order["commission"]
    direction = 1 if order["side"] == "BUY" else -1
    state["cash"] -= direction * value + extra_fee
    key = order["symbol"]
    _mark_entitlement_uncertainty(state, order)
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
        "available_cash": str(max(ZERO, state["cash"] - cash - dividend_payable(state))),
        "dividend_refund_cash_reserve": str(dividend_payable(state)),
        "positions": {key: qty for key, qty in state["positions"].items() if qty},
        "reserved_positions": shares,
        "available_positions": {key: max(0, min(qty, sellable.get(key, 0)) - shares.get(key, 0)) for key, qty in state["positions"].items() if qty},
        "sellable_positions": {key: qty for key, qty in sellable.items() if qty},
        "admission_policy_fingerprint": state["admission_policy_fingerprint"],
        "timeout_policy_fingerprint": state["timeout_policy_fingerprint"],
        "dividend_policy_fingerprint": state["dividend_policy_fingerprint"],
        "conversion_policy_fingerprint": state["conversion_policy_fingerprint"],
        "price_basis": dict(state["price_basis"]),
        "conversions": {**state["conversions"], "released": sorted(state["conversions"]["released"]),
            "unresolved_fills": {key: row for key, row in state["conversions"]["unapplied_fills"].items()
                if key not in state["conversions"]["accounted_fills"]}},
        "dividends": {**state["dividends"], "accrued": sorted(state["dividends"]["accrued"]),
            "paid": sorted(state["dividends"]["paid"]), "receivable_total": str(dividend_receivable(state)), "payable_total": str(dividend_payable(state))},
        "risk_session": state["risk_session"],
        "drawdown_guard": state.get('drawdown_guard'),
        "drawdown_guard_configured": (state.get('admission_policy') or {}).get('schema_version') == 2,
        "portfolio_valuation": {**state["portfolio_valuation"], "matches_current_journal":
            (state["portfolio_valuation"]["last_valid"] or {}).get("event_sequence") == state["sequence"]},
        "paused": bool(state["kill_switch"] or state["faults"] or (state["risk_session"] or {}).get("risk_stop")), "kill_switch": state["kill_switch"],
        "faults": sorted(state["faults"]),
        "orders": {key: {name: str(value) if isinstance(value, Decimal) else value for name, value in row.items()}
            for key, row in state["orders"].items()}}
