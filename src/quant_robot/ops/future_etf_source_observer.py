"""Finite, future-only source observation. No candidate, account or signal authority.

Production has no injectable transport/clock/token. The separately named synthetic
route permanently labels all evidence artificial, even for calendar-shaped dates.
No release/config is shipped with this implementation.
"""
from __future__ import annotations

from datetime import date, datetime, time as day_time, timedelta, timezone
from hashlib import sha256
import ast
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import ssl
import sys
import time

from quant_robot.ops import tushare_fund_daily_batch as transport
from quant_robot.ops import tushare_fund_daily_wire as wire

MODE = "finite_future_etf_source_observation_only"
CLOSED_MODE = "future_etf_source_observation_unadmitted"
BRANCH = "codex/data-pipeline-future-etf-observation-20261107"
CONFIG = "configs/future_etf_source_observer_admission.json"
# One project-wide namespace, including across worktrees and replacement releases.
PRODUCTION_LEDGER = Path("F:/lhjqr/data/reports/future_etf_source_observer")
CHINA = timezone(timedelta(hours=8))
CAMPAIGN_END = "2026-11-09T16:21:39+00:00"
LIMITS = {"sessions": 20, "posts_per_symbol_day": 1, "response_bytes": 262144,
          "worker_seconds": 40, "pair_seconds": 150, "retry": 0, "redirect": 0}
CONTEXT = {"machine": "office_desktop", "task": "data_pipeline", "branch": BRANCH}
ARTIFICIAL = "synthetic_only_not_source_evidence"
SOURCE = "future_source_observation_only"
CODE_FILES = ("src/quant_robot/ops/future_etf_source_observer.py",
              "scripts/run_future_etf_source_observer.py",
              "src/quant_robot/ops/tushare_fund_daily_batch.py",
              "src/quant_robot/ops/tushare_fund_daily_wire.py",
              "src/quant_robot/ops/paper_evidence_session.py",
              "scripts/run_quant_pm_startup_gate.py", "scripts/bootstrap.py", "scripts/start_task_context.py")


class ObservationError(ValueError):
    """Static error codes only; never include provider/credential contents."""


def require(ok, code):
    if not ok:
        raise ObservationError(code)


def utc_now():
    return datetime.now(timezone.utc)


def instant(value):
    require(type(value) is str, "clock_type")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ObservationError("clock_format") from None
    require(result.tzinfo is not None and result.utcoffset() == timedelta(0), "UTC_clock_required")
    return result


def iso_day(value):
    require(type(value) is str, "date_type")
    try:
        result = date.fromisoformat(value)
    except ValueError:
        raise ObservationError("date_format") from None
    require(result.isoformat() == value, "ISO_date_required")
    return result


def _decode(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, "duplicate_metadata_key")
            out[key] = value
        return out
    def nonfinite(_):
        raise ObservationError("nonfinite_metadata")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _bound(ref):
    return transport._bound(ref)


def implementation(root):
    # Lazy import avoids changing the actual-PM early-return path's read set.
    from quant_robot.ops.paper_evidence_session import _PM_FILES
    root = Path(root).resolve()
    # Pin the local static import closure as well as the explicit PM read catalogue.
    # Dynamic external dependencies remain named environment versions, not project files.
    pending, seen = list(set(CODE_FILES) | set(_PM_FILES)), set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        tree = ast.parse((root/name).read_text(encoding="utf-8"))
        modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                modules.append(node.module)
                modules.extend(node.module+"."+a.name for a in node.names)
        for module in modules:
            if module.startswith("quant_robot") or module.startswith("scripts."):
                prefix = "src/" if module.startswith("quant_robot") else ""
                parts = module.split(".")
                for length in range(1, len(parts)+1):
                    stem = prefix+"/".join(parts[:length])
                    for candidate in (stem+".py", stem+"/__init__.py"):
                        if (root/candidate).is_file() and candidate not in seen:
                            pending.append(candidate)
    files = sorted(seen)
    return {"python": platform.python_version(), "openssl": ssl.OPENSSL_VERSION,
            "optimize": sys.flags.optimize,
            "executable": transport.reference(sys.executable),
            "dependencies": {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "pydantic")},
            "code": {name: transport.reference(root/name) for name in files}}


