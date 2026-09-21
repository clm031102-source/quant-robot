"""One-attempt source collections with claims written before each HTTP request."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Callable

from quant_robot.config.secrets import SecretMissingError
from quant_robot.data.sources import tushare_http
from quant_robot.data.sources.tushare_collection_scope import make_client, validate_scope
from quant_robot.data.sources.tushare_http import TushareSourceError
from quant_robot.storage.atomic import atomic_write_json


COLLECTION_ROOT = Path("data/reports/tushare_source_collections")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _exclusive_json(path: Path, payload: dict) -> None:
    # Even an interrupted/partial claim is treated as consumed, never auto-retried.
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.flush()
        os.fsync(handle.fileno())


def _implementation_hashes() -> dict:
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (
        Path(__file__), Path(tushare_http.__file__), Path(__file__).with_name("tushare_collection_scope.py"),
        Path(__file__).with_name("tushare_calendar_contract.py"))}


def _collect_requests(scope: dict, validated: dict, *, client, output: Path, claims: Path, result: dict) -> None:
    for index, (request, identity) in enumerate(zip(scope["requests"], validated["request_identities"], strict=True), 1):
        attempt_path = output / f"request_{index:03d}.json"
        attempt = {"request_identity": identity, "request": request, "status": "started", "started_at": _now()}
        # Persist both request details and an exclusive cross-scope reservation before I/O.
        atomic_write_json(attempt_path, attempt)
        try:
            _exclusive_json(claims / f"{identity}.json", {"scope_sha256": validated["scope_sha256"],
                "request_identity": identity, "attempt_path": str(attempt_path), "claimed_at": _now()})
        except FileExistsError:
            attempt.update(status="already_claimed", finished_at=_now())
            atomic_write_json(attempt_path, attempt)
            result["status"] = "request_already_claimed"
            break
        result["requests_started"] += 1
        result["requests_not_started"] -= 1
        atomic_write_json(output / "result.json", result)
        try:
            client.query(request["api_name"], fields=request["fields"],
                max_rows=request["max_rows"], **request["params"])
            if client.last_payload is None:
                raise RuntimeError("validated source payload unavailable")
            payload_path = output / f"response_{index:03d}.json"
            atomic_write_json(payload_path, client.last_payload)
            attempt.update(status=client.last_attempt["status"],
                canonical_payload_file=payload_path.name,
                canonical_payload_sha256=hashlib.sha256(payload_path.read_bytes()).hexdigest(),
                payload_representation="validated_redacted_projection_not_original_http_bytes")
            result["responses_received"] += 1
            if client.last_attempt["status"] == "empty_unqualified":
                result["empty_responses"] += 1
        except TushareSourceError:
            attempt["status"] = "failed"
            result["status"] = "failed"
        except Exception as exc:
            attempt.update(status="evidence_write_failed", failure_kind=type(exc).__name__)
            raise
        finally:
            attempt.update(transport=client.last_attempt, finished_at=_now())
            atomic_write_json(attempt_path, attempt)
            atomic_write_json(output / "result.json", result)
        if result["status"] == "failed":
            break
    else:
        result["status"] = "collected_with_empty_unqualified" if result["empty_responses"] else "collected_unqualified"


def collect_source(
    scope: dict, *, repo_root: str | Path, run_gate: Callable[[Path], dict],
    get_token: Callable[[], str], execute: bool = False, expected_scope_sha256: str | None = None,
) -> dict:
    """Preview by default. Execution consumes each identical request at most once.

    The gate callback must run the project's fresh startup gate, not load a cached
    ready result. The CLI supplies this callback and the existing-secret reader.
    Hashes bind reviewed files; they do not themselves grant research admission.
    """
    validated = validate_scope(scope, repo_root=repo_root)
    root = (Path(repo_root).resolve() / COLLECTION_ROOT).resolve()
    if not root.is_relative_to(Path(repo_root).resolve()):
        raise ValueError("collection output escapes repository")
    claims = root / "claims"
    output = root / "runs" / validated["scope_sha256"]
    already = [identity for identity in validated["request_identities"] if (claims / f"{identity}.json").exists()]
    preview = {**validated, "status": "preview", "output_dir": str(output),
        "already_claimed_requests": already, "source_audit_verified": False,
        "research_admission_granted": False, "network_requests": 0}
    if not execute:
        return preview
    if expected_scope_sha256 != validated["scope_sha256"]:
        raise ValueError("execution requires the exact frozen scope hash from preview")
    if already or output.exists():
        raise ValueError("scope or identical source request already attempted; no automatic restart")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        output.mkdir()
    except FileExistsError as exc:
        raise ValueError("scope already reserved by another process") from exc
    claims.mkdir(parents=True, exist_ok=True)
    result = {**validated, "status": "started", "output_dir": str(output), "started_at": _now(),
        "requests_started": 0, "requests_not_started": len(scope["requests"]),
        "responses_received": 0, "empty_responses": 0, "source_audit_verified": False,
        "research_admission_granted": False, "implementation_sha256": _implementation_hashes()}
    atomic_write_json(output / "scope.json", scope)
    atomic_write_json(output / "result.json", result)
    try:
        gate = run_gate(output / "startup_gate")
        atomic_write_json(output / "gate.json", gate)
        result["gate_sha256"] = hashlib.sha256((output / "gate.json").read_bytes()).hexdigest()
        if gate.get("status") != "ready" or gate.get("primary_market") != "CN_ETF" or gate.get("blockers") != []:
            result["status"] = "gate_blocked"
        else:
            client = make_client(scope, token=get_token())
            _collect_requests(scope, validated, client=client, output=output, claims=claims, result=result)
    except SecretMissingError:
        result.update(status="credential_missing", failure_kind="existing_tushare_token_required")
    except Exception as exc:
        # Never echo arbitrary exception text from credential/gate/storage callbacks.
        result.update(status="failed", failure_kind=type(exc).__name__)
    except BaseException:
        result["status"] = "interrupted"
        raise
    finally:
        result["finished_at"] = _now()
        atomic_write_json(output / "result.json", result)
    return result
