from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.cn_etf_dynamic_peer_dislocation_preregistration import (  # noqa: E402
    STATUS_READY,
    STAGE,
    build_cn_etf_dynamic_peer_dislocation_preregistration,
    write_cn_etf_dynamic_peer_dislocation_preregistration,
)
from quant_robot.storage.fingerprints import sha256_file  # noqa: E402
from quant_robot.validation.single_prescreen_authorization import (  # noqa: E402
    build_single_prescreen_authorization,
    write_single_prescreen_authorization,
)


DEFAULT_CONFIG = Path("configs/cn_etf_dynamic_peer_dislocation_preregistration_20260716.json")
FROZEN_SECTION_SHA256 = {
    "candidate": "57c469be037290a22b235ca72203db9e407a1e248b1564c95fb21477686d144c",
    "data_boundary": "eb17a26fb8c4da7325a47897ca514b6b51c0fa7fbd4b7184d8c9c0d6e623f564",
    "eligibility": "2136448986601ec1133cd96cb1ab0d0fffe7521f98149b5fc9b0c4c8ed481265",
    "evaluation": "bf63d511e98eb5c4ede4c81a63fc228677db268205c14b1804d8d4e5c26623ec",
    "reference_policy": "b71321579b345f35bca8c4a7c1888b3667645a2fac15a26b7669038305d8d88c",
    "capacity": "08487805cbb33ec81e89a34744ded4fee9312b7382c522ea23683893bbd7c7cc",
    "costs": "d2b44bd036bee0b9bd3675845f6202e3f06834d442c6c4fb91b4a8f9398ae013",
    "stop_policy": "68187f8cbc0c8ce59838044b64ad3b0c10529b40e7376007dbf96cc74d355bdb",
}
SOURCE_KEYS = ("mapping", "source_config", "source_result")
FALSE_BOUNDARY_KEYS = (
    "forward_return_read_allowed",
    "factor_generation_allowed",
    "prescreen_execution_allowed",
    "portfolio_grid_allowed",
    "walk_forward_allowed",
    "final_holdout_allowed",
    "promotion_allowed",
    "paper_signal_allowed",
    "broker_connection_allowed",
    "account_read_allowed",
    "order_placement_allowed",
    "live_trading_allowed",
    "live_boundary_allowed",
)


def run_cn_etf_dynamic_peer_dislocation_preregistration_cli(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(config_path)
    payload = _load_and_validate_config(path)
    config_sha256 = sha256_file(path)
    source_paths = _source_paths(payload)
    evidence_hashes = {name: sha256_file(source) for name, source in source_paths.items()}
    _validate_evidence_hashes(payload, evidence_hashes)
    source_readiness = _load_source_readiness(source_paths["source_result"])
    mapping_method = _validated_mapping_method(
        source_paths["mapping"],
        expected=payload["source_evidence"]["mapping_method"],
    )
    mapping_integrity = dict(source_readiness.get("mapping_integrity", {}))
    mapping_integrity["mapping_method"] = mapping_method
    source_readiness["mapping_integrity"] = mapping_integrity
    result = build_cn_etf_dynamic_peer_dislocation_preregistration(
        config=payload,
        source_readiness=source_readiness,
        evidence_hashes=evidence_hashes,
        config_sha256=config_sha256,
    )
    if result["status"] != STATUS_READY:
        raise ValueError(f"preregistration blocked: {result['summary']['blockers']}")
    destination = Path(output_dir) if output_dir is not None else Path(payload["output_dir"])
    paths = write_cn_etf_dynamic_peer_dislocation_preregistration(destination, result)
    result_sha256 = sha256_file(paths["json"])
    authorization = build_single_prescreen_authorization(
        registration_date=payload["registration_date"],
        candidate_name=payload["candidate"]["factor_name"],
        preregistration_config_sha256=config_sha256,
        preregistration_result_sha256=result_sha256,
        source_hashes=evidence_hashes,
    )
    authorization_path = write_single_prescreen_authorization(
        destination / payload["authorization_filename"],
        authorization,
    )
    paths["authorization"] = authorization_path
    result["artifacts"] = {name: str(artifact) for name, artifact in paths.items()}
    result["artifact_hashes"] = {
        "config": config_sha256,
        "result": result_sha256,
        "authorization": sha256_file(authorization_path),
        **{f"source_{key}": value for key, value in evidence_hashes.items()},
    }
    result["authorization"] = {
        "authorization_id": authorization["authorization_id"],
        "allowed_task": authorization["allowed_task"],
        "allowed_stage": authorization["allowed_stage"],
        "max_executions": authorization["max_executions"],
        "execution_ledger_path": payload["execution_ledger_path"],
        "execution_claim_recorded": False,
    }
    return result


def _load_and_validate_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"CN ETF dynamic peer preregistration config does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid CN ETF dynamic peer preregistration config JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("CN ETF dynamic peer preregistration config must be a JSON object")
    expected_values = {
        "stage": STAGE,
        "registration_date": "2026-07-16",
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_dynamic_comovement_peer_dislocation",
        "output_dir": "data/reports/cn_etf_dynamic_peer_dislocation_preregistration_20260716",
        "authorization_filename": "single_prescreen_authorization.json",
        "execution_ledger_path": "data/reports/cn_etf_dynamic_peer_dislocation_prescreen_execution_ledger.json",
    }
    for key, expected in expected_values.items():
        if payload.get(key) != expected:
            raise ValueError(f"config {key} does not match the frozen value")
    for section, expected_sha256 in FROZEN_SECTION_SHA256.items():
        if _canonical_sha256(payload.get(section)) != expected_sha256:
            label = section.replace("_", " ")
            raise ValueError(f"config does not match the frozen {label}")
    source = payload.get("source_evidence")
    if not isinstance(source, dict):
        raise ValueError("config does not contain frozen source evidence")
    if source.get("required_status") != "ready_for_peer_source_preregistration":
        raise ValueError("config does not match the frozen source evidence status")
    if source.get("mapping_method") != "lagged_market_residual_correlation_topk":
        raise ValueError("config does not match the frozen source evidence mapping method")
    _validate_source_mapping(source.get("paths"), label="paths", require_sha256=False)
    _validate_source_mapping(source.get("hashes"), label="hashes", require_sha256=True)
    for key in FALSE_BOUNDARY_KEYS:
        if payload.get(key) is not False:
            raise ValueError(f"config {key} must be false")
    return payload


def _source_paths(payload: Mapping[str, Any]) -> dict[str, Path]:
    values = payload["source_evidence"]["paths"]
    paths = {key: Path(values[key]) for key in SOURCE_KEYS}
    for key, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"frozen source evidence is missing for {key}: {path}")
    return paths


