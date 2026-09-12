"""Exact holder-level share conversions with explicit custody and trading locks."""
from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR, localcontext

from .offline_intent_contract import SHANGHAI, day, exact, instant, version
from .offline_order_state import ACTIVE, VALUATION_UNAVAILABLE, AdmissionRejected, identity, symbol


def _ratio(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError("share ratio must be an exact decimal string or integer")
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValueError("invalid share ratio") from None
    if (not number.is_finite() or number <= 0 or number > 1_000_000
            or number.as_tuple().exponent < -12 or len(number.as_tuple().digits) > 30):
        raise ValueError("share ratio is outside exact supported bounds")
    return str(number)


def normalize_conversion_policy(value, policy):
    exact(value, {"schema_version", "mode", "source_ref", "coverage_start", "coverage_end", "record_cutoff", "events"}, "conversion policy")
    version(value)
    if value["mode"] != "offline_fixture_only":
        raise ValueError("only synthetic share conversions are supported")
    start, end = day(value["coverage_start"]), day(value["coverage_end"])
    if start > end or any(not start <= day(date) <= end for date in policy["session_dates"]):
        raise ValueError("conversion coverage must include every frozen session")
    cutoff = value["record_cutoff"]
    if (not isinstance(cutoff, str) or len(cutoff) != 5 or time.fromisoformat(cutoff).isoformat(timespec="minutes") != cutoff
            or cutoff <= policy["trading_windows"][-1][1]):
        raise ValueError("conversion cutoff must follow the inclusive submission window in HH:MM")
    if not isinstance(value["events"], list):
        raise ValueError("conversion events must be explicit")
    events, ids, economics = [], set(), set()
    dispositions = {"reject_fractional": "none", "ceil_per_holder": "holder_share_credit", "floor_per_holder": "fund_assets"}
    for raw in value["events"]:
        exact(raw, {"event_id", "symbol", "announced_at", "record_date", "suspension_date", "conversion_date", "tradable_date",
            "share_ratio", "share_rounding", "fractional_disposition"}, "share conversion")
        key, code = identity(raw["event_id"]), symbol(raw["symbol"])
        identity("share_conversion:" + key)
        record, convert, tradable = (day(raw[k]) for k in ("record_date", "conversion_date", "tradable_date"))
        suspension = day(raw["suspension_date"])
        known = instant(raw["announced_at"])
        if (not start <= record < suspension <= convert <= tradable <= end
                or known > datetime.combine(record, time.fromisoformat(cutoff), SHANGHAI)
                or any(date.isoformat() not in policy["session_dates"] for date in (record, tradable))):
            raise ValueError("unsupported conversion chronology or session coverage")
        if (code not in policy["allowed_symbols"] or not isinstance(raw["share_rounding"], str)
                or dispositions.get(raw["share_rounding"]) != raw["fractional_disposition"]):
            raise ValueError("unsupported conversion instrument or fractional disposition")
        if key in ids or (code, convert) in economics:
            raise ValueError("duplicate conversion identity or economic event")
        ids.add(key); economics.add((code, convert))
        events.append({**raw, "announced_at": known.isoformat(), "share_ratio": _ratio(raw["share_ratio"])})
    events.sort(key=lambda row: (row["conversion_date"], row["event_id"]))
    previous = {}
    for row in events:
        if row["symbol"] in previous and row["record_date"] < previous[row["symbol"]]["tradable_date"]:
            raise ValueError("overlapping conversion custody periods are unsupported")
        previous[row["symbol"]] = row
    return {**value, "source_ref": identity(value["source_ref"]), "events": events}


def _clock(state, now):
    policy = state.get("conversion_policy")
    if policy is None:
        raise AdmissionRejected("explicit conversion policy required")
    now = instant(now)
    date = now.astimezone(SHANGHAI).date().isoformat()
    if not policy["coverage_start"] <= date <= policy["coverage_end"]:
        raise AdmissionRejected("conversion clock outside declared coverage")
    last = state["corporate_last_transition_at"]
    if last and now < instant(last):
        raise AdmissionRejected("corporate-action clock moved backward")
    return policy, now, date


def require_due_conversions_applied(state, date):
    if any(row["conversion_date"] <= date and row["event_id"] not in state["conversions"]["applied"]
            for row in (state.get("conversion_policy") or {}).get("events", [])):
        raise AdmissionRejected("due share conversion must be applied before using current inventory")


def entitlement_event(state, now):
    policy, now, date = _clock(state, now)
    due = [row for row in policy["events"] if row["record_date"] == date and row["event_id"] not in state["conversions"]["entitlements"]]
    if not due:
        return None
    require_due_conversions_applied(state, date)
    if (now.astimezone(SHANGHAI).time() < time.fromisoformat(policy["record_cutoff"])
            or (state.get("risk_session") or {}).get("session_date") != date):
        raise AdmissionRejected("conversion entitlement requires the initialized record date at its cutoff")
    affected = {row["symbol"] for row in due}
    if state["faults"] - {VALUATION_UNAVAILABLE} or any(o["symbol"] in affected and o["status"] in ACTIVE for o in state["orders"].values()):
        raise AdmissionRejected("unresolved account or orders prevent conversion entitlement capture")
    rows = {}
    for event in due:
        if now < instant(event["announced_at"]):
            raise AdmissionRejected("conversion announcement is not yet known")
        qty = state["positions"].get(event["symbol"], 0)
        if qty < 0 or qty > 2**53 - 1:
            raise AdmissionRejected("holder quantity exceeds the exact supported conversion bounds")
        rows[event["event_id"]] = {"symbol": event["symbol"], "quantity": qty, "record_date": date,
            "source_journal_sequence": state["sequence"], "source_journal_hash": state["journal_hash"]}
    return {"kind": "CONVERSION_ENTITLEMENTS", "data": {"entitlements": rows, "decision_at": now.isoformat()}}


def _convert(quantity, event):
    ratio = Decimal(event["share_ratio"])
    with localcontext() as precision:
        precision.prec = max(50, len(str(quantity)) + len(ratio.as_tuple().digits) + 2)
        theoretical = quantity * ratio
        rounding = ROUND_FLOOR if event["share_rounding"] == "floor_per_holder" else ROUND_CEILING
        converted = theoretical.to_integral_value(rounding=rounding)
        if event["share_rounding"] == "reject_fractional" and converted != theoretical:
            raise AdmissionRejected("fractional holder shares are forbidden by the frozen rule")
        if converted > 2**53 - 1:
            raise AdmissionRejected("converted quantity exceeds exact supported bounds")
        return int(converted), str(theoretical), str(converted - theoretical)


def conversion_event(state, now):
    policy, now, date = _clock(state, now)
    due = [row for row in policy["events"] if row["conversion_date"] <= date and row["event_id"] not in state["conversions"]["applied"]]
    if not due:
        return None
    if any(row["event_id"] not in state["conversions"]["entitlements"] for row in due):
        raise AdmissionRejected("missing conversion record-date entitlement")
    affected = {row["symbol"] for row in due}
    if state["faults"] - {VALUATION_UNAVAILABLE} or any(o["symbol"] in affected and o["status"] in ACTIVE for o in state["orders"].values()):
        raise AdmissionRejected("unresolved account or orders require review before conversion")
    applied = {}
    for row in due:
        qty = state["conversions"]["entitlements"][row["event_id"]]["quantity"]
        if state["positions"].get(row["symbol"], 0) != qty:
            raise AdmissionRejected("current holdings differ from conversion entitlement; review required")
        converted, theoretical, adjustment = _convert(qty, row)
        applied[row["event_id"]] = {"symbol": row["symbol"], "old_quantity": qty, "new_quantity": converted,
            "unrounded_quantity": theoretical, "rounding_share_adjustment": adjustment,
            "share_ratio": row["share_ratio"], "share_rounding": row["share_rounding"],
            "fractional_disposition": row["fractional_disposition"], "tradable_date": row["tradable_date"]}
    return {"kind": "SHARE_CONVERSIONS", "data": {"conversions": applied, "decision_at": now.isoformat()}}


def check_conversion_state(state, packet, now, required):
    date = now.astimezone(SHANGHAI).date().isoformat()
    policy = state.get("conversion_policy")
    if policy is not None:
        if not policy["coverage_start"] <= date <= policy["coverage_end"]:
            raise AdmissionRejected("conversion coverage unavailable")
        require_due_conversions_applied(state, date)
        if any(row["symbol"] in required and row["suspension_date"] <= date < row["tradable_date"] for row in policy["events"]):
            raise AdmissionRejected("conversion instrument is not yet tradable; no supported valuation mark")
    for code in required:
        lock = state["conversions"]["locks"].get(code)
        if lock and date < lock["tradable_date"]:
            raise AdmissionRejected("converted instrument is not yet tradable; no supported valuation mark")


def opening_conversion_locks(state, packet):
    released = []
    for code, lock in state["conversions"]["locks"].items():
        if packet["session_date"] < lock["tradable_date"]:
            if packet["sellable_positions"].get(code, 0):
                raise AdmissionRejected("converted shares remain locked before their tradable date")
        else:
            released.append(code)
    return released


def has_converted_order_basis(state, order):
    return any(row["symbol"] == order["symbol"] and row["event_id"] in state["conversions"]["applied"]
        and order["admission"]["session_date"] < row["conversion_date"]
        for row in (state.get("conversion_policy") or {}).get("events", []))
