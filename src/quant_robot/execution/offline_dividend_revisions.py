"""Append-only dividend corrections under explicitly assumed synthetic facts."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, time
from decimal import Decimal, ROUND_HALF_UP
import json
import re

from .offline_dividends import _clock
from .offline_execution_evidence import validate_execution_supplement, _time
from .offline_intent_contract import SHANGHAI, exact, fingerprint, version
from .offline_order_state import ACTIVE, DIVIDEND_ENTITLEMENT_UNCERTAIN, AdmissionRejected, effective_dividend_entitlement, identity, money_context, units


def normalize_facts(value):
    exact(value, {"schema_version", "mode", "revision_id", "journal", "event_id", "policy_fingerprint", "original_entitlement_fingerprint",
        "corrected_quantity", "record_date", "facts_as_of", "entitlement_source", "settlement_receipt_keys", "execution_supplement", "receipt_decisions"}, "dividend revision facts")
    version(value)
    if value["mode"] != "offline_fixture_only":
        raise ValueError("only explicitly assumed offline revision facts are supported")
    exact(value["journal"], {"sequence", "hash", "genesis_hash"}, "revision journal")
    units(value["journal"]["sequence"], positive=True)
    exact(value["execution_supplement"], {"schema_version", "mode", "journal", "records"}, "execution supplement")
    identity(value["revision_id"]); identity(value["event_id"]); units(value["corrected_quantity"])
    source = value["entitlement_source"]
    exact(source, {"mode", "source_ref", "sha256"}, "entitlement source")
    if source["mode"] != "assumed_offline_fixture":
        raise ValueError("entitlement source is not an assumed offline fixture")
    identity(source["source_ref"])
    for digest in (source["sha256"], value["policy_fingerprint"], value["original_entitlement_fingerprint"]):
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("invalid dividend evidence fingerprint")
    _time(value["facts_as_of"], "facts_as_of")
    for name in ("settlement_receipt_keys", "receipt_decisions"):
        if not isinstance(value[name], list) or len(value[name]) > 500:
            raise ValueError("dividend revision list limit exceeded")
    for key in value["settlement_receipt_keys"]:
        identity(key)
    for row in value["receipt_decisions"]:
        exact(row, {"evidence_id", "entitlement_effect"}, "receipt decision")
        identity(row["evidence_id"])
        if row["entitlement_effect"] not in ("included", "excluded"):
            raise ValueError("unresolved receipt decision")
    try:
        encoded = json.dumps(value, allow_nan=False).encode("utf-8")
    except (TypeError, RecursionError) as exc:
        raise ValueError("unsupported revision facts structure") from exc
    if len(encoded) > 1_250_000:
        raise ValueError("dividend revision facts exceed size limit")
    return deepcopy(value)


def _candidates(view, rule):
    captures = [row for row in view["events"] if row["event"]["kind"] == "DIVIDEND_ENTITLEMENTS"
        and rule["event_id"] in row["event"]["data"]["entitlements"]]
    if not captures:
        return []
    if len(captures) != 1:
        raise AdmissionRejected("multiple original captures require review")
    rows = []
    for row in view["events"]:
        if row["sequence"] <= captures[0]["sequence"] or row["event"]["kind"] not in {"FILL", "CONVERSION_UNAPPLIED_FILL"}:
            continue
        order = view["snapshot"]["orders"][row["event"]["data"]["order_id"]]
        if order["symbol"] == rule["symbol"] and order["admission"]["session_date"] <= rule["record_date"]:
            rows.append(row)
    return rows


def _check_dependencies(state, rule):
    code, target = rule["symbol"], rule["event_id"]
    if any(order["symbol"] == code and order["status"] in ACTIVE for order in state["orders"].values()):
        raise AdmissionRejected("active orders prevent dividend revision")
    if any(row["symbol"] == code for row in state["conversions"]["applied"].values()):
        raise AdmissionRejected("converted units require a separate correction protocol")
    for policy_key, state_key in (("dividend_policy", "dividends"), ("conversion_policy", "conversions")):
        for other in (state.get(policy_key) or {}).get("events", []):
            if (other["symbol"] == code and (policy_key != "dividend_policy" or other["event_id"] != target)
                    and other["record_date"] >= rule["record_date"] and other["event_id"] in state[state_key]["entitlements"]):
                raise AdmissionRejected("later captured corporate-action dependency requires review")


def _resolved_quantity(state, packet, view, rule, cutoff):
    validated = validate_execution_supplement(packet["execution_supplement"], view)
    candidates = _candidates(view, rule)
    if not candidates:
        raise AdmissionRejected("no recorded late receipts support this revision route")
    required = {row["sequence"]: row for row in candidates}
    records = {row["assertion"]["evidence_id"]: row["assertion"] for row in validated["records"]}
    prior_revision = state["dividends"]["revisions"].get(rule["event_id"])
    if prior_revision:
        prior_facts = state["receipts"]["dividend_revision:" + prior_revision["revision_id"]]["facts"]
        if any(records.get(old["evidence_id"]) != old for old in prior_facts["execution_supplement"]["records"]):
            raise AdmissionRejected("previous evidence records must be retained unchanged")
    for key, value in state["receipts"].items():
        if key.startswith("dividend_revision:") and value["event_id"] == rule["event_id"]:
            prior_facts = value["facts"]
            if (prior_facts["entitlement_source"]["sha256"] == packet["entitlement_source"]["sha256"]
                    and prior_facts["corrected_quantity"] != packet["corrected_quantity"]):
                raise AdmissionRejected("same entitlement source cannot assert a different quantity")
    predecessors = {row["source"]["previous_evidence_id"] for row in records.values() if row["source"]["previous_evidence_id"] is not None}
    leaves = set(records) - predecessors
    decisions = packet["receipt_decisions"]
    if len(decisions) != len(leaves) or {row["evidence_id"] for row in decisions} != leaves:
        raise AdmissionRejected("all terminal evidence revisions need an explicit decision")
    if any(row["receipt"]["sequence"] not in required for row in records.values()):
        raise AdmissionRejected("supplement contains unrelated receipt evidence")
    quantity = state["dividends"]["entitlements"][rule["event_id"]]["quantity"]
    seen = set(); as_of = _time(packet["facts_as_of"], "facts_as_of")
    for decision in decisions:
        assertion = records[decision["evidence_id"]]; sequence = assertion["receipt"]["sequence"]
        if sequence in seen:
            raise AdmissionRejected("multiple source leaves for one receipt remain ambiguous")
        seen.add(sequence); row = required[sequence]; original = row["event"]["data"]; execution = assertion["execution"]
        order = state["orders"][original["order_id"]]
        if (row["event"]["kind"] != "FILL" or assertion["operation"] == "cancel" or execution["executed_at"] is None
                or execution["quantity"] != original["quantity"] or execution["price"] is None
                or Decimal(execution["price"]) != Decimal(original["price"])
                or execution["quantity_basis"] != "unconverted_shares" or execution["price_basis"] != "raw_execution"
                or assertion["source"]["claimed_artifact_sha256"] is None):
            raise AdmissionRejected("execution or unit facts require a separate fill correction or source review")
        executed = _time(execution["executed_at"], "executed_at")
        if _time(assertion["observed_at"], "observed_at") > as_of or executed < _time(order["admission"]["decision_at"], "order decision"):
            raise AdmissionRejected("execution evidence chronology disagrees with revision facts")
        included = executed <= cutoff
        if included != (decision["entitlement_effect"] == "included"):
            raise AdmissionRejected("receipt decision disagrees with record cutoff")
        if included:
            quantity += (1 if order["side"] == "BUY" else -1) * original["quantity"]
    if seen != set(required) or quantity != packet["corrected_quantity"] or quantity < 0:
        raise AdmissionRejected("incomplete receipts or unexplained corrected quantity")
    return quantity, {str(row["sequence"]): row["event_hash"] for row in candidates}, validated["supplement_fingerprint"]


def _may_clear_dividend_fault(state, view, action_id, reviewed):
    if any(row["event"]["kind"] == "FAULT" and row["event"]["data"].get("reason") == DIVIDEND_ENTITLEMENT_UNCERTAIN for row in view["events"]):
        return False
    for rule in state["dividend_policy"]["events"]:
        candidates = {str(row["sequence"]): row["event_hash"] for row in _candidates(view, rule)}
        current = reviewed if rule["event_id"] == action_id else state["dividends"]["reviewed_receipts"].get(rule["event_id"], {})
        if candidates and candidates != current:
            return False
    return True


@money_context
def revision_event(state, packet, now, evidence_supplier):
    receipt_key = "dividend_revision:" + packet["revision_id"]
    previous = state["receipts"].get(receipt_key)
    if previous is not None:
        if previous["facts"] != packet:
            raise AdmissionRejected("conflicting dividend revision identity")
        return None
    policy, now, _date = _clock(state, now)
    as_of = _time(packet["facts_as_of"], "facts_as_of")
    if as_of > now or (state["corporate_last_transition_at"] and as_of < _time(state["corporate_last_transition_at"], "corporate transition")):
        raise AdmissionRejected("revision facts are future or predate recorded settlements")
    action_id = packet["event_id"]
    rule = next((row for row in policy["events"] if row["event_id"] == action_id), None)
    original = state["dividends"]["entitlements"].get(action_id)
    if rule is None or original is None or packet["record_date"] != rule["record_date"]:
        raise AdmissionRejected("unknown or uncaptured dividend revision")
    if packet["policy_fingerprint"] != state["dividend_policy_fingerprint"] or packet["original_entitlement_fingerprint"] != fingerprint(original):
        raise AdmissionRejected("dividend rule or original entitlement fingerprint mismatch")
    _check_dependencies(state, rule)
    view = evidence_supplier()
    binding = dict(genesis_hash=view["events"][0]["event_hash"], sequence=state["sequence"], hash=state["journal_hash"])
    if packet["journal"] != binding or packet["execution_supplement"].get("journal") != binding:
        raise AdmissionRejected("dividend revision has a stale journal anchor")
    settlements = sorted(key for key, value in state["receipts"].items() if key.startswith("dividend_cash:") and value["event_id"] == action_id)
    if sorted(packet["settlement_receipt_keys"]) != settlements:
        raise AdmissionRejected("complete recorded dividend settlement evidence required")
    cutoff = datetime.combine(datetime.fromisoformat(rule["record_date"]).date(), time.fromisoformat(policy["record_cutoff"]), SHANGHAI)
    quantity, reviewed, supplement_hash = _resolved_quantity(state, packet, view, rule, cutoff)
    net = (quantity * Decimal(rule["net_cash_per_share"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    adjustment = net - Decimal(effective_dividend_entitlement(state, action_id)["net_amount"])
    posted = adjustment if action_id in state["dividends"]["accrued"] else Decimal("0")
    return dict(kind="DIVIDEND_ENTITLEMENT_REVISION", receipt_key=receipt_key,
        data=dict(event_id=action_id, revision_id=packet["revision_id"], symbol=rule["symbol"], quantity=quantity, net_amount=str(net),
            net_adjustment=str(adjustment), posted_adjustment=str(posted), facts=packet, facts_fingerprint=fingerprint(packet),
            supplement_fingerprint=supplement_hash, reviewed_receipts=reviewed, decision_at=now.isoformat(),
            clears_dividend_review_fault=_may_clear_dividend_fault(state, view, action_id, reviewed),
            source_authenticated=False, authority="assumed_offline_fixture_only", executable=False))


@money_context
def refund_event(state, action_id, receipt_id, amount, revision_id, now):
    policy, now, date = _clock(state, now)
    receipt_key = "dividend_cash:" + receipt_id
    previous = state["receipts"].get(receipt_key)
    if previous is not None:
        if previous["event_id"] != action_id or Decimal(previous["cash_amount"]) != -amount or previous.get("revision_id") != revision_id:
            raise AdmissionRejected("conflicting dividend cash receipt identity")
        return None
    rule = next((row for row in policy["events"] if row["event_id"] == action_id), None)
    current = state["dividends"]["revisions"].get(action_id)
    if rule is None or date < rule["pay_date"] or current is None or current["revision_id"] != revision_id:
        raise AdmissionRejected("refund requires the current dividend revision and pay date")
    payable = Decimal(state["dividends"]["payables"].get(action_id, "0"))
    settled = Decimal(state["dividends"]["settled_net"].get(action_id, "0"))
    if amount <= 0 or amount != amount.quantize(Decimal("0.01")) or amount > payable or amount > settled:
        raise AdmissionRejected("refund exceeds the payable or recorded settled amount, or is not positive cents")
    return dict(kind="DIVIDEND_CASH_REFUND", receipt_key=receipt_key, data=dict(event_id=action_id, cash_amount=str(-amount),
        revision_id=revision_id, decision_at=now.isoformat()))
