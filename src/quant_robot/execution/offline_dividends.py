"""Frozen synthetic cash distributions: entitlement, receivable, explicit credit."""
from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal, ROUND_HALF_UP

from .offline_intent_contract import SHANGHAI, day, exact, instant, version
from .offline_order_state import ACTIVE, DIVIDEND_ENTITLEMENT_UNCERTAIN, VALUATION_UNAVAILABLE, AdmissionRejected, amount, identity, money_context, symbol


def normalize_dividend_policy(value, policy):
    exact(value, {"schema_version", "mode", "source_ref", "coverage_start", "coverage_end", "record_cutoff", "events"}, "dividend policy")
    version(value)
    if value["mode"] != "offline_fixture_only":
        raise ValueError("only synthetic dividends are supported")
    start, end = day(value["coverage_start"]), day(value["coverage_end"])
    if start > end or any(not start <= day(date) <= end for date in policy["session_dates"]):
        raise ValueError("dividend coverage must include every frozen session")
    cutoff = value["record_cutoff"]
    if not isinstance(cutoff, str) or len(cutoff) != 5 or time.fromisoformat(cutoff).isoformat(timespec="minutes") != cutoff:
        raise ValueError("dividend record cutoff must be HH:MM")
    if cutoff <= policy["trading_windows"][-1][1]:
        raise ValueError("dividend cutoff must follow the inclusive final submission window")
    if not isinstance(value["events"], list):
        raise ValueError("dividend events must be explicit")
    events, ids, economics = [], set(), set()
    for raw in value["events"]:
        exact(raw, {"event_id", "symbol", "announced_at", "record_date", "ex_date", "pay_date", "net_cash_per_share", "cash_rounding"}, "dividend")
        key, code = identity(raw["event_id"]), symbol(raw["symbol"])
        identity("cash_dividend:" + key)
        record, ex, pay = (day(raw[k]) for k in ("record_date", "ex_date", "pay_date"))
        known = instant(raw["announced_at"])
        record_close = datetime.combine(record, time.fromisoformat(cutoff), SHANGHAI)
        if (not start <= record < ex <= pay <= end or known > record_close
                or any(date.isoformat() not in policy["session_dates"] for date in (record, ex))):
            raise ValueError("dividend chronology or session coverage is invalid")
        if code not in policy["allowed_symbols"] or raw["cash_rounding"] != "half_up_cent_per_holder":
            raise ValueError("unsupported dividend instrument or cash rounding")
        if key in ids or (code, ex) in economics:
            raise ValueError("duplicate dividend identity or economic event")
        ids.add(key)
        economics.add((code, ex))
        events.append({**raw, "announced_at": known.isoformat(), "net_cash_per_share": str(amount(raw["net_cash_per_share"], positive=True))})
    return {**value, "source_ref": identity(value["source_ref"]), "events": sorted(events, key=lambda row: (row["ex_date"], row["event_id"]))}


def _clock(state, now):
    policy = state.get("dividend_policy")
    if policy is None:
        raise AdmissionRejected("explicit dividend policy required")
    now = instant(now)
    date = now.astimezone(SHANGHAI).date().isoformat()
    if not policy["coverage_start"] <= date <= policy["coverage_end"]:
        raise AdmissionRejected("dividend clock outside declared coverage")
    last = state["corporate_last_transition_at"]
    if last and now < instant(last):
        raise AdmissionRejected("dividend clock moved backward")
    return policy, now, date


