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
from quant_robot.factors.etf_market_residual_volatility import (  # noqa: E402
    ETF_MARKET_RESIDUAL_VOLATILITY_FACTOR_NAMES,
    ETF_MARKET_RESIDUAL_VOLATILITY_REFERENCE_NAMES,
)
from quant_robot.ops.cn_etf_market_residual_volatility_prescreen import (  # noqa: E402
    DEFAULT_HORIZONS,
    STAGE,
    build_cn_etf_market_residual_volatility_prescreen,
    write_cn_etf_market_residual_volatility_prescreen,
)


DEFAULT_CONFIG = Path("configs/cn_etf_market_residual_volatility_prescreen_20260716.json")
BOUNDARY_KEYS = (
    "sign_flip_rescue_allowed",
    "parameter_rescue_allowed",
    "window_tuning_allowed",
    "threshold_relaxation_allowed",
    "regime_rescue_allowed",
    "portfolio_grid_allowed",
    "walk_forward_allowed",
    "paper_signal_allowed",
    "broker_connection_allowed",
    "account_read_allowed",
    "order_placement_allowed",
    "live_trading_allowed",
)
EXPECTED_CANDIDATE_PARAMETERS = {
    "beta_window": 120,
    "beta_min_observations": 80,
    "downside_beta_window": 120,
    "downside_beta_min_observations": 24,
    "residual_window": 60,
    "residual_min_observations": 40,
    "residual_model_lag": 1,
    "include_intercept": True,
}
EXPECTED_ELIGIBILITY = {
    "point_in_time": True,
    "official_etf_only": True,
    "min_prior_observations": 252,
    "liquidity_window": 20,
    "min_trailing_median_amount": 5_000_000.0,
    "max_stale_rate": 0.05,
    "max_abs_return": 0.20,
}
EXPECTED_MARKET_PROXY = {
    "method": "point_in_time_eligible_cross_sectional_median_return",
    "min_cross_section": 30,
}
EXPECTED_THRESHOLDS = {
    "alpha": 0.05,
    "min_cross_section": 30,
    "min_ic_observations": 20,
    "min_year_ic_observations": 20,
    "min_usable_years": 3,
    "min_mean_rank_ic": 0.02,
    "min_icir": 0.30,
    "min_positive_ic_rate": 0.55,
    "min_quantile_monotonicity": 0.70,
    "max_top_quantile_turnover": 0.90,
    "min_positive_year_rate": 0.60,
    "max_abs_reference_correlation": 0.85,
}
EXPECTED_CAPACITY = {
    "amount_unit": "CNY",
    "adv_window": 20,
    "portfolio_value_cny": 1_000_000.0,
    "position_count": 10,
    "max_one_way_participation_rate": 0.01,
    "top_quantile_adv20_percentile": 0.10,
    "required_capacity_coverage_rate": 1.0,
}
EXPECTED_MULTIPLE_TESTING = {
    "method": "benjamini_hochberg",
    "scope": "all_frozen_candidate_horizon_tests",
}
EXPECTED_ZERO_LEAD_BUDGETS = {
    "cn_etf_flow_breadth_aggregation": 0.35,
    "cn_etf_fund_structure": 0.35,
    "cn_etf_peer_relative_value": 0.30,
}