def validate_plan(plan, calendar):
    """Only metadata. Calendar dates are explicit; weekdays are never inferred."""
    require(plan.get("artifact_type") == "finite_future_etf_observer_scope_v1"
            and plan.get("purpose") == SOURCE and plan.get("limits") == LIMITS,
            "fixed_source_plan_required")
    require(plan.get("context") == CONTEXT and plan.get("symbols") == list(wire.SYMBOLS)
            and plan.get("api") == wire.API and plan.get("fields") == ",".join(wire.FIELDS),
            "fixed_source_identity_required")
    require(plan.get("financial_decode_allowed") is False and plan.get("qualified") is False
            and plan.get("real_forward") == 0, "source_only_required")
    created, expires = instant(plan["created_at"]), instant(plan["expires_at"])
    slots = plan["slots"]
    require(type(slots) is list and 1 <= len(slots) <= LIMITS["sessions"], "finite_slots_required")
    days = [s["date"] for s in slots]
    require(days == sorted(set(days)), "ordered_unique_days_required")
    require(calendar.get("timezone") == "Asia/Shanghai"
            and type(calendar.get("session_rows")) is list, "explicit_exchange_calendar_required")
    rows = calendar["session_rows"]
    calendar_days = [r["date"] for r in rows]
    require(calendar_days == sorted(set(calendar_days)), "calendar_dates_invalid")
    for d in calendar_days:
        iso_day(d)
    require(days == [d for d in calendar_days if days[0] <= d <= days[-1]], "calendar_gap_or_non_session")
    require(created < expires <= created+timedelta(days=45), "finite_expiry_required")
    require(plan["request_budget"] == 2*len(days)
            and plan["body_byte_budget"] == 2*len(days)*LIMITS["response_bytes"], "exact_budget_required")
    if plan["authority_kind"] == "campaign_72h":
        require(expires <= instant(CAMPAIGN_END) and days == ["2026-11-09"], "campaign_does_not_authorize_later_dates")
    else:
        require(plan["authority_kind"] == "separately_authorized_finite", "finite_authority_kind_required")
    by_day = {r["date"]: r for r in rows}
    for slot in slots:
        require(set(slot) == {"date", "not_before", "deadline"}, "slot_schema")
        d = iso_day(slot["date"])
        start, end = instant(slot["not_before"]), instant(slot["deadline"])
        midnight = datetime.combine(d, day_time(), CHINA).astimezone(timezone.utc)
        earliest = datetime.combine(d, day_time(15, 30), CHINA).astimezone(timezone.utc)
        require(created < midnight and earliest <= start < end <= midnight+timedelta(days=1)
                and end-start <= timedelta(hours=4) and end <= expires, "future_same_day_slot_required")
        row = by_day[slot["date"]]
        require("SSE" in row.get("exchange_codes", [])
                and start >= instant(row["daily_observation_not_before_utc"]), "calendar_observation_clock_required")
    return days


def _protocol_refs(root):
    names = {"configs/quant_pm_startup_gate_cn_etf.json", "configs/workstations.json", "pyproject.toml"}
    config = _decode((root/"configs/quant_pm_startup_gate_cn_etf.json").read_bytes())
    names.add(config.get("research_family_config", "configs/research_family_scheduler_cn_etf.json"))
    names.update(row["path"] for row in config["required_reading"])
    refs = []
    for name in sorted(names):
        path = (root/name).resolve()
        require(path.is_relative_to(root), "protocol_path_outside_repository")
        refs.append(transport.reference(path))
    return refs


