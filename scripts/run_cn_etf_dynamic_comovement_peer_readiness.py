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

from quant_robot.data.etf_point_in_time_universe import EtfEligibilityPolicy  # noqa: E402
from quant_robot.ops.cn_etf_dynamic_comovement_peer_readiness import (  # noqa: E402
    STAGE,
    build_cn_etf_dynamic_comovement_peer_readiness,
    write_cn_etf_dynamic_comovement_peer_readiness,
)
from quant_robot.research.dynamic_comovement_peer_source import DynamicPeerPolicy  # noqa: E402


DEFAULT_CONFIG = Path("configs/cn_etf_dynamic_comovement_peer_readiness_20260716.json")
EXPECTED_ELIGIBILITY_POLICY = {
    "min_prior_observations": 120,
    "liquidity_window": 20,
    "min_trailing_median_amount": 5_000_000.0,
    "max_stale_rate": 0.05,
    "max_abs_return": 0.20,
}
EXPECTED_PEER_POLICY = {
    "return_window": 120,
    "min_asset_return_observations": 100,
    "market_min_cross_section": 30,
    "beta_min_observations": 80,
    "pair_min_observations": 80,
    "min_correlation": 0.50,
    "max_peers": 5,
    "min_peers": 3,
    "rebalance_months": [1, 4, 7, 10],
    "residual_volatility_window": 60,
    "momentum_window": 60,
    "short_return_window": 5,
    "liquidity_window": 20,
}
EXPECTED_THRESHOLDS = {
    "min_qualifying_assets_per_date": 30,
    "min_qualifying_date_coverage": 0.80,
    "min_comparable_assets_per_transition": 30,
    "min_median_jaccard": 0.25,
    "min_median_retention": 0.40,
    "max_complete_churn_rate": 0.40,
    "min_reciprocity_rate": 0.30,
    "max_reference_edge_overlap": 0.50,
    "min_reference_edge_coverage": 0.80,
}
FALSE_BOUNDARY_KEYS = (
    "current_name_input_allowed",
    "official_2026_peer_mapping_allowed",
    "forward_return_calculation_allowed",
    "factor_generation_allowed",
    "prescreen_execution_allowed",
    "portfolio_grid_allowed",
    "walk_forward_allowed",
    "paper_signal_allowed",
    "broker_connection_allowed",
    "account_read_allowed",
    "order_placement_allowed",
    "live_trading_allowed",
)


def run_cn_etf_dynamic_comovement_peer_readiness_cli(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(config_path)
    payload = _load_and_validate_config(path)
    peer_payload = dict(payload["peer_policy"])
    peer_payload["rebalance_months"] = tuple(peer_payload["rebalance_months"])
    audit = build_cn_etf_dynamic_comovement_peer_readiness(
        data_root=payload["data_root"],
        metadata_root=payload.get("metadata_root"),
        analysis_start_date=payload["analysis_start_date"],
        analysis_end_date=payload["analysis_end_date"],
        eligibility_policy=EtfEligibilityPolicy(**payload["eligibility_policy"]),
        peer_policy=DynamicPeerPolicy(**peer_payload),
        **payload["thresholds"],
    )
    result = dict(audit.result)
    result["configuration"] = {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "stage": STAGE,
        "frozen_analysis_boundary": True,
        "frozen_eligibility_policy": True,
        "frozen_peer_policy": True,
        "frozen_thresholds": True,
        "all_execution_boundaries_false": True,
    }
    destination = Path(output_dir) if output_dir is not None else Path(payload["output_dir"])
    paths = write_cn_etf_dynamic_comovement_peer_readiness(
        destination,
        result=result,
        source=audit.source,
    )
    result["artifacts"] = {name: str(artifact) for name, artifact in paths.items()}
    return result


def _load_and_validate_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"CN ETF dynamic peer readiness config does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid CN ETF dynamic peer readiness config JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("CN ETF dynamic peer readiness config must be a JSON object")
    expected_values = {
        "stage": STAGE,
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_dynamic_comovement_peer_dislocation",
        "audit_scope": "lagged_market_residual_correlation_topk_peer_source",
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
            "eligibility_policy",
            "peer_policy",
            "thresholds",
            "output_dir",
        ),
    )
    start = pd.Timestamp(payload["analysis_start_date"])
    end = pd.Timestamp(payload["analysis_end_date"])
    holdout = pd.Timestamp(payload["final_holdout_start"])
    if start > end:
        raise ValueError("config analysis_start_date must be on or before analysis_end_date")
    if end >= holdout:
        raise ValueError("config analysis window cannot read the sealed final holdout")
    if payload["analysis_start_date"] != "2020-01-02" or payload["analysis_end_date"] != "2024-06-28":
        raise ValueError("config analysis dates do not match the frozen analysis boundary")
    if payload["final_holdout_start"] != "2026-01-01":
        raise ValueError("config final_holdout_start must be 2026-01-01")
    if payload.get("eligibility_policy") != EXPECTED_ELIGIBILITY_POLICY:
        raise ValueError("config does not match the frozen eligibility policy")
    if payload.get("peer_policy") != EXPECTED_PEER_POLICY:
        raise ValueError("config does not match the frozen peer policy")
    if payload.get("thresholds") != EXPECTED_THRESHOLDS:
        raise ValueError("config does not match the frozen readiness thresholds")
    for key in FALSE_BOUNDARY_KEYS:
        if payload.get(key) is not False:
            raise ValueError(f"config {key} must be false")
    metadata_root = payload.get("metadata_root")
    if metadata_root is not None and not isinstance(metadata_root, str):
        raise ValueError("config metadata_root must be a path string or null")
    return payload


def _require_keys(payload: Mapping[str, Any], keys: tuple[str, ...]) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise ValueError("config missing required keys: " + ", ".join(missing))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit lagged CN ETF dynamic co-movement peer-source readiness."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    result = run_cn_etf_dynamic_comovement_peer_readiness_cli(
        config_path=args.config,
        output_dir=args.output_dir,
    )
    print(
        json.dumps(
            {
                "stage": result.get("stage"),
                "status": result.get("status"),
                "blockers": result.get("gate", {}).get("blockers", []),
                "next_direction": result.get("next_direction"),
                "artifacts": result.get("artifacts", {}),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
