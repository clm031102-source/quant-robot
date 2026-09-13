"""Scheduled synthetic close observations used by an explicit daily-loss policy."""
from datetime import datetime, time, timedelta
from decimal import Decimal

from .offline_intent_contract import SHANGHAI, day, instant
from .offline_order_state import ACTIVE, VALUATION_UNAVAILABLE, AdmissionRejected, risk_deficit


BASIS = "previous_session_close_v1"


def opening_reference(state, policy, session_date, equity):
    if policy.get("daily_loss_basis") != BASIS:
        return {}
    index = policy["session_dates"].index(session_date)
    if index == 0 and state.get("risk_session") is None:
        evidence = {"basis": "first_session_open", "session_date": session_date, "book_equity": str(equity)}
    else:
        close = state.get("last_session_close")
        expected = policy["session_dates"][index - 1] if index else None
        if not close or close["session_date"] != expected or close["policy_fingerprint"] != state["admission_policy_fingerprint"]:
            raise AdmissionRejected("qualified previous session close is required for the daily loss baseline")
        evidence = dict(close)
    return {"daily_loss_reference_equity": evidence["book_equity"], "daily_loss_reference": evidence}


def close_observation(state, policy, packet, now, equity):
    if policy.get("daily_loss_basis") != BASIS:
        return None
    if (state.get("last_session_close") or {}).get("session_date") == packet["session_date"]:
        return None
    closing = datetime.combine(day(packet["session_date"]), time(15), SHANGHAI)
    # First usable observation in this frozen 30-second window; never select a
    # later favorable mark or reinterpret an arbitrary intraday quote as close.
    if not closing <= now <= closing + timedelta(seconds=30) or instant(packet["as_of"]) < closing:
        return None
    if risk_deficit(state) or state["faults"] - {VALUATION_UNAVAILABLE} or any(row["status"] in ACTIVE for row in state["orders"].values()):
        return None
    return {"basis": BASIS, "session_date": packet["session_date"], "book_equity": str(equity),
        "decision_at": now.isoformat(), "context_as_of": packet["as_of"],
        "context_journal_sequence": packet["journal_sequence"], "context_journal_hash": packet["journal_hash"],
        "policy_fingerprint": state["admission_policy_fingerprint"],
        "quote_basis": "first_valid_supplied_midquote_book_15h00_to_15h00m30s_Shanghai",
        "official_exchange_close_verified": False, "mode": "offline_fixture_only", "executable": False}


def loss_from_reference(session, equity):
    return Decimal(session.get("daily_loss_reference_equity", session["opening_equity"])) - equity
