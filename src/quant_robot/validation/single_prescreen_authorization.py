from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from quant_robot.storage.atomic import atomic_write_json
from quant_robot.storage.fingerprints import sha256_file


AUTHORIZATION_STAGE = "cn_etf_single_prescreen_authorization"
AUTHORIZED_STATUS = "authorized_single_prescreen"
ALLOWED_TASK = "factor_batch"
ALLOWED_STAGE = "cn_etf_dynamic_peer_dislocation_prescreen"
LEDGER_SCHEMA_VERSION = 1
SOURCE_HASH_KEYS = ("mapping", "source_config", "source_result")
PROHIBITED_BOUNDARIES = (
    "portfolio_grid_allowed",
    "walk_forward_allowed",
    "final_holdout_allowed",
    "promotion_allowed",
    "paper_signal_allowed",
    "broker_connection_allowed",
    "account_read_allowed",
    "order_placement_allowed",
    "live_boundary_allowed",
)


def build_single_prescreen_authorization(
    *,
    registration_date: str,
    candidate_name: str,
    preregistration_config_sha256: str,
    preregistration_result_sha256: str,
    source_hashes: Mapping[str, str],
    execution_ledger_path: str | Path,
) -> dict[str, Any]:
    """Build a deterministic authorization for exactly one frozen prescreen."""

    _require_nonempty(candidate_name, "candidate name")
    _require_sha256(preregistration_config_sha256, "preregistration config SHA-256")
    _require_sha256(preregistration_result_sha256, "preregistration result SHA-256")
    ledger_path = str(execution_ledger_path)
    _require_nonempty(ledger_path, "execution ledger path")
    normalized_source_hashes = _validated_source_hashes(source_hashes)
    identity_payload = {
        "candidate_name": candidate_name,
        "preregistration_config_sha256": preregistration_config_sha256,
        "preregistration_result_sha256": preregistration_result_sha256,
        "source_hashes": normalized_source_hashes,
        "execution_ledger_path": ledger_path,
    }
    packet: dict[str, Any] = {
        "stage": AUTHORIZATION_STAGE,
        "registration_date": registration_date,
        "status": AUTHORIZED_STATUS,
        "authorization_id": _authorization_id(identity_payload),
        **identity_payload,
        "primary_horizon": 5,
        "diagnostic_horizon": 20,
        "allowed_task": ALLOWED_TASK,
        "allowed_stage": ALLOWED_STAGE,
        "max_executions": 1,
        "execution_ledger_required": True,
    }
    packet.update({field: False for field in PROHIBITED_BOUNDARIES})
    return packet


def write_single_prescreen_authorization(
    path: str | Path,
    packet: Mapping[str, Any],
) -> Path:
    destination = Path(path)
    atomic_write_json(destination, dict(packet))
    return destination


def validate_single_prescreen_authorization(
    *,
    packet_path: str | Path,
    expected_candidate_name: str,
    expected_config_sha256: str,
    expected_packet_sha256: str,
    context: str,
) -> dict[str, Any]:
    path = Path(packet_path)
    if not path.is_file():
        raise ValueError(f"{context} single prescreen authorization is missing: {path}")
    _require_sha256(expected_config_sha256, f"{context} expected config SHA-256")
    _require_sha256(expected_packet_sha256, f"{context} expected authorization SHA-256")
    packet_sha256 = sha256_file(path)
    if packet_sha256 != expected_packet_sha256:
        raise ValueError(f"{context} single prescreen authorization hash mismatch: {path}")
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{context} single prescreen authorization is invalid: {path}") from exc
    if not isinstance(packet, dict):
        raise ValueError(f"{context} single prescreen authorization is invalid: {path}")
    if packet.get("stage") != AUTHORIZATION_STAGE:
        raise ValueError(f"{context} single prescreen authorization stage mismatch: {path}")
    if packet.get("status") != AUTHORIZED_STATUS:
        raise ValueError(f"{context} single prescreen is not authorized: {path}")
    if packet.get("candidate_name") != expected_candidate_name:
        raise ValueError(f"{context} single prescreen candidate mismatch: {path}")
    if packet.get("preregistration_config_sha256") != expected_config_sha256:
        raise ValueError(f"{context} single prescreen config hash mismatch: {path}")
    _validate_packet_contract(packet, context=context, path=path)
    identity_payload = _identity_payload(packet)
    if packet.get("authorization_id") != _authorization_id(identity_payload):
        raise ValueError(f"{context} single prescreen authorization identity mismatch: {path}")
    return {
        "packet": packet,
        "packet_path": str(path),
        "packet_sha256": packet_sha256,
        "authorization_id": str(packet["authorization_id"]),
    }