def load_authority(root):
    """No gate, claim, credential or HTTP. Missing release fails closed."""
    root = Path(root).resolve()
    config_ref = transport.reference(root/CONFIG)
    admission = _decode(_bound(config_ref))
    require(set(admission) == {"artifact_type", "scope", "root_review", "manager_review"}
            and admission["artifact_type"] == "future_etf_source_release_v1", "release_schema")
    scope_ref = admission["scope"]
    plan = _decode(_bound(scope_ref))
    calendar = _decode(_bound(plan["calendar"]))
    days = validate_plan(plan, calendar)
    require(plan["implementation"] == implementation(root) and sys.flags.optimize == 0,
            "implementation_or_runtime_changed")
    require(Path(__file__).resolve() == root/CODE_FILES[0], "imported_module_root_mismatch")
    require(transport._git(root, "branch", "--show-current") == BRANCH
            and transport._git(root, "rev-parse", "HEAD") == plan["head"], "branch_or_HEAD_changed")
    require(Path(plan["ledger_directory"]).resolve() == PRODUCTION_LEDGER.resolve(), "fixed_project_ledger_required")
    require(plan["protocol_bindings"] == _protocol_refs(root), "protocol_raw_bytes_changed")
    refs = [config_ref, scope_ref, plan["calendar"], *plan["protocol_bindings"],
            *plan["bindings"], plan["implementation"]["executable"], *plan["implementation"]["code"].values()]
    require(plan["bindings"], "source_contract_bindings_required")
    first_day = datetime.combine(iso_day(days[0]), day_time(), CHINA).astimezone(timezone.utc)
    review_paths = set()
    for role in ("root_review", "manager_review"):
        ref = admission[role]
        review_paths.add(Path(ref["path"]).resolve())
        review = _decode(_bound(ref))
        require(review.get("artifact_type") == "future_etf_source_exact_review_v1"
                and review.get("reviewer") == role.removesuffix("_review")
                and review.get("status") == "accepted_exact_source_observation"
                and review.get("scope_sha256") == scope_ref["sha256"]
                and review.get("implementation_sha256") == _digest(plan["implementation"])
                and review.get("authority_kind") == plan["authority_kind"]
                and review.get("dates") == days and review.get("request_budget") == plan["request_budget"]
                and review.get("expires_at") == plan["expires_at"]
                and review.get("source_only") is True
                and instant(plan["created_at"]) <= instant(review["accepted_at"]) < first_day,
                "exact_dual_review_required")
        refs.append(ref)
    require(len(review_paths) == 2, "independent_review_paths_required")
    transport._verify(refs)
    require(instant(plan["created_at"]) <= utc_now() < instant(plan["expires_at"]), "release_not_current")
    return plan, scope_ref, refs


def future_source_observation_scope(task, family, schedule, *, root=None, branch=None):
    # This branch guard must precede ANY filesystem access, including exists().
    if task != "data_pipeline" or branch != BRANCH:
        return None
    try:
        plan, ref, _ = load_authority(root)
        return {"mode": MODE, "scope": {"scope_sha256": ref["sha256"], "dates": [s["date"] for s in plan["slots"]],
                 "request_budget": plan["request_budget"], "qualified": False, "real_forward": 0}}
    except (Exception, SystemExit):
        return {"mode": CLOSED_MODE, "scope": {}}


def _slot(plan, day, now):
    require(now.tzinfo is not None, "aware_clock_required")
    require(now.astimezone(CHINA).date() == iso_day(day), "no_historical_or_backfill_day")
    slots = [s for s in plan["slots"] if s["date"] == day]
    require(len(slots) == 1, "day_not_authorized")
    slot = slots[0]
    require(instant(slot["not_before"]) <= now < instant(slot["deadline"])
            and now < instant(plan["expires_at"]), "outside_observation_slot")
    return slot


def _request(symbol, day):
    return {"id": symbol.replace(".", "_"), "role": "future_daily_"+symbol[:6],
            "endpoint": wire.URL, "method": "POST", "api_name": wire.API,
            "params": {"ts_code": symbol, "trade_date": day.replace("-", "")},
            "fields": ",".join(wire.FIELDS), "expected_trade_dates": [day.replace("-", "")], "expected_rows": 1}


def _idle(ledger):
    """A crashed prior invocation cannot silently turn into a new day's permission."""
    ledger = Path(ledger)
    require(not (ledger/"halt.json").exists(), "unconfirmed_worker_requires_external_recovery_review")
    if not ledger.exists():
        return
    for child in ledger.iterdir():
        if not child.is_dir():
            continue
        try:
            iso_day(child.name)
        except ObservationError:
            continue
        # Only small, saved metadata is read, never historical response bodies.
        require((child/"claim.json").is_file() and (child/"outcome.json").is_file(),
                "prior_day_incomplete_requires_external_recovery_review")
        with (child/"outcome.json").open("rb") as stream:
            raw = stream.read(2_000_001)
        require(len(raw) <= 2_000_000, "prior_day_metadata_size")
        prior = _decode(raw)
        require(prior.get("date") == child.name and prior.get("worker_exit_all_confirmed") is True
                and prior.get("status") in ("completed_structure_only", "failed_consumed"),
                "prior_day_state_requires_external_recovery_review")
        require(Path(prior["claim"]["path"]).resolve() == (child/"claim.json").resolve(), "prior_claim_identity")
        _bound(prior["claim"])


