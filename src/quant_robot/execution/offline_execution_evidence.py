"""Validate synthetic receipt assertions, without authenticating or applying them."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re


def _object(value, fields, name):
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise ValueError("invalid " + name + " fields")


def _text(value, name):
    if not isinstance(value, str) or not 0 < len(value) <= 160 or value != value.strip() or any(ord(c) < 32 for c in value):
        raise ValueError("invalid " + name)


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("invalid evidence hash")


def _time(value, name):
    if not isinstance(value, str) or len(value) > 40 or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", value):
        raise ValueError(name + " requires an ISO timestamp with explicit offset")
    if value.endswith("-00:00"):
        raise ValueError(name + " offset is unknown")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_execution_supplement(path):
    with Path(path).open("rb") as handle:
        payload = handle.read(1_000_001)
    if len(payload) > 1_000_000:
        raise ValueError("execution supplement exceeds byte limit")
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate execution evidence key")
            value[key] = item
        return value
    def invalid_constant(_value):
        raise ValueError("non-finite execution evidence constant")
    try:
        value = json.loads(payload.decode("utf-8-sig"), object_pairs_hook=unique, parse_constant=invalid_constant)
    except RecursionError as exc:
        raise ValueError("execution evidence nesting exceeds supported structure") from exc
    _object(value, "schema_version mode journal records", "supplement")
    return value


def _execution(value, observed, view, order):
    _object(value, "executed_at quantity price quantity_basis price_basis basis_event_id", "execution")
    if value["executed_at"] is not None and _time(value["executed_at"], "executed_at") > observed:
        raise ValueError("execution follows observation")
    quantity, price = value["quantity"], value["price"]
    if quantity is not None and (type(quantity) is not int or not 0 < quantity <= 10**15):
        raise ValueError("invalid execution quantity")
    if price is not None and (not isinstance(price, str) or not re.fullmatch(r"(?:0|[1-9]\d{0,14})(?:\.\d{1,12})?", price) or Decimal(price) <= 0):
        raise ValueError("invalid execution price")
    if value["quantity_basis"] not in ("unknown", "pre_action_shares", "post_action_shares") or value["price_basis"] not in ("unknown", "raw_execution"):
        raise ValueError("invalid execution basis")
    action_id = value["basis_event_id"]
    if value["quantity_basis"] == "unknown":
        if action_id is not None:
            raise ValueError("unknown units cannot assert a basis action")
    else:
        _text(action_id, "basis action")
        rules = (view["policies"]["conversion_policy"] or {}).get("events", [])
        if not any(rule["event_id"] == action_id and rule["symbol"] == order["symbol"] for rule in rules):
            raise ValueError("basis action does not match receipt symbol")


def validate_execution_supplement(packet, view):
    _object(packet, "schema_version mode journal records", "supplement")
    if type(packet["schema_version"]) is not int or packet["schema_version"] != 1 or packet["mode"] != "offline_fixture_only":
        raise ValueError("unsupported execution supplement scope")
    snapshot = view["snapshot"]
    expected = dict(genesis_hash=view["events"][0]["event_hash"], sequence=snapshot["sequence"], hash=snapshot["journal_hash"])
    _object(packet["journal"], "genesis_hash sequence hash", "journal binding")
    if type(packet["journal"]["sequence"]) is not int or packet["journal"] != expected:
        raise ValueError("execution supplement journal binding is stale or different")
    records = packet["records"]
    if not isinstance(records, list) or len(records) > 500:
        raise ValueError("execution supplement exceeds record limit")
    events = {row["sequence"]: row for row in view["events"]}
    by_id, messages, series_revisions, result = {}, set(), set(), []
    for record in records:
        _object(record, "evidence_id receipt operation source observed_at execution", "record")
        evidence_id, receipt, source = record["evidence_id"], record["receipt"], record["source"]
        _text(evidence_id, "evidence identity")
        _object(receipt, "sequence event_hash order_id fill_id", "receipt")
        row = events.get(receipt["sequence"]) if type(receipt["sequence"]) is int else None
        if row is None or row["event"]["kind"] not in {"FILL", "CONVERSION_UNAPPLIED_FILL"} or row["event_hash"] != receipt["event_hash"]:
            raise ValueError("execution supplement receipt binding mismatch")
        original = row["event"]["data"]
        if any(receipt[key] != original[key] for key in ("order_id", "fill_id")):
            raise ValueError("execution supplement receipt identity mismatch")
        _object(source, "source_id series_id message_id revision previous_evidence_id claimed_artifact_sha256", "source")
        for key in ("source_id", "series_id", "message_id"):
            _text(source[key], key)
        if source["claimed_artifact_sha256"] is not None:
            _hash(source["claimed_artifact_sha256"])
        revision = source["revision"]
        if type(revision) is not int or not 0 <= revision < 500:
            raise ValueError("invalid source revision")
        previous = source["previous_evidence_id"]
        if previous is not None:
            _text(previous, "previous evidence identity")
        operation = record["operation"]
        if (revision == 0 and (operation != "execution" or previous is not None)) or (revision > 0 and (operation not in ("correction", "cancel") or previous is None)):
            raise ValueError("invalid revision operation")
        message = (source["source_id"], source["message_id"])
        series_revision = (source["source_id"], source["series_id"], revision)
        if evidence_id in by_id or message in messages or series_revision in series_revisions:
            raise ValueError("duplicate evidence identity or source revision")
        observed = _time(record["observed_at"], "observed_at")
        _execution(record["execution"], observed, view, snapshot["orders"][original["order_id"]])
        by_id[evidence_id] = record; messages.add(message); series_revisions.add(series_revision)
        execution = record["execution"]
        unresolved = [key + "_unknown" for key in ("executed_at", "quantity", "price") if execution[key] is None]
        unresolved += [key + "_unknown" for key in ("quantity_basis", "price_basis") if execution[key] == "unknown"]
        if source["claimed_artifact_sha256"] is None:
            unresolved.append("source_artifact_hash_unknown")
        if revision:
            unresolved.append("revision_requires_source_review")
        differences = [key for key in ("quantity", "price") if execution[key] is not None and Decimal(str(execution[key])) != Decimal(str(original[key]))]
        result.append(dict(assertion=deepcopy(record), recorded_receipt=deepcopy(original),
            recorded_receipt_differences=differences, unresolved=unresolved))
    children = set()
    for record in records:
        source = record["source"]; previous_id = source["previous_evidence_id"]
        if previous_id is None:
            continue
        previous = by_id.get(previous_id)
        if previous is None or previous_id in children or previous["receipt"] != record["receipt"] or any(
                previous["source"][key] != source[key] for key in ("source_id", "series_id")) or previous["source"]["revision"] + 1 != source["revision"]:
            raise ValueError("dangling, forked or mismatched evidence revision")
        if _time(previous["observed_at"], "observed_at") > _time(record["observed_at"], "observed_at"):
            raise ValueError("revision observation precedes its predecessor")
        children.add(previous_id)
    encoded = json.dumps(packet, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(encoded) > 1_000_000:
        raise ValueError("execution supplement exceeds byte limit")
    return dict(schema_version=1, mode="offline_fixture_only", status="assertions_only",
        journal_and_receipt_binding_verified=True, source_authenticated=False, execution_attribution_confirmed=False,
        automatic_correction_allowed=False, clears_faults=False, supplement_fingerprint=hashlib.sha256(encoded).hexdigest(),
        journal=deepcopy(expected), records=result,
        unresolved=["source_authentication_not_performed", "execution_evidence_completeness_not_certified",
            "authoritative_entitlement_and_settlement_evidence"],
        limitations=["asserted artifact hash is not source authentication", "all revisions retained; no automatic latest-wins selection",
            "recorded receipt differences are not correction quantities", "journal recording time is not execution time"])
