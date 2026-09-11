"""Atomic revalidation of a reserved intent; no transport or reusable permit."""
from __future__ import annotations

from .offline_admission import admission_event, deny
from .offline_intent_contract import instant
from .offline_order_state import risk_deficit


def dispatch_event(state, order_id, attempt_id, packet, now):
    if attempt_id in state["attempted_dispatch_ids"]:
        deny("dispatch attempt identity has already been consumed")
    order = state["orders"].get(order_id)
    if order is None:
        deny("unknown dispatch order identity")
    if order["status"] != "PENDING" or order["filled_quantity"] or "dispatch" in order:
        deny("only an unfilled, never-prepared pending order can be prepared")
    admission = order.get("admission")
    if admission is None or admission["policy_fingerprint"] != state["admission_policy_fingerprint"]:
        deny("dispatch requires the original guarded admission policy")
    if admission["session_date"] != packet["session_date"]:
        deny("dispatch cannot move a DAY order into another session")
    if instant(now) < instant(admission["decision_at"]):
        deny("dispatch clock precedes the original admission")
    if risk_deficit(state):
        deny("account or reservation deficit before dispatch", stop=True)

    # Revalidate the ORIGINAL immutable intent as one candidate. Its unfilled
    # reservation is removed only from this temporary view, never the journal.
    # Other orders, fills, sellable shares and all risk budgets stay in place.
    view = {**state,
        "orders": {key: row for key, row in state["orders"].items() if key != order_id},
        "attempted_intent_ids": state["attempted_intent_ids"] - {order_id},
        "attempted_idempotency_keys": state["attempted_idempotency_keys"] - {order["idempotency_key"]}}
    checked = admission_event(view, admission["intent"], packet, now)["data"]["admission"]
    from .offline_timeouts import ack_deadline
    return {"kind": "DISPATCH_PREPARED", "data": {"order_id": order_id, "attempt_id": attempt_id,
        "context": packet, "decision_at": checked["decision_at"], "risk": checked["risk"],
        "policy_fingerprint": checked["policy_fingerprint"], "mode": "offline_fixture_only", "executable": False,
        **ack_deadline(state, now)}}