def _pair(plan, day, ledger, refs, scope_sha, *, clock, token_loader, exchange, evidence_class, guard):
    """Durable once-per-day pair; failure consumes this day, never resumes a leg."""
    slot = _slot(plan, day, clock())
    _idle(ledger)
    folder = Path(ledger)/day
    folder.mkdir(parents=True, exist_ok=False)
    claim = transport._save(folder/"claim.json", {"at": clock().isoformat(), "date": day,
        "scope_sha256": scope_sha, "evidence_class": evidence_class, "symbols": list(wire.SYMBOLS),
        "request_budget": 2, "exposure": "reserved_not_yet_confirmed", "retry_allowed": False})
    refs = [*refs, claim]
    receipts, request_claims = [], []
    deadline = time.monotonic()+LIMITS["pair_seconds"]
    failure, token, pending, worker_unknown = None, None, False, False
    exact_attempts = exact_bytes = True
    attempts = received = lower_attempts = lower_bytes = 0
    try:
        guard(); transport._verify(refs); _slot(plan, day, clock())
        token = token_loader()
        require(type(token) is str and 1 <= len(token) <= 4096 and token == token.strip(), "credential_unavailable")
        for symbol in wire.SYMBOLS:
            guard(); transport._verify(refs); _slot(plan, day, clock())
            remaining = min(deadline-time.monotonic(), (instant(slot["deadline"])-clock()).total_seconds())
            require(remaining > 0, "pair_deadline")
            request = _request(symbol, day)
            directory = folder/request["id"]
            directory.mkdir(exist_ok=False)
            request_claim = transport._save(directory/"claim.json", {"at": clock().isoformat(),
                "request": request, "pair_claim": claim, "exposure": "reserved_not_yet_confirmed"})
            refs.append(request_claim); request_claims.append(request_claim)
            pending = True
            response = exchange(request, token, min(remaining, LIMITS["worker_seconds"]))
            pending = False
            exited = response.get("worker_exit_confirmed") is True
            worker_unknown |= not exited
            # Unknown worker exit cannot establish a final zero or safe body.
            count = response.get("attempts_started") if exited else None
            size = response.get("received_bytes") if exited else None
            exact_attempts &= count is not None; exact_bytes &= size is not None
            attempts += count or 0; received += size or 0
            lower_attempts += response.get("attempts_started_lower_bound", 0)
            lower_bytes += response.get("received_bytes_lower_bound", 0)
            raw_ref, structure, safety_rejected, retained_at = None, None, False, None
            error = response.get("error") if exited else "worker_termination_unconfirmed"
            raw = response.get("body") if exited else None
            if type(raw) is bytes and raw:
                try:
                    wire.decode_opaque(raw, token=token)
                except wire.WireError:
                    safety_rejected = True
                    error = error or "raw_not_retained_due_safety_screen"
                else:
                    raw_ref = transport._save(directory/"response.entity.json", raw, raw=True)
                    retained_at = clock().isoformat()
                    refs.append(raw_ref)
                    if not error and response.get("body_complete") is True:
                        try:
                            structure = wire.inspect_structure(raw, request, token=token)
                        except wire.WireError as exc:
                            error = exc.code
            if not structure:
                error = error or "complete_structure_required"
            start = response.get("request_started_at")
            headers_at = response.get("headers_received_at")
            body_at = response.get("body_completed_at")
            clock_valid = False
            if structure:
                require(count == 1 and size == len(raw) <= LIMITS["response_bytes"], "transport_count_mismatch")
                try:
                    clock_valid = (instant(slot["not_before"]) <= instant(start) <= instant(headers_at)
                                   <= instant(body_at) <= instant(retained_at) <= clock() < instant(slot["deadline"]))
                except ObservationError:
                    clock_valid = False
                if not clock_valid:
                    error = "response_clock_unknown_out_of_order_or_outside_slot"
            exposure = ("complete_raw_structure_observed" if structure and clock_valid and not error else
                        "partial_or_unvalidated_raw_observed" if raw_ref else
                        "possible_exposure_unknown" if count is None or count else "no_request_confirmed")
            receipt = {"artifact_type": "future_etf_observation_receipt_v1", "evidence_class": evidence_class,
                "date": day, "symbol": symbol, "request_claim": request_claim, "raw": raw_ref,
                "request_started_at": start, "headers_received_at": headers_at,
                "body_completed_at": body_at, "retained_at": retained_at,
                "http_status": response.get("http_status"), "headers": response.get("headers", {}),
                "failed_at": response.get("failed_at"),
                "originals_not_retained_due_safety_screen": safety_rejected,
                "worker_exit_confirmed": exited, "body_complete": response.get("body_complete") is True and exited,
                "attempts_started": count, "attempts_started_lower_bound": response.get("attempts_started_lower_bound", 0),
                "received_bytes": size, "received_bytes_lower_bound": response.get("received_bytes_lower_bound", 0),
                "exposure": exposure, "structure": structure, "clock_valid": clock_valid, "error": error,
                "financial_numeric_values_decoded": False, "qualified": False, "real_forward": 0}
            receipt_ref = transport._save(directory/"receipt.json", receipt)
            refs.append(receipt_ref)
            receipts.append({"symbol": symbol, "receipt": receipt_ref, "raw": raw_ref,
                             "complete": not error and clock_valid and structure is not None})
            guard(); transport._verify(refs); _slot(plan, day, clock())
            require(time.monotonic() <= deadline, "pair_deadline")
            require(not error, error or "capture_failed")
        require(len(receipts) == 2 and all(x["complete"] for x in receipts), "pair_incomplete")
    except BaseException as exc:
        if pending:
            exact_attempts = exact_bytes = False
            worker_unknown = True
        failure = str(exc) if type(exc) is ObservationError else "capture_failed_redacted"
    finally:
        token = None
    if worker_unknown:
        halt = transport._save(Path(ledger)/"halt.json", {"at": clock().isoformat(), "date": day,
            "pair_claim": claim, "reason": "worker_exit_or_dispatch_state_unknown", "no_automatic_resume": True})
        refs.append(halt)
    integrity = True
    try:
        guard(); transport._verify(refs)
    except BaseException:
        integrity, failure = False, "final_binding_integrity_failed"
    outcome = {"artifact_type": "future_etf_observation_day_v1", "at": clock().isoformat(), "date": day,
        "scope_sha256": scope_sha, "evidence_class": evidence_class,
        "status": "completed_structure_only" if not failure else "failed_consumed", "error": failure,
        "claim": claim, "request_claims": request_claims, "receipts": receipts, "original_refs": refs,
        "paired_session_complete": not failure, "final_integrity": integrity,
        "worker_exit_all_confirmed": not worker_unknown,
        "attempts_started": attempts if exact_attempts else None, "attempts_started_lower_bound": lower_attempts,
        "received_bytes": received if exact_bytes else None, "received_bytes_lower_bound": lower_bytes,
        "reserved_request_upper_bound": len(request_claims),
        "exposure": "complete_paired_structure" if not failure else "incomplete_or_possible_exposure",
        "retry_allowed": False, "financial_numeric_values_decoded": False, "qualified": False, "real_forward": 0}
    transport._save(folder/"outcome.json", outcome)
    return outcome


