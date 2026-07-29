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

from quant_robot.ops.cn_etf_delayed_nav_premium_preregistration import (  # noqa: E402
    BOUNDARY_KEYS,
    EXPECTED_CANDIDATE,
    EXPECTED_CAPACITY,
    EXPECTED_COSTS,
    EXPECTED_EVALUATION,
    STAGE,
    STATUS_READY,
    build_cn_etf_delayed_nav_premium_preregistration,
    write_cn_etf_delayed_nav_premium_preregistration,
)
from quant_robot.storage.fingerprints import sha256_file  # noqa: E402
from quant_robot.validation.single_prescreen_authorization import (  # noqa: E402
    build_single_prescreen_authorization,
    write_single_prescreen_authorization,
)


DEFAULT_CONFIG = Path(
    "configs/cn_etf_delayed_nav_premium_innovation_reversal_60_20260729.json"
)
PRESCREEN_STAGE = "cn_etf_delayed_nav_premium_prescreen"
SOURCE_KEYS = (
    "source_config",
    "source_result",
    "request_manifest",
    "canonical_nav",
    "session_coverage",
    "nav_agreement",
    "small_capital_inputs",
)


def run_cn_etf_delayed_nav_premium_preregistration_cli(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(config_path)
    config = _load_and_validate_config(path)
    source_paths = {
        key: Path(config["source_evidence"]["paths"][key])
        for key in SOURCE_KEYS
    }
    for key, source_path in source_paths.items():
        if not source_path.is_file():
            raise FileNotFoundError(f"frozen source evidence is missing for {key}: {source_path}")
    evidence_hashes = {key: sha256_file(source_paths[key]) for key in SOURCE_KEYS}
    expected_hashes = config["source_evidence"]["hashes"]
    for key in SOURCE_KEYS:
        if evidence_hashes[key] != expected_hashes[key]:
            raise ValueError(f"frozen source evidence hash mismatch: {key}")
    source_readiness = _load_json(
        source_paths["source_result"],
        "Tushare NAV source readiness",
    )
    config_sha256 = sha256_file(path)
    result = build_cn_etf_delayed_nav_premium_preregistration(
        config=config,
        source_readiness=source_readiness,
        evidence_hashes=evidence_hashes,
        config_sha256=config_sha256,
    )
    if result["status"] != STATUS_READY:
        raise ValueError(f"preregistration blocked: {result['summary']['blockers']}")
    destination = Path(output_dir) if output_dir is not None else Path(config["output_dir"])
    paths = write_cn_etf_delayed_nav_premium_preregistration(destination, result)
    result_sha256 = sha256_file(paths["json"])
    authorization = build_single_prescreen_authorization(
        registration_date=config["registration_date"],
        candidate_name=config["candidate"]["factor_name"],
        preregistration_config_sha256=config_sha256,
        preregistration_result_sha256=result_sha256,
        source_hashes=evidence_hashes,
        execution_ledger_path=config["execution_ledger_path"],
        allowed_stage=PRESCREEN_STAGE,
        source_hash_keys=SOURCE_KEYS,
        primary_horizon=1,
        diagnostic_horizon=5,
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
        "primary_horizon": authorization["primary_horizon"],
        "diagnostic_horizon": authorization["diagnostic_horizon"],
        "max_executions": authorization["max_executions"],
        "execution_ledger_path": authorization["execution_ledger_path"],
        "execution_claim_recorded": False,
    }
    return result


def _load_and_validate_config(path: Path) -> dict[str, Any]:
    config = _load_json(path, "delayed-NAV premium preregistration config")
    expected = {
        "stage": STAGE,
        "registration_date": "2026-07-29",
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_nav_premium_relative_value",
        "output_dir": "data/reports/cn_etf_delayed_nav_premium_preregistration_20260729",
        "authorization_filename": "single_prescreen_authorization.json",
        "execution_ledger_path": (
            "data/reports/cn_etf_delayed_nav_premium_prescreen_execution_ledger.json"
        ),
    }
    for key, value in expected.items():
        if config.get(key) != value:
            raise ValueError(f"config {key} does not match the frozen value")
    if config.get("candidate") != EXPECTED_CANDIDATE:
        raise ValueError("config candidate does not match the frozen contract")
    if config.get("evaluation") != EXPECTED_EVALUATION:
        raise ValueError("config evaluation does not match the frozen contract")
    if config.get("costs") != EXPECTED_COSTS:
        raise ValueError("config costs do not match the frozen contract")
    if config.get("capacity") != EXPECTED_CAPACITY:
        raise ValueError("config capacity does not match the frozen contract")
    stop_policy = config.get("stop_policy", {})
    if (
        stop_policy.get("candidate_count") != 1
        or stop_policy.get("hypothesis_count") != 1
        or stop_policy.get("single_prescreen_run_limit") != 1
        or stop_policy.get("diagnostic_horizon_can_rescue_primary") is not False
        or stop_policy.get("final_holdout_remains_sealed") is not True
    ):
        raise ValueError("config stop policy does not match the frozen contract")
    boundaries = config.get("boundaries")
    if not isinstance(boundaries, dict) or set(boundaries) != set(BOUNDARY_KEYS):
        raise ValueError("config boundaries do not match the frozen contract")
    for key in BOUNDARY_KEYS:
        if boundaries.get(key) is not False:
            raise ValueError(f"config boundary {key} must be false")
    source = config.get("source_evidence")
    if not isinstance(source, dict):
        raise ValueError("config source evidence must be an object")
    if source.get("required_status") != "ready_for_nav_premium_preregistration":
        raise ValueError("config source evidence status does not match the frozen contract")
    for label in ("paths", "hashes"):
        values = source.get(label)
        if not isinstance(values, dict) or set(values) != set(SOURCE_KEYS):
            raise ValueError(f"config source evidence {label} does not match the frozen key set")
    for key, value in source["hashes"].items():
        if not _is_sha256(value):
            raise ValueError(f"config source evidence hash is invalid: {key}")
    data_boundary = config.get("data_boundary", {})
    if (
        data_boundary.get("analysis_start_date") != "2020-01-02"
        or data_boundary.get("analysis_end_date") != "2024-06-28"
        or data_boundary.get("final_holdout_start") != "2026-01-01"
        or data_boundary.get("current_name_input_allowed") is not False
        or data_boundary.get("current_theme_input_allowed") is not False
    ):
        raise ValueError("config data boundary does not match the frozen contract")
    return config


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid {label}: {path}") from exc
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
        description="Freeze one hash-bound delayed-NAV premium prescreen."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    result = run_cn_etf_delayed_nav_premium_preregistration_cli(
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
