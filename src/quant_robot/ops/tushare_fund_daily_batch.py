"""One frozen 24-shard source capture; no financial numeric conversion.

Production transport has no injected token/session hooks. The separately named
synthetic entry always stamps synthetic evidence. Claims are exclusive and fsynced;
this is process interruption protection, not a physical power-loss certification.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import http.client
import json
import multiprocessing
import os
from pathlib import Path
import platform
import queue
import re
import ssl
import subprocess
import sys
import threading
import time

from quant_robot.ops import tushare_fund_daily_wire as wire

LIMITS = {"response_bytes": 262144, "batch_bytes": 6291456,
          "worker_seconds": 40, "idle_seconds": 10, "batch_seconds": 1200}
CODE_FILES = ("src/quant_robot/ops/tushare_fund_daily_batch.py",
              "src/quant_robot/ops/tushare_fund_daily_wire.py",
              "scripts/run_tushare_fund_daily_batch_capture.py",
              "scripts/run_quant_pm_startup_gate.py",
              "src/quant_robot/research/pm_startup_gate.py")


class BatchError(ValueError):
    """Only static codes may cross the public error boundary."""


def _now():
    return datetime.now(timezone.utc).isoformat()


def _check(value, code):
    if not value:
        raise BatchError(code)


def reference(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {"path": path.as_posix(), "sha256": sha256(raw).hexdigest(), "bytes": len(raw)}


def _bound(ref):
    _check(type(ref) is dict and set(ref) == {"path", "sha256", "bytes"}, "invalid_binding")
    _check(type(ref["bytes"]) is int and 0 <= ref["bytes"] <= 2_000_000, "binding_size_limit")
    with Path(ref["path"]).open("rb") as stream:
        raw = stream.read(ref["bytes"]+1)
    _check(len(raw) == ref["bytes"] and sha256(raw).hexdigest() == ref["sha256"], "bound_artifact_changed")
    return raw


def _save(path, value, *, raw=False):
    data = value if raw else (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n").encode()
    ref = {"path": Path(path).resolve().as_posix(), "sha256": sha256(data).hexdigest(), "bytes": len(data)}
    with Path(path).open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    _bound(ref)  # Verify against bytes supplied by this action, never rebaseline from disk.
    return ref


def implementation(root):
    root = Path(root).resolve()
    return {"python": platform.python_version(), "openssl": ssl.OPENSSL_VERSION,
            "code": {name: reference(root/name) for name in CODE_FILES}}


def _headers(headers, token):
    """Fixed grammar projection; no arbitrary response header text is retained."""
    result = {}
    patterns = {"date": r"[A-Za-z]{3}, [0-9]{2} [A-Za-z]{3} [0-9]{4} [0-9:]{8} GMT",
                "content-length": r"[0-9]{1,12}",
                "content-type": r"application/json(?:;\s*charset=[Uu][Tt][Ff]-?8)?",
                "content-encoding": r"identity|gzip|deflate|br"}
    for key, pattern in patterns.items():
        value = headers.get(key)
        if value is not None:
            _check(type(value) is str and token not in value, "unsafe_header_not_retained")
            result[key] = value if re.fullmatch(pattern, value) else "unrecognized"
    return result


def _exchange(request, token, emit, connection_factory=http.client.HTTPSConnection):
    """Private injectable primitive for artificial tests, never exposed by capture."""
    body = bytearray()
    report = {"attempts_started": 0, "request_started_at": None,
              "headers_received_at": None, "body_completed_at": None,
              "failed_at": None, "http_status": None, "headers": {},
              "body_complete": False, "error": None}
    connection = None
    try:
        # Direct HTTPSConnection does not consult proxies or follow redirects/retry.
        connection = connection_factory("api.tushare.pro", timeout=LIMITS["idle_seconds"],
                                        context=ssl.create_default_context())
        payload = json.dumps({"api_name": wire.API, "token": token,
                              "params": request["params"], "fields": request["fields"]}).encode()
        report.update(attempts_started=1, request_started_at=_now())
        emit({"event": "start", "at": report["request_started_at"]})
        connection.request("POST", "/", body=payload,
                           headers={"Content-Type": "application/json", "Accept-Encoding": "identity"})
        response = connection.getresponse()
        report.update(headers_received_at=_now(), http_status=response.status)
        pairs = [(key.lower(), value) for key, value in response.getheaders()]
        for name in ("content-length", "transfer-encoding", "content-encoding"):
            _check(sum(key == name for key, _ in pairs) <= 1, "ambiguous_HTTP_framing")
        headers = dict(pairs)
        _check(not ("content-length" in headers and "transfer-encoding" in headers), "ambiguous_HTTP_framing")
        report["headers"] = _headers(headers, token)
        emit({"event": "headers", "at": report["headers_received_at"]})
        _check(headers.get("content-encoding", "identity").lower() == "identity", "unsupported_content_encoding")
        # read1 is a single bounded application read; no decompression, no cap+1 probe.
        while len(body) < LIMITS["response_bytes"]:
            remaining = LIMITS["response_bytes"]-len(body)
            try:
                part = response.read1(min(8192, remaining))
            except http.client.IncompleteRead as exc:
                part = exc.partial
                _check(type(part) is bytes and len(part) <= remaining, "invalid_partial_body")
                body.extend(part)
                emit({"event": "bytes", "count": len(body)})
                raise BatchError("incomplete_HTTP_body") from None
            _check(type(part) is bytes and len(part) <= remaining, "invalid_body_chunk")
            body.extend(part)
            emit({"event": "bytes", "count": len(body)})
            if not part:
                _check(response.length in (None, 0), "incomplete_HTTP_body")
                report["body_complete"] = True
                break
            if response.length == 0:
                report["body_complete"] = True
                break
        _check(report["body_complete"], "response_cap_without_EOF")
        report["body_completed_at"] = _now()
        _check(response.status == 200, "HTTP_status_rejected")
    except BaseException as exc:
        report["error"] = str(exc) if isinstance(exc, BatchError) else "transport_failed_redacted"
        report["failed_at"] = _now()
    finally:
        if connection is not None:
            try:
                connection.close()
            except BaseException:
                report.update(error="transport_cleanup_failed", failed_at=_now())
    return {**report, "body": bytes(body), "received_bytes": len(body)}


def _worker(connection, request, token):
    try:
        connection.send({"result": _exchange(request, token, connection.send)})
    except BaseException:
        # Neither traceback nor arbitrary exception text may expose token/body.
        pass
    finally:
        token = None
        connection.close()


def _reader(connection, messages):
    try:
        while True:
            messages.put(connection.recv())
    except BaseException:
        messages.put({"reader_closed": True})


def _stop(process, started, deadline):
    try:
        if started:
            process.join(timeout=max(0, min(.2, deadline-time.monotonic())))
            if process.is_alive():
                process.terminate(); process.join(timeout=.5)
            if process.is_alive():
                process.kill(); process.join(timeout=.5)
        return not started or not process.is_alive()
    except BaseException:
        return False


def _isolated(request, token, timeout, *, worker=_worker, context=None):
    """Hard wall deadline also covers a blocked IPC receive; exit is confirmed first."""
    _check(0 < timeout <= LIMITS["worker_seconds"], "worker_time_limit")
    context = context or multiprocessing.get_context("spawn")
    incoming, outgoing = context.Pipe(duplex=False)
    process = context.Process(target=worker, args=(outgoing, request, token), daemon=True)
    messages = queue.Queue(maxsize=128)
    reader = threading.Thread(target=_reader, args=(incoming, messages), daemon=True)
    deadline, lower_bytes, observed_start = time.monotonic()+timeout, 0, False
    observed_times = {"request_started_at": None, "headers_received_at": None}
    result, failure, started = None, "worker_failed_redacted", False
    try:
        process.start(); started = True; outgoing.close(); reader.start()
        while True:
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                failure = "worker_wall_deadline"; break
            try:
                message = messages.get(timeout=remaining)
            except queue.Empty:
                failure = "worker_wall_deadline"; break
            if type(message) is not dict:
                failure = "worker_protocol_invalid"; break
            if "result" in message:
                result = message["result"]; break
            if message.get("reader_closed"):
                break
            if message.get("event") == "start":
                observed_start = True
                observed_times["request_started_at"] = message.get("at")
            elif message.get("event") == "headers":
                observed_times["headers_received_at"] = message.get("at")
            elif message.get("event") == "bytes":
                count = message.get("count")
                if type(count) is not int or not lower_bytes <= count <= LIMITS["response_bytes"]:
                    failure = "worker_protocol_invalid"; break
                lower_bytes = count
            else:
                failure = "worker_protocol_invalid"; break
    except BaseException:
        failure = "worker_launch_or_IPC_failed"
    finally:
        exited = _stop(process, started, deadline)
        outgoing.close()
        if exited:
            incoming.close()
            if reader.ident is not None:
                reader.join(timeout=.2)
            process.close()
    # Do not accept final bytes until the worker and IPC reader are stopped.
    if not exited or reader.is_alive():
        result, failure = None, "worker_termination_unconfirmed"
    if result is not None:
        return {**result, "worker_exit_confirmed": True,
                "received_bytes_lower_bound": result["received_bytes"],
                "attempts_started_lower_bound": result["attempts_started"]}
    return {"body": None, "error": failure, "body_complete": False,
            "worker_exit_confirmed": exited and not reader.is_alive(),
            "received_bytes": 0 if not started else None,
            "received_bytes_lower_bound": lower_bytes,
            "attempts_started": 0 if not started else None,
            "attempts_started_lower_bound": int(observed_start),
            **observed_times,
            "body_completed_at": None, "failed_at": _now(), "headers": {}, "http_status": None}


def _verify(refs):
    for ref in refs:
        _bound(ref)


def _capture(manifest, folder, refs, token_loader, transport, *, evidence_class, check_context=lambda: None):
    """Internal controller. Any caller-supplied transport is synthetic by public API."""
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    claim = _save(folder/"claim.json", {"at": _now(), "evidence_class": evidence_class,
                                       "once": True, "request_budget": 24, "retry": 0})
    refs = [*refs, claim]
    deadline = time.monotonic()+LIMITS["batch_seconds"]
    receipts, actual_bytes, lower_bytes, attempts, lower_attempts, reserved = [], 0, 0, 0, 0, 0
    token, failure, exact_bytes, exact_attempts = None, None, True, True
    transport_pending, request_claims = False, []
    try:
        _verify(refs)
        check_context()
        token = token_loader()
        _check(type(token) is str and 1 <= len(token) <= 4096 and token == token.strip(), "credential_unavailable")
        for request in manifest["requests"]:
            _verify(refs)
            check_context()
            remaining = deadline-time.monotonic()
            _check(remaining > 0, "batch_wall_deadline")
            reserved += LIMITS["response_bytes"]
            _check(reserved <= LIMITS["batch_bytes"], "batch_byte_reservation_exceeded")
            directory = folder/"requests"/request["id"]
            directory.mkdir(parents=True, exist_ok=False)
            request_claim = _save(directory/"claim.json", {"at": _now(), "request": request,
                                  "batch_claim": claim, "reserved_bytes": LIMITS["response_bytes"]})
            refs.append(request_claim)
            request_claims.append(request_claim)
            transport_pending = True
            response = transport(request, token, min(remaining, LIMITS["worker_seconds"]))
            transport_pending = False
            actual = response["received_bytes"]
            exact_bytes &= actual is not None
            exact_attempts &= response["attempts_started"] is not None
            actual_bytes += actual or 0
            attempts += response["attempts_started"] or 0
            lower_bytes += response["received_bytes_lower_bound"]
            lower_attempts += response["attempts_started_lower_bound"]
            metadata = {key: value for key, value in response.items() if key != "body"}
            raw = response["body"]
            raw_ref, structure, safe = None, None, False
            if response["worker_exit_confirmed"] and type(raw) is bytes and raw:
                try:
                    wire.decode_opaque(raw, token=token)
                    safe = True
                except wire.WireError:
                    pass
            if safe:
                raw_ref = _save(directory/"response.entity.json", raw, raw=True)
                refs.append(raw_ref)
                if not response["error"]:
                    try:
                        structure = wire.inspect_structure(raw, request, token=token)
                    except wire.WireError as exc:
                        metadata.update(error=exc.code, identity_findings=exc.metadata)
            elif not metadata["error"]:
                metadata["error"] = "original_not_retained_due_safety_screen"
            metadata.update(artifact_type="fund_daily_batch_request_receipt_v1", evidence_class=evidence_class,
                            request_id=request["id"], request_claim=request_claim, raw=raw_ref,
                            retained_at=_now() if raw_ref else None, structure=structure,
                            originals_not_retained_due_safety_screen=not safe,
                            financial_numeric_values_decoded=False, qualified=False, real_forward=0)
            receipt_ref = _save(directory/"receipt.json", metadata)
            refs.append(receipt_ref)
            receipts.append({"request_id": request["id"], "role": request["role"],
                             "raw": raw_ref, "receipt": receipt_ref, "request_claim": request_claim,
                             "structure": structure})
            _verify(refs)
            check_context()
            _check(time.monotonic() <= deadline, "batch_wall_deadline")
            if metadata["error"]:
                raise BatchError(metadata["error"])
        _check(len(receipts) == 24 and sum(x["structure"]["rows"] for x in receipts) == 4908,
               "complete_source_set_required")
        _verify(refs)
        check_context()
        index_ref = _save(folder/"source_index.json", {"at": _now(), "evidence_class": evidence_class,
                          "roles": receipts, "request_count": 24, "identity_rows": 4908,
                          "numerical_quality_verified": False, "qualified": False, "real_forward": 0})
    except BaseException as exc:
        if transport_pending:
            exact_bytes = exact_attempts = False
        failure = str(exc) if isinstance(exc, (BatchError, wire.WireError)) else "capture_failed_redacted"
        index_ref = None
    finally:
        token = None
    outcome = {"at": _now(), "status": "completed_structure_only" if not failure else "failed_consumed",
               "evidence_class": evidence_class, "error": failure, "batch_claim": claim,
               "request_receipts": receipts, "source_index": index_ref, "retry_allowed": False,
               "request_claims": request_claims,
               "body_bytes_received": actual_bytes if exact_bytes else None,
               "body_bytes_received_lower_bound": lower_bytes, "reserved_body_bytes_upper_bound": reserved,
               "HTTP_attempts_started": attempts if exact_attempts else None,
               "HTTP_attempts_started_lower_bound": lower_attempts,
               "financial_numeric_values_decoded": False, "qualified": False, "real_forward": 0}
    _save(folder/"outcome.json", outcome)
    return outcome


def capture_synthetic(manifest, sessions, folder, *, transport, token_loader, bound_refs=()):
    """Artificial tests only. This entry can never issue production evidence."""
    wire.validate_manifest(manifest, sessions)
    return _capture(manifest, folder, list(bound_refs), token_loader, transport,
                    evidence_class="synthetic_only_not_source_evidence")


def _git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=15, check=True)
    return result.stdout.decode().strip()


def _scope(path, root, digest):
    ref = reference(path)
    _check(ref["sha256"] == digest, "exact_scope_digest_required")
    scope = json.loads(_bound(ref))
    _check(scope.get("artifact_type") == "constant_mix_fund_daily_batch_scope_v1"
           and scope.get("purpose") == "source_structure_only"
           and scope.get("limits") == LIMITS and scope.get("allow_2026_prices") is False,
           "fixed_source_scope_required")
    _check(scope["implementation"] == implementation(root), "implementation_or_runtime_changed")
    context = scope["context"]
    _check(context.get("machine") == "office_desktop" and context.get("task") in ("data_pipeline", "factor_review")
           and context.get("branch", "").startswith("codex/"), "desktop_context_required")
    _check(_git(root, "branch", "--show-current") == context["branch"]
           and _git(root, "rev-parse", "HEAD") == scope["head"], "branch_or_HEAD_changed")
    first, last = (datetime.fromisoformat(scope[key].replace("Z", "+00:00")) for key in ("valid_from", "valid_until"))
    now = datetime.now(timezone.utc)
    _check(first.tzinfo is not None and last.tzinfo is not None and first <= now < last <= first+timedelta(hours=72),
           "source_scope_expired")
    manifest = json.loads(_bound(scope["manifest"]))
    sessions = json.loads(_bound(scope["sessions"]))
    wire.validate_manifest(manifest, sessions)
    refs = [ref, scope["manifest"], scope["sessions"], *scope["bindings"], *scope["implementation"]["code"].values()]
    _verify(refs)
    folder = Path(scope["capture_directory"]).resolve()
    _check(folder.is_relative_to(root/"data"/"reports"), "archive_must_stay_in_local_reports")
    return scope, manifest, folder, refs


def _fresh_gate(root, context, folder):
    root = Path(root).resolve()
    output = folder.parent/(folder.name+"_startup_gate")
    output.mkdir(parents=True, exist_ok=False)
    command = [sys.executable, str(root/"scripts/run_quant_pm_startup_gate.py"),
               "--machine", context["machine"], "--task", context["task"],
               "--branch", context["branch"], "--output-dir", str(output)]
    run = subprocess.run(command, cwd=root, capture_output=True, timeout=60, check=False)
    _check(run.returncode == 0, "fresh_PM_gate_failed")
    ref = reference(output/"quant_pm_startup_gate_pack.json")
    gate = json.loads(_bound(ref))
    _check(gate.get("status") == "ready" and gate.get("primary_market") == "CN_ETF"
           and gate.get("blockers") == [], "fresh_PM_gate_blocked")
    selected = gate.get("selected", {})
    _check(all(selected.get(key) == value for key, value in context.items())
           and selected.get("current_branch") == context["branch"], "fresh_PM_context_changed")
    generated = datetime.fromisoformat(gate["generated_at"].replace("Z", "+00:00"))
    _check(generated <= datetime.now(timezone.utc) <= generated+timedelta(seconds=120), "fresh_PM_clock_invalid")
    reading, rows = gate.get("reading_summary", {}), gate.get("required_reading", [])
    _check(rows and reading.get("required") == reading.get("read") == len(rows)
           and reading.get("missing") == 0 and all(r.get("status") == "read" for r in rows), "PM_reading_incomplete")
    _check(gate.get("safety", {}).get("final_holdout_allowed") is False
           and gate.get("safety", {}).get("live_boundary_allowed") is False, "PM_boundaries_changed")
    refs = [ref]
    for row in rows:
        path = (root/row["path"]).resolve()
        _check(path.is_relative_to(root), "PM_reading_path_invalid")
        # The existing gate hashes universal-newline text; bind both that evidence
        # and the current raw bytes rather than pretending they have identical SHAs.
        normalized = path.read_text(encoding="utf-8").encode("utf-8")
        _check(sha256(normalized).hexdigest() == row["sha256"] and len(normalized) == row["bytes"],
               "PM_reading_changed")
        refs.append(reference(path))
    return refs


def capture(scope_path, *, repo_root, expected_scope_sha256, execute=False):
    """Default preview has no credential lookup, gate execution, claim or network."""
    root = Path(repo_root).resolve()
    scope, manifest, folder, refs = _scope(scope_path, root, expected_scope_sha256)
    if not execute:
        return {"status": "preview", "request_count": 24, "expected_rows": 4908,
                "claim_exists": (folder/"claim.json").exists(), "credentials_read": False, "network_calls": 0}
    _check(not (folder/"claim.json").exists(), "batch_already_consumed")
    review_ref = reference(scope["root_review_path"])
    review = json.loads(_bound(review_ref))
    _check(review.get("status") == "accepted_exact_constant_mix_source_capture"
           and review.get("scope_sha256") == expected_scope_sha256
           and review.get("manifest_sha256") == scope["manifest"]["sha256"]
           and review.get("implementation") == scope["implementation"], "exact_root_review_required")
    refs += [review_ref, *_fresh_gate(root, scope["context"], folder)]
    _verify(refs)
    def context_unchanged():
        _check(_git(root, "branch", "--show-current") == scope["context"]["branch"]
               and _git(root, "rev-parse", "HEAD") == scope["head"], "branch_or_HEAD_changed")
        _check(datetime.now(timezone.utc) < datetime.fromisoformat(scope["valid_until"].replace("Z", "+00:00")),
               "source_scope_expired")
    return _capture(manifest, folder, refs, lambda: os.environ.get("TUSHARE_TOKEN"), _isolated,
                    evidence_class="provider_wire_structure_only", check_context=context_unchanged)