def capture_synthetic(plan, calendar, day, folder, *, clock, exchange, bound_refs=()):
    """Artificial responses only; injected clock/transport NEVER produce real evidence."""
    validate_plan(plan, calendar)
    return _pair(plan, day, folder, bound_refs, _digest(plan), clock=clock,
                 token_loader=lambda: "ARTIFICIAL_TEST_SENTINEL", exchange=exchange,
                 evidence_class=ARTIFICIAL, guard=lambda: None)


def capture(day, *, repo_root, expected_scope_sha256, execute=False):
    """Preview by default. Exact dual release and fresh PM precede credentials/HTTP."""
    root = Path(repo_root).resolve()
    plan, scope_ref, refs = load_authority(root)
    require(scope_ref["sha256"] == expected_scope_sha256, "exact_scope_required")
    _slot(plan, day, utc_now())
    folder = PRODUCTION_LEDGER/day
    require(not (folder/"claim.json").exists(), "day_already_consumed")
    _idle(PRODUCTION_LEDGER)
    if not execute:
        return {"status": "preview", "date": day, "request_budget": 2, "credentials_read": False, "network_calls": 0}
    gate_refs = transport._fresh_gate(root, CONTEXT, folder)
    gate = _decode(_bound(gate_refs[0]))
    safety = gate["safety"]
    require(gate.get("mode") == MODE and safety.get("future_source_observation_allowed") is True
            and safety.get("future_source_observation_scope", {}).get("scope_sha256") == scope_ref["sha256"],
            "fresh_source_PM_required")
    require(all(value is False for key, value in safety.items()
                if key.endswith("_allowed") and key != "future_source_observation_allowed"),
            "all_other_PM_permissions_must_be_closed")
    refs += gate_refs
    def guard():
        require(transport._git(root, "branch", "--show-current") == BRANCH
                and transport._git(root, "rev-parse", "HEAD") == plan["head"], "branch_or_HEAD_changed")
        require(utc_now() < instant(plan["expires_at"]), "release_expired")
    guard(); transport._verify(refs)
    generated = instant(gate["generated_at"])
    require(generated <= utc_now() <= generated+timedelta(seconds=120), "fresh_PM_before_claim_required")
    # Only this production boundary can look up credentials. No actual release is shipped.
    return _pair(plan, day, PRODUCTION_LEDGER, refs, scope_ref["sha256"], clock=utc_now,
                 token_loader=lambda: os.environ.get("TUSHARE_TOKEN"), exchange=transport._isolated,
                 evidence_class=SOURCE, guard=guard)