def claim_single_prescreen_authorization(
    *,
    packet_path: str | Path,
    ledger_path: str | Path,
    expected_candidate_name: str,
    expected_config_sha256: str,
    expected_packet_sha256: str,
    context: str,
) -> dict[str, Any]:
    validated = validate_single_prescreen_authorization(
        packet_path=packet_path,
        expected_candidate_name=expected_candidate_name,
        expected_config_sha256=expected_config_sha256,
        expected_packet_sha256=expected_packet_sha256,
        context=context,
    )
    ledger = Path(ledger_path)
    bound_ledger = Path(validated["packet"]["execution_ledger_path"])
    if ledger.resolve() != bound_ledger.resolve():
        raise ValueError(
            f"{context} single prescreen ledger path mismatch: "
            f"expected {bound_ledger}, received {ledger}"
        )
    ledger.parent.mkdir(parents=True, exist_ok=True)
    lock_path = ledger.with_suffix(ledger.suffix + ".lock")
    descriptor = _exclusive_lock(lock_path, context=context)
    try:
        payload = _load_ledger(ledger)
        claims = payload.setdefault("claims", {})
        authorization_id = validated["authorization_id"]
        if authorization_id in claims:
            raise ValueError(
                f"{context} single prescreen authorization already consumed: {authorization_id}"
            )
        receipt = {
            "authorization_id": authorization_id,
            "candidate_name": expected_candidate_name,
            "packet_path": validated["packet_path"],
            "packet_sha256": validated["packet_sha256"],
            "claimed_at": datetime.now(timezone.utc).isoformat(),
            "context": context,
            "execution_claim_recorded": True,
        }
        claims[authorization_id] = receipt
        atomic_write_json(ledger, payload)
        return receipt
    finally:
        os.close(descriptor)
        lock_path.unlink(missing_ok=True)


def _validate_packet_contract(packet: Mapping[str, Any], *, context: str, path: Path) -> None:
    _require_sha256(
        packet.get("preregistration_result_sha256"),
        f"{context} preregistration result SHA-256",
    )
    _validated_source_hashes(packet.get("source_hashes", {}))
    if packet.get("allowed_task") != ALLOWED_TASK or packet.get("allowed_stage") != ALLOWED_STAGE:
        raise ValueError(f"{context} single prescreen scope mismatch: {path}")
    if packet.get("primary_horizon") != 5 or packet.get("diagnostic_horizon") != 20:
        raise ValueError(f"{context} single prescreen horizon contract mismatch: {path}")
    if packet.get("max_executions") != 1 or packet.get("execution_ledger_required") is not True:
        raise ValueError(f"{context} single prescreen execution contract mismatch: {path}")
    _require_nonempty(packet.get("execution_ledger_path"), f"{context} execution ledger path")
    for field in PROHIBITED_BOUNDARIES:
        if packet.get(field) is not False:
            raise ValueError(f"{context} single prescreen boundary enabled: {field}")


def _identity_payload(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_name": packet.get("candidate_name"),
        "preregistration_config_sha256": packet.get("preregistration_config_sha256"),
        "preregistration_result_sha256": packet.get("preregistration_result_sha256"),
        "source_hashes": packet.get("source_hashes"),
        "execution_ledger_path": packet.get("execution_ledger_path"),
    }


def _authorization_id(identity_payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(identity_payload),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validated_source_hashes(source_hashes: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(source_hashes, Mapping):
        raise ValueError("source hashes must be a JSON object")
    normalized = {str(key): str(value) for key, value in source_hashes.items()}
    if tuple(sorted(normalized)) != SOURCE_HASH_KEYS:
        raise ValueError(
            "source hashes must contain exactly mapping, source_config, and source_result"
        )
    for key, value in normalized.items():
        _require_sha256(value, f"source {key} SHA-256")
    return {key: normalized[key] for key in SOURCE_HASH_KEYS}


def _require_sha256(value: Any, label: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{label} must be 64 lowercase hexadecimal characters")
    if value != value.lower() or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{label} must be 64 lowercase hexadecimal characters")


def _require_nonempty(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty")


def _exclusive_lock(path: Path, *, context: str) -> int:
    try:
        return os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ValueError(f"{context} single prescreen ledger is locked: {path}") from exc


def _load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": LEDGER_SCHEMA_VERSION, "claims": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid single prescreen ledger: {path}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != LEDGER_SCHEMA_VERSION:
        raise ValueError(f"Invalid single prescreen ledger schema: {path}")
    if not isinstance(payload.get("claims"), dict):
        raise ValueError(f"Invalid single prescreen ledger claims: {path}")
    return payload
