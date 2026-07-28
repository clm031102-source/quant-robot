from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.cn_etf_margin_positioning_preregistration import (  # noqa: E402
    BOUNDARY_FIELDS,
    FACTOR_NAME,
    STAGE,
    STATUS_READY,
    build_cn_etf_margin_positioning_preregistration,
    write_cn_etf_margin_positioning_preregistration,
)
from quant_robot.storage.fingerprints import sha256_file  # noqa: E402
from quant_robot.validation.single_prescreen_authorization import (  # noqa: E402
    build_single_prescreen_authorization,
    write_single_prescreen_authorization,
)


DEFAULT_CONFIG = Path("configs/cn_etf_margin_positioning_preregistration_20260728.json")
PRESCREEN_STAGE = "cn_etf_margin_positioning_prescreen"
SOURCE_KEYS = (
    "source_config",
    "source_result",
    "manifest",
    "date_coverage",
    "canonical_2020",
    "canonical_2021",
    "canonical_2022",
    "canonical_2023",
    "canonical_2024",
)


def run_cn_etf_margin_positioning_preregistration_cli(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(config_path)
    config = _load_and_validate_config(path)
    config_sha256 = sha256_file(path)
    source_paths = _source_paths(config)
    evidence_hashes = {key: sha256_file(source_paths[key]) for key in SOURCE_KEYS}
    _validate_evidence_hashes(config, evidence_hashes)
    source_readiness = _load_json_object(
        source_paths["source_result"],
        "margin-positioning source readiness",
    )
    result = build_cn_etf_margin_positioning_preregistration(
        config=config,
        source_readiness=source_readiness,
        evidence_hashes=evidence_hashes,
        config_sha256=config_sha256,
    )
    if result["status"] != STATUS_READY:
        raise ValueError(f"preregistration blocked: {result['summary']['blockers']}")
    destination = Path(output_dir or config["output_dir"])
    paths = write_cn_etf_margin_positioning_preregistration(destination, result)
    result_sha256 = sha256_file(paths["json"])
    authorization = build_single_prescreen_authorization(
        registration_date=config["registration_date"],
        candidate_name=FACTOR_NAME,
        preregistration_config_sha256=config_sha256,
        preregistration_result_sha256=result_sha256,
        source_hashes=evidence_hashes,
        execution_ledger_path=config["execution_ledger_path"],
        allowed_stage=PRESCREEN_STAGE,
        source_hash_keys=SOURCE_KEYS,
    )
    authorization_path = write_single_prescreen_authorization(
        destination / config["authorization_filename"],
        authorization,
    )
    paths["authorization"] = authorization_path
    result["artifacts"] = {name: str(value) for name, value in paths.items()}
    result["artifact_hashes"] = {
        "config": config_sha256,
        "result": result_sha256,
        "authorization": sha256_file(authorization_path),
        **evidence_hashes,
    }
    result["authorization"] = {
        "authorization_id": authorization["authorization_id"],
        "allowed_task": authorization["allowed_task"],
        "allowed_stage": authorization["allowed_stage"],
        "max_executions": authorization["max_executions"],
        "execution_ledger_path": config["execution_ledger_path"],
        "execution_claim_recorded": False,
    }
    return result


def _load_and_validate_config(path: Path) -> dict[str, Any]:
    payload = _load_json_object(path, "margin-positioning preregistration config")
    expected = {
        "stage": STAGE,
        "registration_date": "2026-07-28",
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_margin_positioning",
        "output_dir": "data/reports/cn_etf_margin_positioning_preregistration_20260728",
        "authorization_filename": "single_prescreen_authorization.json",
        "execution_ledger_path": (
            "data/reports/cn_etf_margin_positioning_prescreen_execution_ledger.json"
        ),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(f"config {key} does not match the frozen value")
    source = payload.get("source_evidence")
    if not isinstance(source, dict):
        raise ValueError("config does not contain frozen source evidence")
    if source.get("required_status") != "ready_for_margin_positioning_preregistration":
        raise ValueError("config does not match the frozen source status")
    _validate_source_mapping(source.get("paths"), hashes=False)
    _validate_source_mapping(source.get("hashes"), hashes=True)
    if payload.get("candidate", {}).get("factor_name") != FACTOR_NAME:
        raise ValueError("config candidate does not match the frozen factor")
    if payload.get("evaluation", {}).get("horizons") != [5, 20]:
        raise ValueError("config evaluation horizons are not frozen")
    for key in BOUNDARY_FIELDS:
        if payload.get(key) is not False:
            raise ValueError(f"config {key} must be false")
    return payload


def _source_paths(config: Mapping[str, Any]) -> dict[str, Path]:
    values = config["source_evidence"]["paths"]
    paths = {key: Path(values[key]) for key in SOURCE_KEYS}
    for key, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"frozen source evidence is missing for {key}: {path}")
    return paths


def _validate_evidence_hashes(
    config: Mapping[str, Any],
    actual: Mapping[str, str],
) -> None:
    expected = config["source_evidence"]["hashes"]
    for key in SOURCE_KEYS:
        if actual.get(key) != expected.get(key):
            raise ValueError(f"frozen source evidence hash mismatch: {key}")


def _validate_source_mapping(value: Any, *, hashes: bool) -> None:
    if not isinstance(value, dict) or set(value) != set(SOURCE_KEYS):
        raise ValueError(f"source evidence must contain exactly {SOURCE_KEYS}")
    for key in SOURCE_KEYS:
        item = value[key]
        if hashes and not _is_sha256(item):
            raise ValueError(f"source evidence hash is invalid: {key}")
        if not hashes and (not isinstance(item, str) or not item.strip()):
            raise ValueError(f"source evidence path is invalid: {key}")


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid {label} JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return payload


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Freeze one hash-bound CN ETF margin-positioning prescreen."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    result = run_cn_etf_margin_positioning_preregistration_cli(
        config_path=args.config,
        output_dir=args.output_dir,
    )
    print(
        json.dumps(
            {
                "stage": result["stage"],
                "status": result["status"],
                "candidate": result["candidate"]["factor_name"],
                "blockers": result["summary"]["blockers"],
                "artifact_hashes": result["artifact_hashes"],
                "artifacts": result["artifacts"],
                "authorization": result["authorization"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
