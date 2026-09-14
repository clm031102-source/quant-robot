"""Bounded decision-cutoff reviews of explicitly pinned source receipts."""
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from quant_robot.data.sources.tushare_moneyflow_observation import (
    ARCHIVE, CHINA, COMMON, FIELDS, MAX_BYTES, parse_moneyflow_payload,
)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read(path, limit):
    with Path(path).open("rb") as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("source byte budget exceeded")
    return raw


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _json(raw):
    def reject_constant(_):
        raise ValueError("nonfinite JSON constant")
    return json.loads(raw, object_pairs_hook=_object, parse_float=Decimal, parse_constant=reject_constant)


def _time(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be an explicit string")
    instant = datetime.fromisoformat(value)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("timezone-aware decision and source clocks required")
    return instant.astimezone(timezone.utc)


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{8}", value):
        raise ValueError("trade dates require YYYYMMDD")
    return datetime.strptime(value, "%Y%m%d").date()


def _source_contract(value):
    if not isinstance(value, dict):
        raise ValueError("source record must be an object")
    for key, expected in COMMON.items():
        if type(value.get(key)) is not type(expected) or value[key] != expected:
            raise ValueError("source receipt contract changed")
    if value.get("api_name") != "moneyflow" or value.get("fields") != FIELDS:
        raise ValueError("source API or fields changed")


def _path(root, value):
    if not isinstance(value, str) or not value:
        raise ValueError("source path required")
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError("source path leaves archive")
    return path


def _pinned(path, expected, limit):
    if not isinstance(expected, str) or not re.fullmatch("[0-9a-f]{64}", expected):
        raise ValueError("source fingerprint required")
    raw = _read(path, limit)
    if _sha(raw) != expected:
        raise ValueError("source fingerprint changed")
    return raw


def _contract(manifest, root):
    keys = {"schema_version", "purpose", "as_of", "trade_dates", "symbols", "receipts"}
    if not isinstance(manifest, dict) or set(manifest) != keys:
        raise ValueError("invalid source review manifest")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise ValueError("unsupported review manifest version")
    if manifest["purpose"] != "moneyflow_asof_source_review":
        raise ValueError("manifest is not a source-only review")
    cutoff = _time(manifest["as_of"])
    days, symbols, receipts = (manifest[k] for k in ("trade_dates", "symbols", "receipts"))
    if not isinstance(days, list) or not 1 <= len(days) <= 31 or len(set(days)) != len(days):
        raise ValueError("require 1 to 31 unique trade dates")
    if any(_day(day) > cutoff.astimezone(CHINA).date() for day in days):
        raise ValueError("requested trade date is after decision cutoff")
    if not isinstance(symbols, list) or not 1 <= len(symbols) <= 1000 or len(set(symbols)) != len(symbols):
        raise ValueError("require 1 to 1000 unique stocks")
    if any(not isinstance(s, str) or not re.fullmatch(r"(?:6[0-9]{5}\.SH|[03][0-9]{5}\.SZ)", s) for s in symbols):
        raise ValueError("requested identities must be Shanghai or Shenzhen A shares")
    if not isinstance(receipts, list) or not 1 <= len(receipts) <= 64:
        raise ValueError("require 1 to 64 explicit receipt packets")
    archive = _path(root, str(ARCHIVE))
    paths, packets = set(), []
    for entry in receipts:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise ValueError("invalid receipt manifest entry")
        path = _path(root, entry["path"])
        if not path.is_relative_to(archive) or path in paths:
            raise ValueError("duplicate or unrelated source path")
        parts = path.relative_to(archive).parts
        if len(parts) != 2 or parts[1] != "completion.json" or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", parts[0]):
            raise ValueError("require a dated moneyflow completion packet")
        date.fromisoformat(parts[0])
        paths.add(path); packets.append((path, entry["sha256"]))
    return cutoff, archive, sorted(days), sorted(symbols), packets


def _metadata(packets, cutoff):
    records, future = {}, 0
    for path, digest in packets:
        packet = _json(_pinned(path, digest, 32_000))
        _source_contract(packet)
        folder = path.parent
        if packet["local_attempt_date"] != folder.name or packet["purpose"] != "prospective_source_receipts_only":
            raise ValueError("packet date or purpose changed")
        finish, start = _time(packet["finished_at"]), _time(packet["started_at"])
        if start > finish or start.astimezone(CHINA).date().isoformat() != folder.name:
            raise ValueError("packet clocks inconsistent")
        if finish > cutoff:
            future += 1
            continue  # Future values and record bodies are not opened.
        claim = _json(_pinned(_path(folder, "claim.json"), packet["claim_sha256"], 16_000))
        _source_contract(claim)
        if (claim["started_at"] != packet["started_at"] or claim["local_attempt_date"] != folder.name
                or claim["purpose"] != packet["purpose"] or claim["maximum_requests"] != 2):
            raise ValueError("daily claim differs from packet")
        entries = packet["records"]
        if not isinstance(entries, list) or len(entries) > 2:
            raise ValueError("source packet record budget exceeded")
        if (type(packet.get("requests_started")) is not int or not 0 <= packet["requests_started"] <= 2
                or len(entries) != packet["requests_started"]):
            raise ValueError("packet has an unaccounted source request")
        if packet.get("status") not in {"observed_unqualified", "source_review_required", "gate_blocked", "credential_missing"}:
            raise ValueError("source packet status invalid")
        kinds = set()
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"kind", "record_path", "record_sha256"}:
                raise ValueError("invalid receipt reference")
            kind = entry["kind"]
            if kind not in {"current", "revision"} or kind in kinds:
                raise ValueError("duplicate or invalid receipt kind")
            kinds.add(kind)
            record_path = _path(folder, kind + ".json")
            if _path(folder, entry["record_path"]) != record_path:
                raise ValueError("receipt reference leaves its fixed path")
            record = _json(_pinned(record_path, entry["record_sha256"], 24_000))
            _source_contract(record)
            if record["kind"] != kind or record["status"] not in {"observed_unqualified", "incomplete_unqualified", "source_rejected"}:
                raise ValueError("invalid source status or kind")
            day = _day(record["trade_date"])
            distance = (date.fromisoformat(folder.name) - day).days
            if (kind == "current" and distance != 0) or (kind == "revision" and not 1 <= distance <= 7):
                raise ValueError("receipt date outside collector scope")
            request_start, request_finish = _time(record["started_at"]), _time(record["finished_at"])
            if not start <= request_start <= request_finish <= finish:
                raise ValueError("request completion clock inconsistent")
            observed = _time(record["observed_at"]) if "observed_at" in record else None
            if observed is not None and not request_start <= observed <= request_finish:
                raise ValueError("receipt clock inconsistent")
            if record["status"] != "source_rejected" and observed is None:
                raise ValueError("parsed source has no receipt clock")
            records[str(record_path)] = {"record": record, "path": record_path, "sha256": entry["record_sha256"],
                                         "packet_path": path, "packet_sha256": digest, "packet_finish": finish,
                                         "observed": observed, "request_start": request_start}
    return records, future