def paired_coverage(plan, calendar, outcome_refs, *, expected_scope_sha256):
    """Hash-bound metadata summary, never admission. No financial body is decoded.

    Caller supplies reviewed outcome references; this does not authenticate who
    issued a scope. It cannot turn this metadata count into a candidate/activation.
    """
    days = validate_plan(plan, calendar)
    by_day = {}
    for ref in outcome_refs:
        result = _decode(_bound(ref))
        require(result["date"] in days and result["date"] not in by_day, "duplicate_or_unplanned_outcome")
        require(result["scope_sha256"] == expected_scope_sha256, "coverage_scope_mismatch")
        transport._verify(result["original_refs"])
        by_day[result["date"]] = result
    complete = []
    for day in days:
        r = by_day.get(day, {})
        good = (r.get("status") == "completed_structure_only" and r.get("paired_session_complete") is True
                and r.get("final_integrity") is True and r.get("evidence_class") == SOURCE
                and [x["symbol"] for x in r.get("receipts", [])] == list(wire.SYMBOLS)
                and all(x.get("complete") is True for x in r.get("receipts", [])))
        if good:
            claim = _decode(_bound(r["claim"]))
            require(claim["evidence_class"] == SOURCE and claim["date"] == day
                    and claim["scope_sha256"] == expected_scope_sha256, "coverage_claim_mismatch")
            for item in r["receipts"]:
                receipt = _decode(_bound(item["receipt"]))
                require(receipt["evidence_class"] == SOURCE and receipt["date"] == day
                        and receipt["symbol"] == item["symbol"] and receipt["raw"] == item["raw"]
                        and receipt["clock_valid"] is True and receipt["error"] is None
                        and receipt["body_complete"] is True and receipt["worker_exit_confirmed"] is True,
                        "coverage_receipt_mismatch")
                _bound(item["raw"])
            complete.append(day)
    missing = [d for d in days if d not in complete]
    return {"planned_sessions": len(days), "complete_paired_sessions": len(complete), "missing_dates": missing,
            "twenty_common_contiguous_source_sessions": len(days) == 20 and not missing,
            "ready_for_candidate": False, "numerical_quality_verified": False,
            "execution_state_verified": False, "action_coverage_verified": False, "qualified": False, "real_forward": 0}
