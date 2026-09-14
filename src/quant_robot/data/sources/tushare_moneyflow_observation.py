"""Prospective entity-body receipts and one bounded later version check.

This independent entrypoint cannot backfill arbitrary dates, fetch ETF prices,
change historical collection ceilings, or grant research admission.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re

SOURCE_URL = "https://api.tushare.pro"
FIELDS = ["ts_code", "trade_date", "net_mf_amount"]
MAX_ROWS = 6000
MAX_BYTES = 1_000_000
ARCHIVE = Path("data/reports/tushare_moneyflow_forward")
CHINA = timezone(timedelta(hours=8))
COMMON = {"receipt_schema_version": 1, "primary_market": "CN_ETF", "stock_role": "auxiliary_only",
          "research_admission_granted": False, "historical_vintage_verified": False,
          "universe_coverage_verified": False, "new_forward_paper_days": 0}
CAPTURE_SCHEMA_VERSION = 2
CAPTURE_COMMON = {**COMMON, "receipt_schema_version": CAPTURE_SCHEMA_VERSION}


def _utc_now():
    return datetime.now(timezone.utc)


def _new_session():
    import requests
    return requests.Session()


def _clock():
    value = _utc_now()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("receipt clock must be timezone aware")
    return value.astimezone(timezone.utc)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _digest(value):
    return _sha(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def _write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.flush()
        os.fsync(handle.fileno())


def _read(path, limit):
    with path.open("rb") as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("archive byte budget exceeded")
    return raw


def _child(root, name):
    result = (root / name).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError("archive path leaves parent")
    return result


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _contains_secret(value, secret):
    if isinstance(value, str):
        return secret in value
    if isinstance(value, list):
        return any(_contains_secret(item, secret) for item in value)
    if isinstance(value, dict):
        return any(secret in key or _contains_secret(item, secret) for key, item in value.items())
    return False


def _decoded_secret_free(raw, token):
    def reject_constant(_):
        raise ValueError("nonfinite JSON constant")
    value = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=reject_constant,
                       parse_float=Decimal)
    if token.encode() in raw or _contains_secret(value, token):
        raise ValueError("credential echo is not archived")
    return value


def _number_identity(value):
    # Preserve exact JSON decimal differences without context rounding. Numeric
    # spelling such as 12, 12.0 and 1.2e1 must identify the same amount.
    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError("net amount must be finite")
    sign, digits, exponent = number.as_tuple()
    if not any(digits):
        return "0:0:0"
    digits = list(digits)
    while digits[-1] == 0:
        digits.pop()
        exponent += 1
    return f"{sign}:{''.join(map(str, digits))}:{exponent}"


def _receipt_version(value):
    if not isinstance(value, dict):
        raise ValueError("source receipt must be an object")
    version = value.get("receipt_schema_version")
    if type(version) is not int or version not in (1, 2):
        raise ValueError("unsupported source receipt version")
    return version


def parse_moneyflow_payload(parsed, *, trade_date, receipt_schema_version=1):
    """Versioned source shape checks; standalone callers retain v1 semantics."""
    version = _receipt_version({"receipt_schema_version": receipt_schema_version})
    if not re.fullmatch(r"[0-9]{8}", trade_date):
        raise ValueError("invalid source date")
    datetime.strptime(trade_date, "%Y%m%d")
    if not isinstance(parsed, dict) or type(parsed.get("code")) is not int or parsed["code"] != 0:
        raise ValueError("provider response rejected")
    data = parsed.get("data")
    if not isinstance(data, dict):
        raise ValueError("data object missing")
    fields, rows = data.get("fields"), data.get("items")
    if not isinstance(fields, list) or len(fields) != len(FIELDS) or set(fields) != set(FIELDS):
        raise ValueError("moneyflow fields changed")
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise ValueError("moneyflow row budget exceeded")
    if "count" in data:
        if version == 1 and (type(data["count"]) is not int or data["count"] != len(rows)):
            raise ValueError("provider count differs from response")
        if version == 2 and (type(data["count"]) is not int or data["count"] < 0):
            raise ValueError("invalid unverified count metadata")
    if "has_more" in data and type(data["has_more"]) is not bool:
        raise ValueError("invalid pagination metadata")
    canonical, seen, nulls, types = [], set(), 0, {field: set() for field in fields}
    eligible_rows = excluded_bj_rows = 0
    for row in rows:
        if not isinstance(row, list) or len(row) != len(fields):
            raise ValueError("invalid moneyflow row")
        item = dict(zip(fields, row, strict=True))
        symbol, day, value = (item[field] for field in FIELDS)
        eligible = isinstance(symbol, str) and re.fullmatch(r"(?:6[0-9]{5}\.SH|[03][0-9]{5}\.SZ)", symbol)
        excluded_bj = version == 2 and isinstance(symbol, str) and re.fullmatch(r"920[0-9]{3}\.BJ", symbol)
        if not eligible and not excluded_bj:
            raise ValueError("source must be a Shanghai or Shenzhen A share")
        eligible_rows += bool(eligible)
        excluded_bj_rows += bool(excluded_bj)
        if day != trade_date or symbol in seen:
            raise ValueError("source date or unique stock identity failed")
        if value is not None and type(value) not in (int, float, Decimal):
            raise ValueError("net amount must be finite numeric or explicit unknown")
        seen.add(symbol)
        nulls += value is None
        canonical.append([symbol, day, None if value is None else _number_identity(value)])
        for field, scalar in item.items():
            types[field].add("number" if type(scalar) in (int, float, Decimal) else type(scalar).__name__)
    complete_shape = bool(eligible_rows) and not nulls and len(rows) < MAX_ROWS and not data.get("has_more", False)
    summary = {"status": "observed_unqualified" if complete_shape else "incomplete_unqualified",
            "rows": len(rows), "null_net_amount_rows": nulls,
            "row_limit_reached": len(rows) == MAX_ROWS, "provider_has_more": data.get("has_more"),
            "provider_count": data.get("count"), "amount_unit": "CNY_10000",
            "content_sha256": _digest(sorted(canonical)),
            "schema_sha256": _digest({"fields": fields, "scalar_types": {k: sorted(v) for k, v in types.items()}}),
            **COMMON, "receipt_schema_version": version}
    if version == 2:
        # The SDK uses fields/items. The undocumented count is retained as
        # metadata, never interpreted as an empty page or completeness proof.
        summary.update(eligible_source_rows=eligible_rows, excluded_bj_source_rows=excluded_bj_rows,
            projection_universe="SH_SZ_A", excluded_source_universe="BJ_920",
            provider_count_semantics_verified=False,
            provider_count_matches_response_rows=data["count"] == len(rows) if "count" in data else None)
    return summary


def _verified_day(folder):
    result = json.loads(_read(_child(folder, "completion.json"), 32_000))
    version = _receipt_version(result)
    claim_raw = _read(_child(folder, "claim.json"), 16_000)
    if result["local_attempt_date"] != folder.name or result["claim_sha256"] != _sha(claim_raw):
        raise ValueError("daily claim differs from receipt")
    if _receipt_version(json.loads(claim_raw)) != version:
        raise ValueError("daily claim and packet versions differ")
    if not isinstance(result["records"], list) or len(result["records"]) > 2:
        raise ValueError("invalid daily record list")
    seen = set()
    records = {}
    for entry in result["records"]:
        kind = entry["kind"]
        if kind not in {"current", "revision"} or kind in seen:
            raise ValueError("invalid receipt kind")
        seen.add(kind)
        path = _child(folder, kind + ".json")
        raw = _read(path, 24_000)
        if str(path) != entry["record_path"] or _sha(raw) != entry["record_sha256"]:
            raise ValueError("record identity changed")
        record = json.loads(raw)
        if _receipt_version(record) != version:
            raise ValueError("daily record and packet versions differ")
        body_path = _child(folder, kind + ".response.json")
        if record.get("raw_retained"):
            if record["raw_path"] != str(body_path) or _sha(_read(body_path, MAX_BYTES)) != record["raw_sha256"]:
                raise ValueError("source body changed")
        elif body_path.exists():
            raise ValueError("unexpected source body")
        records[kind] = (record, entry)
    return result, records


def _prior_candidate(archive, today):
    for distance in range(1, 8):
        day = today - timedelta(days=distance)
        folder = _child(archive, day.isoformat())
        if not folder.exists():
            continue
        try:
            _, records = _verified_day(folder)
        except (OSError, ValueError, KeyError, TypeError):
            return None, "archive_integrity_failed"
        if "current" not in records:
            continue
        record, entry = records["current"]
        if record["status"] not in {"observed_unqualified", "incomplete_unqualified"}:
            continue
        if record["trade_date"] != day.strftime("%Y%m%d"):
            return None, "archive_integrity_failed"
        claim = _child(_child(archive, "revision_claims"), record["trade_date"] + ".json")
        if not claim.exists():
            return (record, entry), "one_recent_original_selected"
    return None, "no_unchecked_recent_original"


def _capture_slot(folder, *, kind, trade_date, token, original=None, revision_claim=None):
    started = _clock()
    record = {**CAPTURE_COMMON, "kind": kind, "trade_date": trade_date, "api_name": "moneyflow",
              "fields": FIELDS, "status": "source_rejected", "started_at": started.isoformat(),
              "source_published_at": None, "raw_retained": False,
              "body_representation": "requests_decompressed_response_entity_bytes_not_wire_encoding"}
    if original:
        prior, entry = original
        record.update(original_record_path=entry["record_path"], original_record_sha256=entry["record_sha256"],
                      original_raw_sha256=prior["raw_sha256"], original_observed_at=prior["observed_at"])
        record.update(revision_claim_path=str(revision_claim),
                      revision_claim_sha256=_sha(_read(revision_claim, 16_000)))
    try:
        if started.astimezone(CHINA).date().isoformat() != folder.name:
            raise ValueError("capture day changed before request")
        with _new_session() as session:
            session.trust_env = False
            with session.post(SOURCE_URL, json={"api_name": "moneyflow", "token": token,
                    "params": {"trade_date": trade_date}, "fields": ",".join(FIELDS)},
                    timeout=(10, 20), stream=True, allow_redirects=False, verify=True) as response:
                record["http_status"] = response.status_code
                if response.status_code != 200:
                    raise ValueError("HTTP status rejected")
                body = bytearray()
                for chunk in response.iter_content(65536):
                    body.extend(chunk)
                    if len(body) > MAX_BYTES:
                        raise ValueError("source body exceeds byte budget")
        received = _clock()
        if received < started:
            raise ValueError("receipt clock moved backwards")
        record.update(observed_at=received.isoformat(), raw_sha256=_sha(body), raw_bytes=len(body))
        parsed = _decoded_secret_free(bytes(body), token)
        raw_path = _child(folder, kind + ".response.json")
        with raw_path.open("xb") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        record.update(raw_retained=True, raw_path=str(raw_path))
        record.update(parse_moneyflow_payload(parsed, trade_date=trade_date,
                                             receipt_schema_version=CAPTURE_SCHEMA_VERSION))
        if original:
            record["content_changed_since_original"] = record["content_sha256"] != original[0]["content_sha256"]
    except Exception as exc:
        # Tokens or arbitrary provider/transport messages must never reach disk.
        record.update(status="source_rejected", failure_kind=type(exc).__name__)
    record["finished_at"] = _clock().isoformat()
    path = _child(folder, kind + ".json")
    _write_json(path, record)
    return record, {"kind": kind, "record_path": str(path), "record_sha256": _sha(path.read_bytes())}


def capture_moneyflow_observation(*, repo_root, run_gate, get_token, execute=False):
    """Preview by default; current-day capture plus at most one prior-date check.

    The caller supplies the fresh project gate and existing-secret reader. A
    weekday clock is an attempt window, not proof that the exchange was open.
    """
    started = _clock()
    local = started.astimezone(CHINA)
    due = local.weekday() < 5 and (local.hour, local.minute) >= (19, 5)
    if not execute:
        return {**CAPTURE_COMMON, "status": "preview", "due": due, "api_name": "moneyflow",
                "maximum_requests_per_local_day": 2, "maximum_response_bytes": MAX_BYTES,
                "maximum_rows": MAX_ROWS, "prior_lookback_calendar_days": 7,
                "each_prior_date_maximum_checks": 1, "fields": FIELDS}
    if not due:
        return {**CAPTURE_COMMON, "status": "not_due"}
    root = Path(repo_root).resolve()
    archive = _child(root, ARCHIVE)
    folder = _child(archive, local.date().isoformat())
    completion = _child(folder, "completion.json")
    if folder.exists():
        try:
            result, _ = _verified_day(folder)
        except FileNotFoundError:
            return {**CAPTURE_COMMON, "status": "attempt_incomplete", "result_path": str(completion)}
        except (OSError, ValueError, KeyError, TypeError):
            return {**CAPTURE_COMMON, "status": "archive_integrity_failed", "result_path": str(completion)}
        return {**CAPTURE_COMMON, "receipt_schema_version": result["receipt_schema_version"],
                "status": "already_attempted", "previous_status": result["status"],
                "result_path": str(completion)}
    folder.parent.mkdir(parents=True, exist_ok=True)
    try:
        folder.mkdir()
    except FileExistsError:
        return {**CAPTURE_COMMON, "status": "attempt_incomplete", "result_path": str(completion)}
    claim = {**CAPTURE_COMMON, "local_attempt_date": local.date().isoformat(), "started_at": started.isoformat(),
             "collector_sha256": _sha(Path(__file__).read_bytes()), "maximum_requests": 2,
             "purpose": "prospective_source_receipts_only", "fields": FIELDS, "api_name": "moneyflow"}
    claim_path = _child(folder, "claim.json")
    _write_json(claim_path, claim)
    result = {**claim, "claim_sha256": _sha(claim_path.read_bytes()), "status": "source_review_required",
              "result_path": str(completion), "records": [], "requests_started": 0,
              "prior_review_status": "not_attempted"}
    try:
        gate = run_gate(_child(folder, "startup_gate"))
        _write_json(_child(folder, "gate.json"), gate)
        if gate.get("status") != "ready" or gate.get("primary_market") != "CN_ETF" or gate.get("blockers") != []:
            result["status"] = "gate_blocked"
        else:
            try:
                token = get_token()
                if not isinstance(token, str) or not token.strip():
                    raise ValueError("existing token missing")
            except Exception:
                result["status"] = "credential_missing"
            else:
                prior, result["prior_review_status"] = _prior_candidate(archive, local.date())
                result["requests_started"] += 1
                current, entry = _capture_slot(folder, kind="current", trade_date=local.strftime("%Y%m%d"), token=token)
                result["records"].append(entry)
                statuses = [current["status"]]
                if prior and current["status"] != "source_rejected":
                    claims = _child(archive, "revision_claims")
                    claims.mkdir(exist_ok=True)
                    revision_claim = _child(claims, prior[0]["trade_date"] + ".json")
                    try:
                        _write_json(revision_claim, {"original_record_sha256": prior[1]["record_sha256"],
                            "check_local_date": local.date().isoformat(), "claimed_at": _clock().isoformat()})
                    except FileExistsError:
                        result["prior_review_status"] = "prior_check_already_claimed"
                    else:
                        result["requests_started"] += 1
                        revision, entry = _capture_slot(folder, kind="revision", trade_date=prior[0]["trade_date"],
                                                        token=token, original=prior, revision_claim=revision_claim)
                        result["records"].append(entry)
                        statuses.append(revision["status"])
                if all(status == "observed_unqualified" for status in statuses) and result["prior_review_status"] != "archive_integrity_failed":
                    result["status"] = "observed_unqualified"
    except Exception as exc:
        result["failure_kind"] = type(exc).__name__
    result["finished_at"] = _clock().isoformat()
    _write_json(completion, result)
    return result
