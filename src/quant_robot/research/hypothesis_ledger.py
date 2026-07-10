from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

from quant_robot.storage.atomic import atomic_write_json


HYPOTHESIS_LEDGER_SCHEMA_VERSION = 1


def canonical_hypothesis_id(identity: dict[str, Any]) -> str:
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def register_hypotheses(
    path: str | Path,
    identities: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    ledger_path = Path(path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    records = {
        canonical_hypothesis_id(identity): identity
        for identity in identities
    }
    lock_path = ledger_path.with_suffix(ledger_path.suffix + ".lock")
    descriptor = _exclusive_lock(lock_path)
    try:
        payload = _load_ledger(ledger_path)
        hypotheses = payload["hypotheses"]
        added = []
        for hypothesis_id, identity in sorted(records.items()):
            existing = hypotheses.get(hypothesis_id)
            if existing is not None and existing != identity:
                raise ValueError(f"Hypothesis identity collision in ledger: {hypothesis_id}")
            if existing is None:
                hypotheses[hypothesis_id] = identity
                added.append(hypothesis_id)
        atomic_write_json(ledger_path, payload)
        return {
            "schema_version": HYPOTHESIS_LEDGER_SCHEMA_VERSION,
            "path": str(ledger_path),
            "hypothesis_count": len(hypotheses),
            "registered_ids": sorted(records),
            "new_ids": added,
        }
    finally:
        os.close(descriptor)
        lock_path.unlink(missing_ok=True)


def _exclusive_lock(path: Path) -> int:
    try:
        return os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise ValueError(f"Hypothesis ledger is locked: {path}") from exc


def _load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": HYPOTHESIS_LEDGER_SCHEMA_VERSION, "hypotheses": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid hypothesis ledger: {path}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != HYPOTHESIS_LEDGER_SCHEMA_VERSION:
        raise ValueError(f"Invalid hypothesis ledger schema: {path}")
    if not isinstance(payload.get("hypotheses"), dict):
        raise ValueError(f"Invalid hypothesis ledger hypotheses: {path}")
    return payload
