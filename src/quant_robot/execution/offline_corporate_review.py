"""Read-only synthetic corporate-action evidence; never corrects or unlocks."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .offline_journal import OfflineOrderJournal
from .offline_order_state import ACTIVE, CONVERSION_UNCERTAIN, DIVIDEND_ENTITLEMENT_UNCERTAIN


_MISSING = ["actual_execution_time_and_timezone", "source_message_identity_and_revision_relationship",
    "quantity_and_price_basis", "authoritative_entitlement_and_settlement_evidence"]
MAX_REVIEW_ITEMS = 25_000


def _reference(row):
    return {key: row[key] for key in ("sequence", "journal_recorded_at", "event_hash")}


def _capture(events, kind, action_id):
    matches = [row for row in events if row["event"]["kind"] == kind
        and action_id in row["event"]["data"]["entitlements"]]
    if len(matches) > 1:
        raise ValueError("multiple entitlement captures require an explicit revision protocol")
    return matches[0] if matches else None


def _action_events(events, action_id, kind):
    kinds = {"DIVIDEND_ENTITLEMENTS", "DIVIDEND_ACCRUAL", "DIVIDEND_CASH_CREDIT"} if kind == "dividend" else {"CONVERSION_ENTITLEMENTS", "SHARE_CONVERSIONS"}
    result = []
    for row in events:
        event, data = row["event"], row["event"]["data"]
        if event["kind"] in kinds and (action_id in data.get("entitlements", {}) or action_id in data.get("conversions", {})
                or action_id in data.get("event_ids", []) or data.get("event_id") == action_id):
            selected = {key: value for key, value in data.items() if key not in {"entitlements", "conversions", "event_ids"}}
            for key in ("entitlements", "conversions"):
                if action_id in data.get(key, {}): selected[key] = {action_id: data[key][action_id]}
            if action_id in data.get("event_ids", []): selected["event_ids"] = [action_id]
            result.append({**_reference(row), "kind": event["kind"], "payload": selected,
                "payload_scope": "selected_action_fields; event_hash_references_original_full_event"})
    return result


def _candidates(events, snapshot, rule, capture):
    if capture is None:
        return []
    result = []
    for row in events:
        event = row["event"]
        if event["kind"] not in {"FILL", "CONVERSION_UNAPPLIED_FILL"} or row["sequence"] <= capture["sequence"]:
            continue
        payload = event["data"]
        order = snapshot["orders"][payload["order_id"]]
        if order["symbol"] != rule["symbol"]:
            continue
        session = (order.get("admission") or {}).get("session_date")
        if session is not None and session > rule["record_date"]:
            continue
        result.append({**_reference(row), "kind": event["kind"], "payload": payload,
            "order_admission_session": session, "applied_to_book": event["kind"] == "FILL",
            "association": "possible_under_recorded_order_session_rule",
            "execution_attribution_confirmed": False, "actual_execution_at": None,
            "journal_time_is_execution_time": False})
    return result


def build_corporate_action_review(path, *, max_events=10_000, max_payload_bytes=16_000_000):
    evidence = OfflineOrderJournal.inspect_evidence(path, max_events=max_events, max_payload_bytes=max_payload_bytes)
    snapshot, events = evidence["snapshot"], evidence["events"]
    actions, item_count = [], 0
    for kind, section, capture_kind, fault in (
            ("dividend", "dividends", "DIVIDEND_ENTITLEMENTS", DIVIDEND_ENTITLEMENT_UNCERTAIN),
            ("conversion", "conversions", "CONVERSION_ENTITLEMENTS", CONVERSION_UNCERTAIN)):
        policy = evidence["policies"][kind + "_policy"]
        for rule in (policy or {}).get("events", []):
            action_id, code = rule["event_id"], rule["symbol"]
            capture = _capture(events, capture_kind, action_id)
            entitlement = snapshot[section]["entitlements"].get(action_id)
            if (entitlement is None) != (capture is None):
                raise ValueError("captured entitlement and its source event disagree")
            candidates = _candidates(events, snapshot, rule, capture)
            row = {"kind": kind, "event_id": action_id, "symbol": code, "rule": rule,
                "policy_source_ref": policy["source_ref"], "policy_fingerprint": snapshot[kind + "_policy_fingerprint"],
                "captured_entitlement": entitlement, "capture_event": _reference(capture) if capture else None,
                "recorded_action_events": _action_events(events, action_id, kind),
                "candidate_receipts": candidates, "family_review_fault_recorded": fault in snapshot["faults"],
                "active_orders": {key: {name: order[name] for name in ("symbol", "side", "quantity", "limit_price", "status", "filled_quantity", "filled_notional", "commission")}
                    for key, order in snapshot["orders"].items()
                    if order["symbol"] == code and order["status"] in ACTIVE},
                "missing_evidence": list(_MISSING) if candidates or fault in snapshot["faults"] else [],
                "correction_proposed": False}
            if kind == "dividend":
                row.update(accrued=action_id in snapshot[section]["accrued"], paid=action_id in snapshot[section]["paid"],
                    receivable=snapshot[section]["receivables"].get(action_id))
            else:
                lock = snapshot[section]["locks"].get(code)
                row.update(applied_conversion=snapshot[section]["applied"].get(action_id),
                    lock=lock if lock and lock["event_id"] == action_id else None,
                    released=action_id in snapshot[section]["released"],
                    unapplied_fill_scope="all_unapplied_for_symbol_not_confirmed_action_attribution",
                    unapplied_fills={key: value for key, value in snapshot[section]["unapplied_fills"].items()
                        if snapshot["orders"][value["order_id"]]["symbol"] == code})
            item_count += 1 + len(candidates) + len(row["recorded_action_events"]) + len(row["active_orders"]) + len(row.get("unapplied_fills", {}))
            if item_count > MAX_REVIEW_ITEMS:
                raise ValueError("review exceeds relationship limit; no partial evidence returned")
            actions.append(row)
    review_faults = sorted(set(snapshot["faults"]) & {DIVIDEND_ENTITLEMENT_UNCERTAIN, CONVERSION_UNCERTAIN})
    gaps = [{"fault": fault, "reason": "no_candidate_receipt_identified; source attribution remains unresolved"}
        for fault in review_faults if not any(action["candidate_receipts"] for action in actions
            if action["kind"] == ("dividend" if fault == DIVIDEND_ENTITLEMENT_UNCERTAIN else "conversion"))]
    return {"schema_version": 1, "mode": "offline_fixture_only", "status": "inspection_only",
        "generated_at": datetime.now(timezone.utc).isoformat(), "executable": False,
        "automatic_correction_allowed": False, "clears_faults": False, "qualifies_for_strategy_promotion": False,
        "counts_as_forward_paper_days": 0, "recorded_corporate_review_required": bool(review_faults),
        "recorded_corporate_review_faults": review_faults,
        "unexplained_review_faults": gaps, "policies": evidence["policies"],
        "journal": {"path": str(Path(path).resolve()), "sequence": snapshot["sequence"], "hash": snapshot["journal_hash"],
            "genesis_hash": events[0]["event_hash"], "view": "single_verified_read_transaction"},
        "source_event_count": evidence["source_event_count"], "source_payload_bytes": evidence["source_payload_bytes"],
        "review_item_count": item_count, "review_item_limit": MAX_REVIEW_ITEMS,
        "account": {key: snapshot[key] for key in ("cash", "positions", "reserved_cash", "reserved_positions", "paused", "kill_switch", "faults")},
        "price_basis": snapshot["price_basis"], "actions": actions,
        "unapplied_fills": snapshot["conversions"]["unapplied_fills"],
        "limitations": ["recorded synthetic book only, not authenticated account data", "candidate links do not establish execution time or cause",
            "one receipt may be a candidate for multiple actions; do not sum hypothetical corrections",
            "absence of a recorded fault does not certify complete rights or sources", "another writer can advance the journal after this view"]}