def run_cn_etf_market_residual_volatility_prescreen_cli(
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(config_path)
    payload = _load_and_validate_config(path)
    eligibility = payload["eligibility"]
    thresholds = payload["thresholds"]
    capacity = payload["capacity"]
    market_proxy = payload["market_proxy"]
    parameters = payload["candidate_parameters"]
    result = build_cn_etf_market_residual_volatility_prescreen(
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
        market_proxy_min_cross_section=int(market_proxy["min_cross_section"]),
        beta_window=int(parameters["beta_window"]),
        beta_min_observations=int(parameters["beta_min_observations"]),
        downside_beta_window=int(parameters["downside_beta_window"]),
        downside_beta_min_observations=int(parameters["downside_beta_min_observations"]),
        residual_window=int(parameters["residual_window"]),
        residual_min_observations=int(parameters["residual_min_observations"]),
        residual_model_lag=int(parameters["residual_model_lag"]),
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
        "candidate_parameters_match_frozen_contract": True,
        "reference_names_match_frozen_contract": True,
        "capacity_contract_match": True,
        "zero_lead_decision_match": True,
        "boundary_keys_all_false": True,
    }
    result["zero_lead_decision"] = payload["zero_lead_decision"]
    destination = Path(output_dir) if output_dir is not None else Path(payload["output_dir"])
    paths = write_cn_etf_market_residual_volatility_prescreen(destination, result)
    result["artifacts"] = {name: str(artifact_path) for name, artifact_path in paths.items()}
    return result


def _load_and_validate_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"CN ETF residual-volatility config does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid CN ETF residual-volatility config JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("CN ETF residual-volatility config must be a JSON object")
    if payload.get("stage") != STAGE:
        raise ValueError(f"config stage must be {STAGE}")
    if payload.get("primary_market") != "CN_ETF":
        raise ValueError("config primary_market must be CN_ETF")
    if payload.get("research_family") != "cn_etf_volatility_regime":
        raise ValueError("config research_family must be cn_etf_volatility_regime")
    if payload.get("research_scope") != "market_residual_volatility_asymmetry_last_chance":
        raise ValueError("config research_scope must remain the frozen last-chance residual scope")
    if tuple(payload.get("candidate_names", ())) != ETF_MARKET_RESIDUAL_VOLATILITY_FACTOR_NAMES:
        raise ValueError("config candidate_names do not match the frozen residual-volatility contract")
    if tuple(payload.get("reference_names", ())) != ETF_MARKET_RESIDUAL_VOLATILITY_REFERENCE_NAMES:
        raise ValueError("config reference_names do not match the frozen historical-reference contract")
    if tuple(int(value) for value in payload.get("horizons", ())) != DEFAULT_HORIZONS:
        raise ValueError(f"config horizons must be {list(DEFAULT_HORIZONS)}")
    if int(payload.get("execution_lag", -1)) != 1:
        raise ValueError("config execution_lag must be 1")
    if payload.get("final_holdout_start") != "2026-01-01":
        raise ValueError("config final_holdout_start must be 2026-01-01")
    if pd.Timestamp(payload.get("analysis_end_date")) >= pd.Timestamp("2026-01-01"):
        raise ValueError("config analysis_end_date cannot read the sealed 2026 final holdout")
    if (
        payload.get("analysis_start_date") != "2020-01-02"
        or payload.get("analysis_end_date") != "2024-06-28"
    ):
        raise ValueError("config analysis window does not match the frozen contract")
    if payload.get("last_chance_batch") is not True:
        raise ValueError("config last_chance_batch must be true")

    eligibility = payload.get("eligibility")
    thresholds = payload.get("thresholds")
    capacity = payload.get("capacity")
    market_proxy = payload.get("market_proxy")
    parameters = payload.get("candidate_parameters")
    multiple_testing = payload.get("multiple_testing")
    zero_lead = payload.get("zero_lead_decision")
    if not isinstance(eligibility, dict) or eligibility != EXPECTED_ELIGIBILITY:
        raise ValueError("config eligibility does not match the frozen contract")
    if not isinstance(thresholds, dict) or thresholds != EXPECTED_THRESHOLDS:
        raise ValueError("config thresholds do not match the frozen contract")
    if not isinstance(capacity, dict) or capacity != EXPECTED_CAPACITY:
        raise ValueError("config capacity does not match the frozen contract")
    if not isinstance(market_proxy, dict) or market_proxy != EXPECTED_MARKET_PROXY:
        raise ValueError("config market_proxy does not match the frozen contract")
    if not isinstance(parameters, dict) or parameters != EXPECTED_CANDIDATE_PARAMETERS:
        raise ValueError("config candidate_parameters do not match the frozen contract")
    if not isinstance(multiple_testing, dict) or multiple_testing != EXPECTED_MULTIPLE_TESTING:
        raise ValueError("config multiple_testing does not match the frozen contract")
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
    _require_keys(market_proxy, ("min_cross_section",), "config market_proxy")
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
    if zero_lead.get("closed_family") != "cn_etf_volatility_regime":
        raise ValueError("config zero-lead closed_family must be cn_etf_volatility_regime")
    if float(zero_lead.get("closed_budget_share", -1.0)) != 0.35:
        raise ValueError("config zero-lead closed_budget_share must be 0.35")
    if zero_lead.get("activated_family") != "cn_etf_peer_relative_value":
        raise ValueError("config zero-lead activated_family must be cn_etf_peer_relative_value")
    if zero_lead.get("resulting_budget_shares") != EXPECTED_ZERO_LEAD_BUDGETS:
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
    parser = argparse.ArgumentParser(
        description="Run the frozen CN ETF market-residual volatility statistical prescreen."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    result = run_cn_etf_market_residual_volatility_prescreen_cli(
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
