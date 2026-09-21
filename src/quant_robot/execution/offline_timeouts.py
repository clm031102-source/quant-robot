"""Frozen synthetic timeout rules: elapsed time is never a cancellation receipt."""
from __future__ import annotations

from datetime import datetime, time, timedelta
import re

from .offline_intent_contract import SHANGHAI, day, exact, instant, version
from .offline_order_state import ACTIVE, identity, units


def normalize_timeout_policy(value, admission):
    exact(value, {"schema_version", "mode", "policy_id", "ack_timeout_seconds",
        "cancel_timeout_seconds", "day_order_cutoff"}, "timeout policy")
    version(value)
    if value["mode"] != "offline_fixture_only":
        raise ValueError("only offline_fixture_only timeouts are supported")
    cutoff = value["day_order_cutoff"]
    if not isinstance(cutoff, str) or re.fullmatch(r"[0-9]{2}:[0-9]{2}", cutoff) is None:
        raise ValueError("invalid DAY order cutoff")
    cutoff_time = time.fromisoformat(cutoff)
    if cutoff_time < time.fromisoformat(admission["trading_windows"][-1][1]):
        raise ValueError("DAY cutoff precedes the final submission window")
    result = {"schema_version": 1, "mode": value["mode"], "policy_id": identity(value["policy_id"]),
        "day_order_cutoff": cutoff}
    for key in ["ack_timeout_seconds", "cancel_timeout_seconds"]:
        result[key] = units(value[key], positive=True)
        if result[key] > 86400:
            raise ValueError("timeout must not exceed one day")
    return result


def ack_deadline(state, now):
    policy = state.get("timeout_policy")
    return ({"acknowledgement_deadline": (instant(now) + timedelta(seconds=policy["ack_timeout_seconds"])).isoformat()}
        if policy else {})


def cancel_timing(state, order, now):
    policy = state.get("timeout_policy")
    if policy is None:
        return {}
    now = instant(now)
    start = order.get("dispatch", order["admission"])["decision_at"]
    if now < instant(start):
        raise ValueError("cancel clock precedes the order decision")
    return {"requested_at": now.isoformat(),
        "confirmation_deadline": (now + timedelta(seconds=policy["cancel_timeout_seconds"])).isoformat()}


def timeout_event(state, now):
    policy = state.get("timeout_policy")
    if policy is None:
        raise ValueError("a frozen timeout policy is required")
    now = instant(now)
    if state.get("last_timeout_at") and now < instant(state["last_timeout_at"]):
        raise ValueError("timeout clock moved backward")
    expired = []
    for key, order in state["orders"].items():
        if order["status"] not in ACTIVE:
            continue
        admission, dispatch, cancel = order["admission"], order.get("dispatch", {}), order.get("cancel_request", {})
        previous = [admission["decision_at"], *([dispatch["decision_at"]] if dispatch else []),
            *([cancel["requested_at"]] if cancel else [])]
        if any(now < instant(value) for value in previous):
            raise ValueError("timeout clock precedes an order decision")
        end = datetime.combine(day(admission["session_date"]), time.fromisoformat(policy["day_order_cutoff"]), SHANGHAI)
        reason, deadline = None, None
        if now >= end:
            reason, deadline = "day_order_expired", end
        elif order["status"] in {"CANCEL_PENDING", "UNKNOWN"} and cancel and now >= instant(cancel["confirmation_deadline"]):
            reason, deadline = "cancel_confirmation_timeout", instant(cancel["confirmation_deadline"])
        elif order["status"] == "PENDING":
            if dispatch and now >= instant(dispatch["acknowledgement_deadline"]):
                reason, deadline = "acknowledgement_timeout", instant(dispatch["acknowledgement_deadline"])
            elif not dispatch and now >= instant(admission["intent"]["expires_at"]):
                reason, deadline = "unprepared_intent_expired", instant(admission["intent"]["expires_at"])
        prior = order.get("timeout", {})
        if reason and (reason != prior.get("reason") or instant(deadline).isoformat() != prior.get("deadline")):
            expired.append({"order_id": key, "previous_status": order["status"], "reason": reason,
                "deadline": instant(deadline).isoformat(), "observed_at": now.isoformat()})
    return ({"kind": "ORDER_TIMEOUT", "data": {"observed_at": now.isoformat(), "orders": expired,
        "policy_fingerprint": state["timeout_policy_fingerprint"]}} if expired else None)
