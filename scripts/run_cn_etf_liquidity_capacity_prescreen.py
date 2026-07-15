from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

import pandas as pd  # noqa: E402

from quant_robot.data.etf_point_in_time_universe import EtfEligibilityPolicy  # noqa: E402
from quant_robot.factors.etf_liquidity_capacity import (  # noqa: E402
    ETF_LIQUIDITY_CAPACITY_FACTOR_NAMES,
    ETF_LIQUIDITY_REFERENCE_FACTOR_NAMES,
)
from quant_robot.ops.cn_etf_liquidity_capacity_prescreen import (  # noqa: E402
    DEFAULT_HORIZONS,
    STAGE,
    build_cn_etf_liquidity_capacity_prescreen,
    write_cn_etf_liquidity_capacity_prescreen,
)


DEFAULT_CONFIG = Path("configs/cn_etf_liquidity_capacity_prescreen_20260716.json")
BOUNDARY_KEYS = (
    "portfolio_grid_allowed",
    "walk_forward_allowed",
    "paper_signal_allowed",
    "broker_connection_allowed",
    "account_read_allowed",
    "order_placement_allowed",
    "live_trading_allowed",
)
EXPECTED_ZERO_LEAD_BUDGETS = {
    "cn_etf_volatility_regime": 0.35,
    "cn_etf_flow_breadth_aggregation": 0.35,
    "cn_etf_fund_structure": 0.30,
}


