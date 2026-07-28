from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.cn_etf_fund_structure_crowding_preregistration import (  # noqa: E402
    STAGE,
    STATUS_READY,
    build_cn_etf_fund_structure_crowding_preregistration,
    write_cn_etf_fund_structure_crowding_preregistration,
)
from quant_robot.storage.fingerprints import sha256_file  # noqa: E402
from quant_robot.validation.single_prescreen_authorization import (  # noqa: E402
    build_single_prescreen_authorization,
    write_single_prescreen_authorization,
)


DEFAULT_CONFIG = Path(
    "configs/cn_etf_fund_structure_crowding_preregistration_20260728.json"
)
PRESCREEN_STAGE = "cn_etf_fund_structure_crowding_prescreen"
SOURCE_KEYS = (
    "source_config",
    "source_result",
    "canonical_2020",
    "canonical_2021",
    "canonical_2022",
    "canonical_2023",
    "canonical_2024",
)
FROZEN_SECTION_SHA256 = {
    "candidate": "a61b1d23f252395f20a7d563fcc453ea9b80863f0144b72cbce3c9598eb2750e",
    "data_boundary": "bb0167d7b3dd34ea372659742984d46bb5f80cf3a8e9ac42520d621f6da4330e",
    "eligibility": "6ab751271e33af84f3e4dbcd658eae6cf77f0ce94b9ecec2c40216f1491f3b08",
    "evaluation": "bf63d511e98eb5c4ede4c81a63fc228677db268205c14b1804d8d4e5c26623ec",
    "reference_policy": "4b2d07f8159af09512192bbb3c2a9964c618c4829c61ff3966b8468138e035f3",
    "capacity": "08487805cbb33ec81e89a34744ded4fee9312b7382c522ea23683893bbd7c7cc",
    "costs": "d2b44bd036bee0b9bd3675845f6202e3f06834d442c6c4fb91b4a8f9398ae013",
    "stop_policy": "249a23772659b656ffb3abbe6f667edce7117ac720f3c6084bcf312583ffdcb5",
}
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


def run_cn_etf_fund_structure_crowding_preregistration_cli(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(config_path)
    config = _load_and_validate_config(path)
    config_sha256 = sha256_file(path)
    source_paths = _source_paths(config)
    evidence_hashes = {
        key: sha256_file(source_paths[key])
        for key in SOURCE_KEYS
    }
    _validate_evidence_hashes(config, evidence_hashes)
    source_readiness = _load_json_object(
        source_paths["source_result"],
        "fund-structure source readiness",
    )
    result = build_cn_etf_fund_structure_crowding_preregistration(
        config=config,
        source_readiness=source_readiness,
        evidence_hashes=evidence_hashes,
        config_sha256=config_sha256,
    )
    if result["status"] != STATUS_READY:
        raise ValueError(f"preregistration blocked: {result['summary']['blockers']}")
    destination = Path(output_dir) if output_dir is not None else Path(config["output_dir"])
    paths = write_cn_etf_fund_structure_crowding_preregistration(destination, result)
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
    payload = _load_json_object(path, "fund-structure crowding preregistration config")
    expected = {
        "stage": STAGE,
        "registration_date": "2026-07-28",
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_fund_structure",
        "output_dir": "data/reports/cn_etf_fund_structure_crowding_preregistration_20260728",
        "authorization_filename": "single_prescreen_authorization.json",
        "execution_ledger_path": (
            "data/reports/"
            "cn_etf_fund_structure_crowding_prescreen_execution_ledger.json"
        ),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(f"config {key} does not match the frozen value")
    for section, expected_hash in FROZEN_SECTION_SHA256.items():
        if _canonical_sha256(payload.get(section)) != expected_hash:
            raise ValueError(
                f"config does not match the frozen {section.replace('_', ' ')}"
            )
    source = payload.get("source_evidence")
    if not isinstance(source, dict):
        raise ValueError("config does not contain frozen source evidence")
    if source.get("required_status") != "ready_for_fund_structure_preregistration":
        raise ValueError("config does not match the frozen source evidence status")
    _validate_source_mapping(source.get("paths"), label="paths", hashes=False)
    _validate_source_mapping(source.get("hashes"), label="hashes", hashes=True)
    for key in FALSE_BOUNDARY_KEYS:
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
    actual_hashes: Mapping[str, str],
) -> None:
    expected = config["source_evidence"]["hashes"]
    for key in SOURCE_KEYS:
        if actual_hashes.get(key) != expected.get(key):
            raise ValueError(f"frozen source evidence hash mismatch: {key}")


def _validate_source_mapping(
    value: Any,
    *,
    label: str,
    hashes: bool,
) -> None:
    if not isinstance(value, dict) or set(value) != set(SOURCE_KEYS):
        raise ValueError(
            f"config frozen source evidence {label} must contain exactly {SOURCE_KEYS}"
        )
    for key in SOURCE_KEYS:
        item = value[key]
        if hashes and not _is_sha256(item):
            raise ValueError(f"config frozen source evidence hash is invalid: {key}")
        if not hashes and (not isinstance(item, str) or not item.strip()):
            raise ValueError(f"config frozen source evidence path is invalid: {key}")


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
        description="Freeze one hash-bound CN ETF fund-structure crowding prescreen."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    result = run_cn_etf_fund_structure_crowding_preregistration_cli(
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