def _validate_evidence_hashes(
    payload: Mapping[str, Any],
    actual_hashes: Mapping[str, str],
) -> None:
    expected_hashes = payload["source_evidence"]["hashes"]
    for key in SOURCE_KEYS:
        if actual_hashes.get(key) != expected_hashes.get(key):
            raise ValueError(f"frozen source evidence hash mismatch: {key}")


def _load_source_readiness(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"frozen source readiness JSON is invalid: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"frozen source readiness JSON must be an object: {path}")
    return payload


def _validated_mapping_method(path: Path, *, expected: str) -> str:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "mapping_method" not in reader.fieldnames:
                raise ValueError(f"frozen source mapping is missing mapping_method: {path}")
            methods = {
                str(row.get("mapping_method", "")).strip()
                for row in reader
                if str(row.get("mapping_method", "")).strip()
            }
    except (OSError, csv.Error) as exc:
        raise ValueError(f"frozen source mapping CSV is invalid: {path}") from exc
    if methods != {expected}:
        raise ValueError(
            f"frozen source mapping method mismatch: expected {expected}, observed {sorted(methods)}"
        )
    return expected


def _validate_source_mapping(value: Any, *, label: str, require_sha256: bool) -> None:
    if not isinstance(value, dict) or tuple(sorted(value)) != SOURCE_KEYS:
        raise ValueError(f"config frozen source evidence {label} must contain exactly {SOURCE_KEYS}")
    for key in SOURCE_KEYS:
        item = value[key]
        if require_sha256:
            if not _is_sha256(item):
                raise ValueError(f"config frozen source evidence hash is invalid: {key}")
        elif not isinstance(item, str) or not item.strip():
            raise ValueError(f"config frozen source evidence path is invalid: {key}")


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Freeze one hash-bound CN ETF dynamic peer dislocation prescreen."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    result = run_cn_etf_dynamic_peer_dislocation_preregistration_cli(
        config_path=args.config,
        output_dir=args.output_dir,
    )
    print(
        json.dumps(
            {
                "stage": result.get("stage"),
                "status": result.get("status"),
                "candidate": result.get("candidate", {}).get("factor_name"),
                "blockers": result.get("summary", {}).get("blockers", []),
                "next_direction": result.get("next_direction"),
                "artifact_hashes": result.get("artifact_hashes", {}),
                "artifacts": result.get("artifacts", {}),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
