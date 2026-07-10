from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from quant_robot.storage.atomic import atomic_write_json
from quant_robot.storage.fingerprints import sha256_file


AUTHORIZATION_STAGE = "final_holdout_access_authorization"
LEDGER_SCHEMA_VERSION = 1


def candidate_set_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_final_holdout_authorization(
    *,
    packet_path: str | Path | None,
    candidate_hash: str,
    context: str,
) -> dict[str, Any]:
    if packet_path is None:
        raise ValueError(f"{context} final holdout requires an access packet")
    path = Path(packet_path)
    if not path.is_file():
        raise ValueError(f"{context} final holdout access packet is missing: {path}")
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{context} final holdout access packet is invalid: {path}") from exc
    decision = packet.get("decision") if isinstance(packet.get("decision"), dict) else {}
    if packet.get("stage") != AUTHORIZATION_STAGE:
        raise ValueError(f"{context} final holdout access packet stage mismatch: {path}")
    if packet.get("generated_at") != date.today().isoformat():
        raise ValueError(f"{context} final holdout access packet must be generated today: {path}")
    if packet.get("status") != "authorized":
        raise ValueError(f"{context} final holdout access is not authorized: {path}")
    if packet.get("candidate_set_sha256") != candidate_hash:
        raise ValueError(f"{context} final holdout candidate hash mismatch: {path}")
    if decision.get("candidate_frozen") is not True or decision.get("final_holdout_read_allowed") is not True:
        raise ValueError(f"{context} final holdout candidate set is not frozen and authorized: {path}")
    if decision.get("blockers"):
        raise ValueError(f"{context} final holdout access packet has blockers: {path}")
    if packet.get("read_once") is not True:
        raise ValueError(f"{context} final holdout access packet must require read once: {path}")
    if packet.get("live_boundary_allowed") is not False:
        raise ValueError(f"{context} final holdout access packet violates live boundary: {path}")
    return {"packet": packet, "packet_path": str(path), "packet_sha256": sha256_file(path)}


def authorize_final_holdout(
    *,
    packet_path: str | Path | None,
    ledger_path: str | Path | None,
    candidate_hash: str,
    context: str,
) -> dict[str, Any]:
    validated = validate_final_holdout_authorization(
        packet_path=packet_path,
        candidate_hash=candidate_hash,
        context=context,
    )
    if ledger_path is None:
        raise ValueError(f"{context} final holdout requires a read-once ledger")
    ledger = Path(ledger_path)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    lock_path = ledger.with_suffix(ledger.suffix + ".lock")
    descriptor = _exclusive_lock(lock_path, context=context)
    try:
        payload = _load_ledger(ledger)
        reads = payload.setdefault("reads", {})
        if candidate_hash in reads:
            raise ValueError(f"{context} final holdout read already consumed for candidate {candidate_hash}")
        receipt = {
            "candidate_set_sha256": candidate_hash,
            "packet_path": validated["packet_path"],
            "packet_sha256": validated["packet_sha256"],
            "read_at": datetime.now(timezone.utc).isoformat(),
            "context": context,
            "read_recorded": True,
        }
        reads[candidate_hash] = receipt
        atomic_write_json(ledger, payload)
        return receipt
    finally:
        os.close(descriptor)
        lock_path.unlink(missing_ok=True)


def _exclusive_lock(path: Path, *, context: str) -> int:
    try:
        return os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ValueError(f"{context} final holdout ledger is locked: {path}") from exc


def _load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": LEDGER_SCHEMA_VERSION, "reads": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid final holdout ledger: {path}") from exc
    if not isinstance(payload, dict) or int(payload.get("schema_version", 0)) != LEDGER_SCHEMA_VERSION:
        raise ValueError(f"Invalid final holdout ledger schema: {path}")
    if not isinstance(payload.get("reads"), dict):
        raise ValueError(f"Invalid final holdout ledger reads: {path}")
    return payload