def _revision_link(item, records, archive):
    record = item["record"]
    if record["kind"] != "revision":
        return
    original_path = str(_path(archive, record["original_record_path"]))
    original = records.get(original_path)
    if original is None:
        raise ValueError("original receipt must be explicitly supplied and visible")
    prior = original["record"]
    if (prior["kind"] != "current" or prior["status"] == "source_rejected"
            or prior["trade_date"] != record["trade_date"] or original["sha256"] != record["original_record_sha256"]
            or prior["raw_sha256"] != record["original_raw_sha256"]
            or prior["observed_at"] != record["original_observed_at"]
            or original["packet_finish"] > item["request_start"]):
        raise ValueError("original version linkage inconsistent")
    expected = _path(archive, "revision_claims/" + record["trade_date"] + ".json")
    if _path(archive, record["revision_claim_path"]) != expected:
        raise ValueError("revision claim path changed")
    claim = _json(_pinned(expected, record["revision_claim_sha256"], 16_000))
    if (claim["original_record_sha256"] != original["sha256"]
            or claim["check_local_date"] != item["path"].parent.name
            or not original["packet_finish"] <= _time(claim["claimed_at"]) <= item["request_start"]):
        raise ValueError("revision claim inconsistent")


def _source_values(item, symbols):
    record, folder = item["record"], item["path"].parent
    if type(record.get("raw_retained")) is not bool:
        raise ValueError("raw retention status missing")
    body_path = _path(folder, record["kind"] + ".response.json")
    if not record["raw_retained"]:
        if record["status"] != "source_rejected" or body_path.exists():
            raise ValueError("source raw retention inconsistent")
        return None, 0
    if _path(folder, record["raw_path"]) != body_path:
        raise ValueError("source body path changed")
    raw = _pinned(body_path, record["raw_sha256"], MAX_BYTES)
    if record["raw_bytes"] != len(raw):
        raise ValueError("source body size changed")
    if record["status"] == "source_rejected":
        return None, len(raw)
    parsed = _json(raw)
    summary = parse_moneyflow_payload(parsed, trade_date=record["trade_date"])
    for key, value in summary.items():
        if key not in record or type(record[key]) is not type(value) or record[key] != value:
            raise ValueError("recorded source summary differs from original body")
    values = {}
    for row in parsed["data"]["items"]:
        value = dict(zip(parsed["data"]["fields"], row, strict=True))
        if value["ts_code"] in symbols:
            values[value["ts_code"]] = None if value["net_mf_amount"] is None else str(value["net_mf_amount"])
    return values, len(raw)


