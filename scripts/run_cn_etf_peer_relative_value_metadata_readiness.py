from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

import pandas as pd  # noqa: E402

from quant_robot.ops.cn_etf_peer_relative_value_metadata_readiness import (  # noqa: E402
    STAGE,
    build_cn_etf_peer_relative_value_metadata_readiness,
    write_cn_etf_peer_relative_value_metadata_readiness,
)


DEFAULT_CONFIG = Path("configs/cn_etf_peer_relative_value_metadata_readiness_20260716.json")
EXPECTED_THRESHOLDS = {
    "min_peer_group_size": 2,
    "min_qualifying_assets_per_date": 30,
    "min_qualifying_date_coverage": 0.8,
}
FALSE_BOUNDARY_KEYS = (
    "name_only_mapping_allowed",
    "prescreen_execution_allowed",
    "portfolio_grid_allowed",
    "walk_forward_allowed",
    "paper_signal_allowed",
    "broker_connection_allowed",
    "account_read_allowed",
    "order_placement_allowed",
    "live_trading_allowed",
)


def run_cn_etf_peer_relative_value_metadata_readiness_cli(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(config_path)
    payload = _load_and_validate_config(path)
    thresholds = payload["thresholds"]
    result = build_cn_etf_peer_relative_value_metadata_readiness(
        data_root=payload["data_root"],
        peer_mapping_path=payload.get("peer_mapping_path"),
        analysis_start_date=payload["analysis_start_date"],
        analysis_end_date=payload["analysis_end_date"],
        min_peer_group_size=int(thresholds["min_peer_group_size"]),
        min_qualifying_assets_per_date=int(thresholds["min_qualifying_assets_per_date"]),
        min_qualifying_date_coverage=float(thresholds["min_qualifying_date_coverage"]),
    )
    result["configuration"] = {
        "stage": STAGE,
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "primary_market": payload["primary_market"],
        "research_family": payload["research_family"],
        "audit_scope": payload["audit_scope"],
        "thresholds_match_frozen_contract": True,
        "final_holdout_sealed": True,
        "boundary_keys_all_false": True,
    }
    destination = Path(output_dir) if output_dir is not None else Path(payload["output_dir"])
    paths = write_cn_etf_peer_relative_value_metadata_readiness(destination, result)
    result["artifacts"] = {name: str(artifact) for name, artifact in paths.items()}
    return result


def _load_and_validate_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"CN ETF peer-relative-value metadata config does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid CN ETF peer-relative-value metadata config JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("CN ETF peer-relative-value metadata config must be a JSON object")
    expected_values = {
        "stage": STAGE,
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_peer_relative_value",
        "audit_scope": "point_in_time_official_peer_mapping",
    }
    for key, expected in expected_values.items():
        if payload.get(key) != expected:
            raise ValueError(f"config {key} must be {expected}")
    _require_keys(
        payload,
        (
            "data_root",
            "analysis_start_date",
            "analysis_end_date",
            "final_holdout_start",
            "thresholds",
            "output_dir",
        ),
    )
    if payload.get("thresholds") != EXPECTED_THRESHOLDS:
        raise ValueError("config thresholds do not match the frozen metadata-readiness contract")
    start = pd.Timestamp(payload["analysis_start_date"])
    end = pd.Timestamp(payload["analysis_end_date"])
    holdout = pd.Timestamp(payload["final_holdout_start"])
    if start > end:
        raise ValueError("config analysis_start_date must be on or before analysis_end_date")
    if end >= holdout:
        raise ValueError("config analysis window cannot read the sealed final holdout")
    for key in FALSE_BOUNDARY_KEYS:
        if payload.get(key) is not False:
            raise ValueError(f"config {key} must be false")
    mapping_path = payload.get("peer_mapping_path")
    if mapping_path is not None and not isinstance(mapping_path, str):
        raise ValueError("config peer_mapping_path must be a path string or null")
    return payload


def _require_keys(payload: Mapping[str, Any], keys: tuple[str, ...]) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise ValueError(f"config missing required keys: {', '.join(missing)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit CN ETF point-in-time peer metadata readiness.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    result = run_cn_etf_peer_relative_value_metadata_readiness_cli(
        config_path=Path(args.config),
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    print(
        json.dumps(
            {
                "stage": result.get("stage"),
                "status": result.get("status"),
                "blockers": result.get("gate", {}).get("blockers", []),
                "capability_gaps": result.get("capability_gaps", []),
                "next_direction": result.get("next_direction"),
                "artifacts": result.get("artifacts", {}),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