def run_cn_etf_liquidity_capacity_prescreen_cli(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(config_path)
    payload = _load_and_validate_config(path)
    eligibility = payload["eligibility"]
    thresholds = payload["thresholds"]
    capacity = payload["capacity"]
    result = build_cn_etf_liquidity_capacity_prescreen(
        data_root=payload["data_root"],
        metadata_root=payload["metadata_root"],
        legacy_promotion_report=payload["legacy_promotion_report"],
        analysis_start_date=payload["analysis_start_date"],
        analysis_end_date=payload["analysis_end_date"],
        horizons=tuple(int(value) for value in payload["horizons"]),
        execution_lag=int(payload["execution_lag"]),
        eligibility_policy=EtfEligibilityPolicy(
            min_prior_observations=int(eligibility["min_prior_observations"]),
            liquidity_window=int(eligibility["liquidity_window"]),
            min_trailing_median_amount=float(eligibility["min_trailing_median_amount"]),
            max_stale_rate=float(eligibility["max_stale_rate"]),
            max_abs_return=float(eligibility["max_abs_return"]),
        ),
        min_cross_section=int(thresholds["min_cross_section"]),
        min_ic_observations=int(thresholds["min_ic_observations"]),
        min_year_ic_observations=int(thresholds["min_year_ic_observations"]),
        min_usable_years=int(thresholds["min_usable_years"]),
        alpha=float(thresholds["alpha"]),
        min_mean_rank_ic=float(thresholds["min_mean_rank_ic"]),
        min_icir=float(thresholds["min_icir"]),
        min_positive_ic_rate=float(thresholds["min_positive_ic_rate"]),
        min_quantile_monotonicity=float(thresholds["min_quantile_monotonicity"]),
        max_top_quantile_turnover=float(thresholds["max_top_quantile_turnover"]),
        min_positive_year_rate=float(thresholds["min_positive_year_rate"]),
        max_abs_reference_correlation=float(thresholds["max_abs_reference_correlation"]),
        portfolio_value_cny=float(capacity["portfolio_value_cny"]),
        position_count=int(capacity["position_count"]),
        max_one_way_participation_rate=float(capacity["max_one_way_participation_rate"]),
    )
    result["configuration"] = {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "primary_market": payload["primary_market"],
        "candidate_names_match_frozen_contract": True,
        "reference_names_match_frozen_contract": True,
        "capacity_contract_match": True,
        "zero_lead_decision_match": True,
        "boundary_keys_all_false": True,
    }
    result["zero_lead_decision"] = payload["zero_lead_decision"]
    destination = Path(output_dir) if output_dir is not None else Path(payload["output_dir"])
    paths = write_cn_etf_liquidity_capacity_prescreen(destination, result)
    result["artifacts"] = {name: str(artifact_path) for name, artifact_path in paths.items()}
    return result


def _load_and_validate_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"CN ETF liquidity-capacity config does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid CN ETF liquidity-capacity config JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("CN ETF liquidity-capacity config must be a JSON object")
    if payload.get("stage") != STAGE:
        raise ValueError(f"config stage must be {STAGE}")
    if payload.get("primary_market") != "CN_ETF":
        raise ValueError("config primary_market must be CN_ETF")
    if payload.get("research_family") != "cn_etf_liquidity_capacity":
        raise ValueError("config research_family must be cn_etf_liquidity_capacity")
    if tuple(payload.get("candidate_names", ())) != ETF_LIQUIDITY_CAPACITY_FACTOR_NAMES:
        raise ValueError("config candidate_names do not match the frozen liquidity-capacity contract")
    if tuple(payload.get("reference_names", ())) != ETF_LIQUIDITY_REFERENCE_FACTOR_NAMES:
        raise ValueError("config reference_names do not match the frozen historical-reference contract")
    if tuple(int(value) for value in payload.get("horizons", ())) != DEFAULT_HORIZONS:
        raise ValueError(f"config horizons must be {list(DEFAULT_HORIZONS)}")
    if int(payload.get("execution_lag", -1)) != 1:
        raise ValueError("config execution_lag must be 1")
    if pd.Timestamp(payload.get("analysis_end_date")) >= pd.Timestamp("2026-01-01"):
        raise ValueError("config analysis_end_date cannot read the sealed 2026 final holdout")

    eligibility = payload.get("eligibility")
    thresholds = payload.get("thresholds")
    capacity = payload.get("capacity")
    zero_lead = payload.get("zero_lead_decision")
    if not isinstance(eligibility, dict) or not eligibility.get("point_in_time"):
        raise ValueError("config must require point-in-time ETF eligibility")
    if not eligibility.get("official_etf_only"):
        raise ValueError("config must require official ETF metadata")
    if not isinstance(thresholds, dict):
        raise ValueError("config thresholds must be a JSON object")
    if not isinstance(capacity, dict):
        raise ValueError("config capacity must be a JSON object")
    if not isinstance(zero_lead, dict):
        raise ValueError("config zero_lead_decision must be a JSON object")

    _require_keys(
        payload,
        (
            "data_root",
            "metadata_root",
            "legacy_promotion_report",
            "analysis_start_date",
            "analysis_end_date",
            "output_dir",
        ),
        "config",
    )
    _require_keys(
        eligibility,
        (
            "min_prior_observations",
            "liquidity_window",
            "min_trailing_median_amount",
            "max_stale_rate",
            "max_abs_return",
        ),
        "config eligibility",
    )
    _require_keys(
        thresholds,
        (
            "alpha",
            "min_cross_section",
            "min_ic_observations",
            "min_year_ic_observations",
            "min_usable_years",
            "min_mean_rank_ic",
            "min_icir",
            "min_positive_ic_rate",
            "min_quantile_monotonicity",
            "max_top_quantile_turnover",
            "min_positive_year_rate",
            "max_abs_reference_correlation",
        ),
        "config thresholds",
    )
    _require_keys(
        capacity,
        (
            "amount_unit",
            "adv_window",
            "portfolio_value_cny",
            "position_count",
            "max_one_way_participation_rate",
            "top_quantile_adv20_percentile",
            "required_capacity_coverage_rate",
        ),
        "config capacity",
    )
    if capacity["amount_unit"] != "CNY" or int(capacity["adv_window"]) != 20:
        raise ValueError("config capacity must use CNY amount and ADV20")
    if float(capacity["top_quantile_adv20_percentile"]) != 0.10:
        raise ValueError("config top_quantile_adv20_percentile must be 0.1")
    if float(capacity["required_capacity_coverage_rate"]) != 1.0:
        raise ValueError("config required_capacity_coverage_rate must be 1.0")
    if zero_lead.get("closed_family") != "cn_etf_liquidity_capacity":
        raise ValueError("config zero-lead closed_family must be cn_etf_liquidity_capacity")
    if float(zero_lead.get("closed_budget_share", -1.0)) != 0.35:
        raise ValueError("config zero-lead closed_budget_share must be 0.35")
    observed_budgets = zero_lead.get("resulting_budget_shares")
    if observed_budgets != EXPECTED_ZERO_LEAD_BUDGETS:
        raise ValueError("config zero-lead resulting budget shares do not match the frozen contract")
    for key in BOUNDARY_KEYS:
        if payload.get(key) is not False:
            raise ValueError(f"config {key} must be explicitly false")
    return payload


def _require_keys(payload: dict[str, Any], keys: tuple[str, ...], label: str) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise ValueError(f"{label} is missing keys: {', '.join(missing)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the frozen CN ETF liquidity-capacity statistical prescreen.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    result = run_cn_etf_liquidity_capacity_prescreen_cli(
        config_path=Path(args.config),
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    print(
        json.dumps(
            {
                "stage": result["stage"],
                "status": result["status"],
                "summary": result["summary"],
                "decision": result["decision"],
                "output_dir": str(Path(result["artifacts"]["json"]).parent),
            },
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
