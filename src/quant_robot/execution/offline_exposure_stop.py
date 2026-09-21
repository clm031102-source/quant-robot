"""Explicit, synthetic reduction policy; a latched stop is never cleared here."""
from decimal import Decimal


EXPOSURE_CAUSES = {"single_position", "capital_exposure"}


def stop_causes(session):
    causes = session.get("risk_stop_causes")
    if not isinstance(causes, list) or not causes or any(not isinstance(item, str) or not item for item in causes):
        return {"unclassified"} if session.get("risk_stop") else set()
    return set(causes)


def latch_stop(state, causes):
    session = state.get("risk_session")
    if session is None:
        return
    previous = stop_causes(session) if session.get("risk_stop") else set()
    valid = isinstance(causes, list) and causes and all(isinstance(item, str) and item for item in causes)
    session["risk_stop_causes"] = sorted(previous | (set(causes) if valid else {"unclassified"}))
    session["risk_stop"] = True


def exposure_only_stop(state, policy):
    session = state.get("risk_session") or {}
    causes = stop_causes(session)
    return (policy.get("exposure_stop_action") == "reduce_only" and session.get("risk_stop")
        and bool(causes) and causes <= EXPOSURE_CAUSES)


def reduction_evidence(state, order, policy, marks):
    from .offline_order_state import ACTIVE, AdmissionRejected, risk_deficit
    if not (state.get("risk_session") or {}).get("risk_stop"):
        return None
    if not exposure_only_stop(state, policy):
        raise AdmissionRejected("session risk stop remains active")
    held = state["positions"].get(order["symbol"], 0)
    if order["side"] != "SELL" or not 0 < order["quantity"] <= held:
        raise AdmissionRejected("exposure stop permits only a reduction of existing holdings")
    if any(row["status"] in ACTIVE and row["side"] == "BUY" for row in state["orders"].values()):
        raise AdmissionRejected("resolve pending buys before exposure-stop reduction")
    if risk_deficit(state):
        raise AdmissionRejected("account or reservation deficit prevents exposure-stop reduction",
            risk_stop=True, risk_stop_causes=["account_or_reservation_deficit"])
    return {"policy_action": "reduce_only", "stop_causes": sorted(stop_causes(state["risk_session"])),
        "held_quantity_before": held, "sell_quantity": order["quantity"],
        "exposure_reduction_if_filled_at_known_mark": str(Decimal(order["quantity"]) * marks[order["symbol"]]),
        "pending_sells_reduce_committed_exposure": False, "stop_reset": False,
        "mode": "offline_fixture_only", "executable": False}
