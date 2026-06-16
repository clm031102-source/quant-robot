from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.experiments.runner import ExperimentGridConfig, run_experiment_grid
from quant_robot.factors.moneyflow_technical import MONEYFLOW_TECHNICAL_COMBO_FACTOR_NAMES
from quant_robot.factors.tushare_inputs import DAILY_BASIC_FACTOR_NAMES
from quant_robot.factors.tushare_moneyflow import MONEYFLOW_FACTOR_NAMES


@dataclass(frozen=True)
class AlphaFactoryConfig:
    market: str = "CN"
    factor_source: str = "tushare_daily_basic"
    factor_input_root: Path | None = None
    moneyflow_input_root: Path | None = None
    output_dir: Path | None = None
    top_n: int = 1
    cost_bps: float = 5.0
    execution_lag: int = 1
    alpha: float = 0.05
    start_date: str | None = None
    end_date: str | None = None
    forward_horizon: int = 1
    rebalance_interval: int = 1
    min_trades: int = 30
    min_ic_observations: int = 20
    min_long_short_observations: int = 20
    rank_by: str = "sharpe"
    portfolio_value: float = 1_000_000.0
    market_impact_bps: float = 10.0
    max_participation_rate: float | None = 0.05
    require_capacity_controls: bool = True


def apply_bonferroni_correction(
    rows: list[dict[str, Any]],
    p_value_key: str = "ic_p_value",
    alpha: float = 0.05,
) -> list[dict[str, Any]]:
    hypothesis_count = len(rows)
    corrected = []
    for row in rows:
        p_value = _float(row.get(p_value_key), 1.0)
        adjusted = min(max(p_value, 0.0) * max(hypothesis_count, 1), 1.0)
        passes = adjusted <= alpha
        reasons = list(row.get("multiple_test_rejection_reasons", []) or [])
        if not passes:
            reasons.append("adjusted_ic_p_value_above_alpha")
        corrected_row = {
            **row,
            "hypothesis_count": hypothesis_count,
            "adjusted_ic_p_value": adjusted,
            "passes_adjusted_ic_p_value": passes,
            "multiple_test_rejection_reasons": _dedupe(reasons),
        }
        paper_reasons = _paper_candidate_rejection_reasons(corrected_row)
        corrected.append(
            {
                **corrected_row,
                "paper_candidate_allowed": not paper_reasons,
                "paper_candidate_rejection_reasons": paper_reasons,
            }
        )
    return corrected


def run_tushare_alpha_factory(bars: pd.DataFrame, config: AlphaFactoryConfig) -> dict[str, Any]:
    factor_names = _factor_names(config)
    grid = ExperimentGridConfig(
        markets=(config.market.upper(),),
        factor_source=config.factor_source,
        factor_input_root=config.factor_input_root,
        moneyflow_input_root=config.moneyflow_input_root,
        factor_input_required=True,
        factor_names=factor_names,
        factor_windows=_factor_windows(config),
        top_n_values=(config.top_n,),
        cost_bps_values=(config.cost_bps,),
        start_date=config.start_date,
        end_date=config.end_date,
        forward_horizon=config.forward_horizon,
        execution_lag=config.execution_lag,
        rebalance_intervals=(config.rebalance_interval,),
        output_dir=config.output_dir / "experiments" if config.output_dir is not None else None,
        rank_by=config.rank_by,
        min_trades=config.min_trades,
        portfolio_value=config.portfolio_value,
        market_impact_bps=config.market_impact_bps,
        max_participation_rate=config.max_participation_rate,
    )
    grid_result = run_experiment_grid(bars, grid)
    rows = [_candidate_row(row, config) for row in grid_result["leaderboard"]]
    leaderboard = _rank_candidates(apply_bonferroni_correction(rows, alpha=config.alpha), config.rank_by)
    result = {
        "config": _config_dict(config),
        "summary": _summary(leaderboard),
        "candidate_leaderboard": leaderboard,
        "experiment_summary": grid_result["summary"],
    }
    if config.output_dir is not None:
        _write_artifacts(config.output_dir, result, leaderboard)
    return result