@money_context
def entitlement_event(state, now):
    policy, now, date = _clock(state, now)
    due = [e for e in policy["events"] if e["record_date"] == date and e["event_id"] not in state["dividends"]["entitlements"]]
    if not due:
        return None
    from .offline_conversions import require_due_conversions_applied
    require_due_conversions_applied(state, date)
    if (now.astimezone(SHANGHAI).time() < time.fromisoformat(policy["record_cutoff"])
            or (state.get("risk_session") or {}).get("session_date") != date):
        raise AdmissionRejected("entitlement requires the initialized record date at its cutoff")
    affected = {e["symbol"] for e in due}
    if state["faults"] - {VALUATION_UNAVAILABLE} or any(o["symbol"] in affected and o["status"] in ACTIVE for o in state["orders"].values()):
        raise AdmissionRejected("unresolved account or orders prevent entitlement capture")
    rows = {}
    for event in due:
        if now < instant(event["announced_at"]):
            raise AdmissionRejected("dividend announcement is not yet known")
        qty = state["positions"].get(event["symbol"], 0)
        if qty < 0:
            raise AdmissionRejected("negative holdings cannot establish an entitlement")
        value = (qty * Decimal(event["net_cash_per_share"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        rows[event["event_id"]] = {"symbol": event["symbol"], "quantity": qty, "net_amount": str(value),
            "record_date": date, "source_journal_sequence": state["sequence"], "source_journal_hash": state["journal_hash"]}
    return {"kind": "DIVIDEND_ENTITLEMENTS", "data": {"entitlements": rows, "decision_at": now.isoformat()}}


def accrual_event(state, now):
    policy, now, date = _clock(state, now)
    due = [e for e in policy["events"] if e["ex_date"] <= date and e["event_id"] not in state["dividends"]["accrued"]]
    if not due:
        return None
    if DIVIDEND_ENTITLEMENT_UNCERTAIN in state["faults"]:
        raise AdmissionRejected("entitlement requires review after a late fill")
    if any(e["event_id"] not in state["dividends"]["entitlements"] for e in due):
        raise AdmissionRejected("missing record-date entitlement; cannot infer it from current holdings")
    affected = {e["symbol"] for e in due}
    if any(o["symbol"] in affected and o["status"] in ACTIVE for o in state["orders"].values()):
        raise AdmissionRejected("unresolved orders prevent the ex-dividend price transition")
    return {"kind": "DIVIDEND_ACCRUAL", "data": {"event_ids": [e["event_id"] for e in due], "decision_at": now.isoformat()}}


@money_context
def credit_event(state, action_id, receipt_id, cash_amount, now, *, installment=False):
    policy, now, date = _clock(state, now)
    event = next((e for e in policy["events"] if e["event_id"] == action_id), None)
    if event is None or date < event["pay_date"]:
        raise AdmissionRejected("unknown dividend or credit before pay date")
    if installment and (cash_amount <= 0 or cash_amount != cash_amount.quantize(Decimal("0.01"))):
        raise AdmissionRejected("dividend installment must be positive whole cents")
    receipt_key = "dividend_cash:" + receipt_id
    previous = state["receipts"].get(receipt_key)
    if previous:
        if previous["event_id"] != action_id or Decimal(previous["cash_amount"]) != cash_amount:
            raise AdmissionRejected("conflicting dividend receipt identity")
        return None
    if action_id in state["dividends"]["paid"]:
        raise AdmissionRejected("dividend has already been credited")
    owed = state["dividends"]["receivables"].get(action_id)
    if owed is None or (cash_amount > Decimal(owed) if installment else Decimal(owed) != cash_amount):
        raise AdmissionRejected("cash credit does not match an accrued dividend receivable")
    return {"kind": "DIVIDEND_CASH_INSTALLMENT" if installment else "DIVIDEND_CASH_CREDIT", "receipt_key": receipt_key,
        "data": {"event_id": action_id, "cash_amount": str(cash_amount), "decision_at": now.isoformat()}}


def check_dividend_basis(state, packet, now, required):
    policy = state.get("dividend_policy")
    if policy is not None:
        date = now.astimezone(SHANGHAI).date().isoformat()
        if not policy["coverage_start"] <= date <= policy["coverage_end"]:
            raise AdmissionRejected("dividend coverage unavailable")
        if any(e["ex_date"] <= date and e["event_id"] not in state["dividends"]["accrued"] for e in policy["events"]):
            raise AdmissionRejected("due dividend accrual must be applied before portfolio valuation")
    last = state["corporate_last_transition_at"]
    if last and now < instant(last):
        raise AdmissionRejected("risk clock predates the last corporate-action transition")
    for code in required:
        expected = state["price_basis"].get(code, "initial_raw")
        if packet["quotes"].get(code, {}).get("price_basis_id", "initial_raw") != expected:
            raise AdmissionRejected("quote price basis does not match the corporate-action state")