def _review(manifest, root):
    cutoff, archive, days, symbols, packets = _contract(manifest, root)
    records, future = _metadata(packets, cutoff)
    candidates, failed, body_bytes, ignored = {day: [] for day in days}, [], 0, 0
    for item in records.values():
        record = item["record"]
        if record["trade_date"] not in candidates:
            ignored += 1
            continue
        _revision_link(item, records, archive)
        values, size = _source_values(item, set(symbols))
        body_bytes += size
        if body_bytes > 64_000_000:
            raise ValueError("source review total byte budget exceeded")
        if values is None:
            failed.append({"trade_date": record["trade_date"], "record_path": str(item["path"]), "status": record["status"]})
        else:
            item["values"] = values
            candidates[record["trade_date"]].append(item)
    cells, selected = [], []
    for day, versions in candidates.items():
        chosen = None
        state = "no_visible_version"
        if versions:
            latest = max(v["observed"] for v in versions)
            ties = [v for v in versions if v["observed"] == latest]
            if len({(v["record"]["content_sha256"], v["record"]["status"]) for v in ties}) > 1:
                state = "conflicting_receipt_time"
            else:
                chosen = sorted(ties, key=lambda v: (v["packet_finish"], str(v["path"])))[-1]
                selected.append({"trade_date": day, "record_path": str(chosen["path"]),
                    "record_sha256": chosen["sha256"], "raw_sha256": chosen["record"]["raw_sha256"],
                    "observed_at": chosen["observed"].isoformat(), "packet_completed_at": chosen["packet_finish"].isoformat(),
                    "source_status": chosen["record"]["status"], "equivalent_latest_receipts": len(ties)})
        for symbol in symbols:
            value = None
            if chosen is not None:
                if symbol not in chosen["values"]:
                    state = "absent_from_response"
                elif chosen["values"][symbol] is None:
                    state = "explicit_null"
                else:
                    state, value = "observed_numeric", chosen["values"][symbol]
            cells.append({"trade_date": day, "symbol": symbol, "state": state, "net_mf_amount": value})
    blockers = []
    if any(c["state"] != "observed_numeric" for c in cells):
        blockers.append("requested_cells_unknown")
    if any(v["source_status"] != "observed_unqualified" for v in selected):
        blockers.append("source_response_incomplete")
    if failed:
        blockers.append("visible_source_request_failed")
    return {"schema_version": 1, "stage": "moneyflow_asof_source_review", "status": "source_review_complete",
            "manifest_sha256": _sha(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()),
            "as_of": cutoff.isoformat(), "amount_unit": "CNY_10000", "cells": cells,
            "selected_versions": selected, "future_packets_skipped": future,
            "nonrequested_records_not_parsed": ignored, "failed_visible_requests": len(failed),
            "failed_request_evidence": failed, "source_body_bytes_read": body_bytes,
            "observed_numeric_cells": sum(c["state"] == "observed_numeric" for c in cells),
            "unknown_cells": sum(c["state"] != "observed_numeric" for c in cells),
            "source_selection_complete": not blockers, "source_review_blockers": blockers,
            "receipt_chain_verified": True, "observation_clock": "collector_local_clock_not_third_party_certified",
            "research_admission_granted": False, "historical_vintage_verified": False,
            "universe_coverage_verified": False, "new_forward_paper_days": 0}


def read_moneyflow_asof(manifest, *, repo_root):
    """Read only pinned, visible source values; no source or research admission."""
    try:
        return _review(manifest, Path(repo_root).resolve())
    except (OSError, KeyError, TypeError, OverflowError, RecursionError) as exc:
        raise ValueError("source archive or manifest is invalid: " + type(exc).__name__) from None