def _candidate_row(row: dict[str, Any], config: AlphaFactoryConfig) -> dict[str, Any]:
    reasons = []
    if str(row.get("status")) != "completed":
        reasons.append("experiment_not_completed")
    if int(_float(row.get("trades"), 0.0)) < config.min_trades:
        reasons.append("insufficient_trades")
    if int(_float(row.get("ic_observations"), 0.0)) < config.min_ic_observations:
        reasons.append("insufficient_ic_observations")
    if int(_float(row.get("long_short_observations"), 0.0)) < config.min_long_short_observations:
        reasons.append("insufficient_long_short_observations")
    if config.require_capacity_controls:
        if config.market_impact_bps <= 0.0:
            reasons.append("market_impact_not_configured")
        if config.max_participation_rate is None or config.max_participation_rate <= 0.0:
            reasons.append("max_participation_rate_not_configured")
    return {
        **row,
        "factor_source": config.factor_source,
        "ic_p_value": _float(row.get("ic_p_value"), 1.0),
        "multiple_test_rejection_reasons": reasons,
    }


def _rank_candidates(rows: list[dict[str, Any]], rank_by: str) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda row: (
            0 if row.get("paper_candidate_allowed") else 1,
            -_float(row.get(rank_by), float("-inf")),
            str(row.get("case_id")),
        ),
    )
    return [{**row, "candidate_rank": index + 1} for index, row in enumerate(ranked)]


def _summary(leaderboard: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "hypothesis_count": len(leaderboard),
        "completed": sum(1 for row in leaderboard if row.get("status") == "completed"),
        "adjusted_significant": sum(1 for row in leaderboard if row.get("passes_adjusted_ic_p_value")),
        "paper_eligible": sum(1 for row in leaderboard if row.get("paper_candidate_allowed")),
        "rejected_after_multiple_testing": sum(1 for row in leaderboard if not row.get("passes_adjusted_ic_p_value")),
    }


def _write_artifacts(output_dir: Path, result: dict[str, Any], leaderboard: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(leaderboard).to_csv(output_dir / "candidate_leaderboard.csv", index=False)
    (output_dir / "candidate_leaderboard.json").write_text(
        json.dumps(leaderboard, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    manifest = {"config": result["config"], "summary": result["summary"], "experiment_summary": result["experiment_summary"]}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _config_dict(config: AlphaFactoryConfig) -> dict[str, Any]:
    data = asdict(config)
    data["factor_input_root"] = str(config.factor_input_root) if config.factor_input_root is not None else None
    data["moneyflow_input_root"] = str(config.moneyflow_input_root) if config.moneyflow_input_root is not None else None
    data["output_dir"] = str(config.output_dir) if config.output_dir is not None else None
    return data


def _factor_names(config: AlphaFactoryConfig) -> tuple[str, ...]:
    if config.factor_source == "tushare_daily_basic":
        if config.factor_input_root is None:
            raise ValueError("factor_input_root is required for Tushare daily-basic alpha factory")
        return DAILY_BASIC_FACTOR_NAMES
    if config.factor_source == "tushare_moneyflow":
        if config.moneyflow_input_root is None:
            raise ValueError("moneyflow_input_root is required for Tushare moneyflow alpha factory")
        return MONEYFLOW_FACTOR_NAMES
    if config.factor_source == "moneyflow_technical_combo":
        if config.moneyflow_input_root is None:
            raise ValueError("moneyflow_input_root is required for moneyflow technical combo alpha factory")
        return MONEYFLOW_TECHNICAL_COMBO_FACTOR_NAMES
    raise ValueError(f"Unsupported Tushare alpha factory factor_source: {config.factor_source}")


def _factor_windows(config: AlphaFactoryConfig) -> tuple[int, ...]:
    if config.factor_source == "moneyflow_technical_combo":
        return (5, 10, 20)
    return (1,)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _paper_candidate_rejection_reasons(row: dict[str, Any]) -> list[str]:
    reasons = list(row.get("multiple_test_rejection_reasons", []) or [])
    if row.get("status") != "completed":
        reasons.append("alpha_candidate_not_completed")
    if not row.get("passes_adjusted_ic_p_value"):
        reasons.append("adjusted_ic_significance_not_passed")
    if row.get("significance_status") != "significant_positive":
        reasons.append("significance_direction_not_positive")
    if _float(row.get("capacity_limited_trades"), 0.0) > 0.0:
        reasons.append("capacity_limited_trades_present")
    return _dedupe([str(reason) for reason in reasons])
