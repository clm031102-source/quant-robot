from __future__ import annotations

from datetime import date
import json
import math
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from quant_robot.factors.etf_dynamic_peer_dislocation import FACTOR_NAME
from quant_robot.factors.etf_liquidity_capacity import (
    ETF_LIQUIDITY_CAPACITY_FACTOR_NAMES,
    ETF_LIQUIDITY_REFERENCE_FACTOR_NAMES,
    compute_etf_liquidity_capacity_factors,
    compute_etf_liquidity_reference_factors,
)
from quant_robot.factors.etf_market_residual_volatility import (
    ETF_MARKET_RESIDUAL_VOLATILITY_FACTOR_NAMES,
    ETF_MARKET_RESIDUAL_VOLATILITY_REFERENCE_NAMES,
    compute_etf_market_residual_volatility_factors,
    compute_etf_market_residual_volatility_references,
)
from quant_robot.factors.etf_skip_momentum import (
    ETF_PRICE_ROTATION_REFERENCE_FACTOR_NAMES,
    ETF_SKIP_MOMENTUM_FACTOR_NAMES,
    compute_etf_price_rotation_reference_factors,
    compute_etf_skip_momentum_factors,
)
from quant_robot.research.cross_sectional_factor_prescreen import (
    CrossSectionalPrescreenThresholds,
    summarize_cross_sectional_factor_prescreen,
)
from quant_robot.research.cross_sectional_prescreen_diagnostics import (
    summarize_direct_exposure_correlations,
    summarize_long_short_costs,
    summarize_top_quantile_capacity_by_date,
)
from quant_robot.schema.factors import FACTOR_COLUMNS


STAGE = "cn_etf_dynamic_peer_dislocation_prescreen"
STATUS_PRIMARY_PASSED = "primary_passed_backfill_required"
STATUS_CLOSED = "close_family_zero_budget"
SAFETY = (
    "Research-to-paper only. No portfolio grid, walk-forward, final holdout, "
    "paper signal, broker connection, account read, order placement, or live trading."
)
CLOSED_FAMILY_REFERENCE_NAMES = (
    *ETF_SKIP_MOMENTUM_FACTOR_NAMES,
    *ETF_PRICE_ROTATION_REFERENCE_FACTOR_NAMES,
    *ETF_LIQUIDITY_CAPACITY_FACTOR_NAMES,
    *ETF_LIQUIDITY_REFERENCE_FACTOR_NAMES,
    *ETF_MARKET_RESIDUAL_VOLATILITY_FACTOR_NAMES,
    *ETF_MARKET_RESIDUAL_VOLATILITY_REFERENCE_NAMES,
)


def compute_closed_family_reference_union(
    bars: pd.DataFrame,
    *,
    eligible_keys: pd.DataFrame,
    evaluation_keys: pd.DataFrame,
    expected_names: tuple[str, ...] = CLOSED_FAMILY_REFERENCE_NAMES,
) -> pd.DataFrame:
    """Build the exact closed-family union and retain only evaluation keys."""

    if tuple(expected_names) != CLOSED_FAMILY_REFERENCE_NAMES:
        raise ValueError("Closed-family reference names do not match the frozen union")
    builders: tuple[Callable[..., pd.DataFrame], ...] = (
        compute_etf_skip_momentum_factors,
        compute_etf_price_rotation_reference_factors,
        compute_etf_liquidity_capacity_factors,
        compute_etf_liquidity_reference_factors,
        compute_etf_market_residual_volatility_factors,
        compute_etf_market_residual_volatility_references,
    )
    key_frame = _normalise_keys(evaluation_keys)
    pieces: list[pd.DataFrame] = []
    for builder in builders:
        full = builder(bars, eligible_keys=eligible_keys).copy()
        full["date"] = pd.to_datetime(full["date"])
        piece = full.merge(
            key_frame,
            on=["date", "asset_id", "market"],
            how="inner",
            validate="many_to_one",
        )
        pieces.append(piece[FACTOR_COLUMNS])
    references = pd.concat(pieces, ignore_index=True)
    observed = tuple(sorted(references["factor_name"].unique()))
    expected_sorted = tuple(sorted(expected_names))
    if observed != expected_sorted:
        missing = sorted(set(expected_names) - set(observed))
        unexpected = sorted(set(observed) - set(expected_names))
        raise ValueError(
            "Closed-family reference union mismatch: "
            f"missing={missing}, unexpected={unexpected}"
        )
    if references.duplicated(["date", "asset_id", "market", "factor_name"]).any():
        raise ValueError("Closed-family reference union contains duplicate factor rows")
    return references.sort_values(["asset_id", "date", "factor_name"]).reset_index(drop=True)


def summarize_cn_etf_dynamic_peer_dislocation_prescreen(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    references: pd.DataFrame,
    direct_exposures: pd.DataFrame,
    adv20: pd.DataFrame,
    *,
    expected_reference_names: tuple[str, ...],
    direct_exposure_names: tuple[str, ...],
    horizons: tuple[int, ...] = (5, 20),
    primary_horizon: int = 5,
    diagnostic_horizon: int = 20,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_year_ic_observations: int = 20,
    min_usable_years: int = 3,
    alpha: float = 0.05,
    min_mean_rank_ic: float = 0.02,
    min_icir: float = 0.30,
    min_positive_ic_rate: float = 0.55,
    min_quantile_monotonicity: float = 0.70,
    max_top_quantile_turnover: float = 0.90,
    min_positive_year_rate: float = 0.60,
    max_abs_reference_correlation: float = 0.85,
    direct_min_daily_observations: int = 20,
    max_abs_direct_exposure_correlation: float = 0.85,
    position_value_cny: float = 100_000.0,
    max_one_way_participation_rate: float = 0.01,
    one_way_costs_bps: tuple[float, ...] = (5.0, 10.0),
    required_positive_net_spread_bps: float = 10.0,
    diagnostic_min_mean_rank_ic: float = 0.0,
    diagnostic_min_quantile_spread: float = 0.0,
    candidate_name: str = FACTOR_NAME,
    result_stage: str = STAGE,
    safety_text: str = SAFETY,
) -> dict[str, Any]:
    _validate_frozen_roles(
        horizons=horizons,
        primary_horizon=primary_horizon,
        diagnostic_horizon=diagnostic_horizon,
        one_way_costs_bps=one_way_costs_bps,
        required_positive_net_spread_bps=required_positive_net_spread_bps,
    )
    thresholds = CrossSectionalPrescreenThresholds(
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_year_ic_observations=min_year_ic_observations,
        min_usable_years=min_usable_years,
        alpha=alpha,
        min_mean_rank_ic=min_mean_rank_ic,
        min_icir=min_icir,
        min_positive_ic_rate=min_positive_ic_rate,
        min_quantile_monotonicity=min_quantile_monotonicity,
        max_top_quantile_turnover=max_top_quantile_turnover,
        min_positive_year_rate=min_positive_year_rate,
        max_abs_reference_correlation=max_abs_reference_correlation,
    )
    core = summarize_cross_sectional_factor_prescreen(
        factors,
        labels,
        references,
        candidate_names=(candidate_name,),
        reference_names=expected_reference_names,
        horizons=horizons,
        thresholds=thresholds,
    )
    costs = summarize_long_short_costs(
        factors,
        labels,
        candidate_names=(candidate_name,),
        horizons=horizons,
        min_cross_section=min_cross_section,
        one_way_costs_bps=one_way_costs_bps,
    )
    capacity = summarize_top_quantile_capacity_by_date(
        factors,
        labels,
        adv20,
        candidate_names=(candidate_name,),
        horizons=horizons,
        min_cross_section=min_cross_section,
        position_value_cny=position_value_cny,
        max_one_way_participation_rate=max_one_way_participation_rate,
    )
    exposure = summarize_direct_exposure_correlations(
        factors,
        direct_exposures,
        candidate_names=(candidate_name,),
        exposure_names=direct_exposure_names,
        min_cross_section=min_cross_section,
        min_daily_observations=direct_min_daily_observations,
        max_abs_mean_daily_correlation=max_abs_direct_exposure_correlation,
    )
    cost_by_key = _rows_by_key(costs["summary"])
    capacity_by_key = _rows_by_key(capacity["summary"])
    results: list[dict[str, Any]] = []
    required_net_column = _mean_net_column(required_positive_net_spread_bps)
    for original in core["results"]:
        row = dict(original)
        key = (str(row["factor_name"]), int(row["horizon"]))
        row["standard_blockers"] = list(row.get("blockers", []))
        row.update(cost_by_key[key])
        row.update(capacity_by_key[key])
        row["max_abs_direct_exposure_correlation"] = exposure["summary"][
            "max_abs_mean_daily_spearman"
        ]
        row["max_direct_exposure_name"] = exposure["summary"]["max_exposure_name"]
        if int(row["horizon"]) == primary_horizon:
            blockers = list(row["standard_blockers"])
            if not exposure["summary"]["evidence_complete"]:
                blockers.append("direct_exposure_evidence_incomplete")
            if not exposure["summary"]["strict_correlation_ceiling_passed"]:
                blockers.append("direct_exposure_correlation_not_strictly_below_threshold")
            if not bool(row["every_date_supported"]):
                blockers.append("primary_capacity_not_supported_every_date")
            if float(row[required_net_column]) <= 0.0:
                blockers.append(
                    f"primary_{_format_bps(required_positive_net_spread_bps)}bps_net_spread_not_positive"
                )
            row["horizon_role"] = "primary"
            row["blockers"] = _unique(blockers)
            row["role_passed"] = not row["blockers"]
            row["research_lead"] = bool(row["role_passed"])
        else:
            diagnostic_blockers = []
            if int(row["ic_observations"]) < min_ic_observations:
                diagnostic_blockers.append("diagnostic_ic_observations_below_threshold")
            if float(row["mean_rank_ic"]) < diagnostic_min_mean_rank_ic:
                diagnostic_blockers.append("diagnostic_mean_rank_ic_below_threshold")
            if float(row["quantile_spread"]) < diagnostic_min_quantile_spread:
                diagnostic_blockers.append("diagnostic_quantile_spread_below_threshold")
            row["horizon_role"] = "diagnostic_only"
            row["blockers"] = diagnostic_blockers
            row["role_passed"] = not diagnostic_blockers
            row["research_lead"] = False
        results.append(row)

    results.sort(key=lambda row: int(row["horizon"]))
    primary = next(row for row in results if int(row["horizon"]) == primary_horizon)
    diagnostic = next(row for row in results if int(row["horizon"]) == diagnostic_horizon)
    primary_passed = bool(primary["role_passed"])
    status = STATUS_PRIMARY_PASSED if primary_passed else STATUS_CLOSED
    core_summary = dict(core["summary"])
    core_summary["research_lead_count"] = int(primary_passed)
    core_summary["research_lead_factor_count"] = int(primary_passed)
    return {
        "stage": result_stage,
        "status": status,
        "summary": core_summary,
        "candidate_names": [candidate_name],
        "reference_names": list(expected_reference_names),
        "direct_exposure_names": list(direct_exposure_names),
        "thresholds": {
            **core["thresholds"],
            "direct_min_daily_observations": direct_min_daily_observations,
            "max_abs_direct_exposure_correlation": max_abs_direct_exposure_correlation,
            "position_value_cny": position_value_cny,
            "max_one_way_participation_rate": max_one_way_participation_rate,
            "one_way_costs_bps": list(one_way_costs_bps),
            "required_positive_net_spread_bps": required_positive_net_spread_bps,
            "diagnostic_min_mean_rank_ic": diagnostic_min_mean_rank_ic,
            "diagnostic_min_quantile_spread": diagnostic_min_quantile_spread,
        },
        "multiple_testing_policy": core["multiple_testing_policy"],
        "results": results,
        "ic_observations": core["ic_observations"],
        "yearly_ic": core["yearly_ic"],
        "reference_correlations": core["reference_correlations"],
        "direct_exposure_correlations": exposure["rows"],
        "direct_exposure_summary": exposure["summary"],
        "turnover_cost_summary": costs["summary"],
        "turnover_cost_daily": costs["daily"],
        "capacity_summary": capacity["summary"],
        "capacity_daily": capacity["daily"],
        "capacity_top_constituents": capacity["top_constituents"],
        "decision": {
            "primary_horizon": int(primary_horizon),
            "primary_passed": primary_passed,
            "primary_blockers": list(primary["blockers"]),
            "diagnostic_horizon": int(diagnostic_horizon),
            "diagnostic_passed": bool(diagnostic["role_passed"]),
            "diagnostic_can_rescue_primary": False,
            "family_budget": 0.0,
            "next_action": (
                "backfill_2024h2_through_2025_then_preregister_walk_forward"
                if primary_passed
                else "close_family_zero_budget_no_rescue"
            ),
            "portfolio_grid_allowed": False,
            "walk_forward_allowed": False,
            "final_holdout_allowed": False,
            "promotion_allowed": False,
            "paper_signal_allowed": False,
            "live_boundary_allowed": False,
        },
        "safety": safety_text,
    }


def write_cn_etf_dynamic_peer_dislocation_prescreen(
    output_dir: str | Path,
    result: dict[str, Any],
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output / "cn_etf_dynamic_peer_dislocation_prescreen.json",
        "markdown": output / "cn_etf_dynamic_peer_dislocation_prescreen.md",
        "results": output / "candidate_horizon_results.csv",
        "ic_observations": output / "daily_ic.csv",
        "yearly_ic": output / "yearly_ic.csv",
        "reference_correlations": output / "reference_correlations.csv",
        "direct_exposure_correlations": output / "direct_exposure_correlations.csv",
        "turnover_cost_summary": output / "turnover_cost_summary.csv",
        "turnover_cost_daily": output / "turnover_cost_daily.csv",
        "capacity_summary": output / "capacity_summary.csv",
        "capacity_daily": output / "capacity_daily.csv",
        "capacity_top_constituents": output / "capacity_top_constituents.csv",
    }
    paths["json"].write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["markdown"].write_text(
        render_cn_etf_dynamic_peer_dislocation_prescreen(result),
        encoding="utf-8",
    )
    table_keys = tuple(name for name in paths if name not in {"json", "markdown"})
    for name in table_keys:
        _stable_frame(result.get(name, [])).to_csv(paths[name], index=False)
    return paths


def render_cn_etf_dynamic_peer_dislocation_prescreen(result: dict[str, Any]) -> str:
    decision = result.get("decision", {})
    lines = [
        "# CN ETF Dynamic Peer Dislocation Prescreen",
        "",
        f"- Status: `{result.get('status', 'unknown')}`",
        f"- Primary passed: {str(bool(decision.get('primary_passed', False))).lower()}",
        f"- Diagnostic passed: {str(bool(decision.get('diagnostic_passed', False))).lower()}",
        f"- Next action: `{decision.get('next_action', 'n/a')}`",
        "- Final 2026 holdout included: false",
        "- Live boundary allowed: false",
        "",
        "## Results",
        "",
        "| Role | H | Mean IC | ICIR | FDR q | Q5-Q1 | Net 10bps | Capacity | Max ref | Max exposure | Passed |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for row in result.get("results", []):
        lines.append(
            "| {role} | {horizon} | {ic:.4f} | {icir:.3f} | {fdr:.4f} | {spread:.6f} | {net:.6f} | {capacity} | {reference:.4f} | {exposure:.4f} | {passed} |".format(
                role=row.get("horizon_role", ""),
                horizon=int(row.get("horizon", 0)),
                ic=float(row.get("mean_rank_ic", 0.0)),
                icir=float(row.get("icir", 0.0)),
                fdr=float(row.get("fdr_adjusted_p_value", 1.0)),
                spread=float(row.get("quantile_spread", 0.0)),
                net=float(row.get("mean_net_top_minus_bottom_10bps", 0.0)),
                capacity="yes" if row.get("every_date_supported") else "no",
                reference=float(row.get("max_abs_reference_correlation", 0.0)),
                exposure=float(row.get("max_abs_direct_exposure_correlation", 0.0)),
                passed="yes" if row.get("role_passed") else "no",
            )
        )
        blockers = row.get("blockers", [])
        if blockers:
            lines.append(f"  Blockers: {', '.join(str(item) for item in blockers)}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "The 20-session diagnostic cannot rescue the five-session primary row. No sign, window, mapping, eligibility, threshold, regime, portfolio, or walk-forward rescue is allowed.",
        ]
    )
    return "\n".join(lines) + "\n"


def _validate_frozen_roles(
    *,
    horizons: tuple[int, ...],
    primary_horizon: int,
    diagnostic_horizon: int,
    one_way_costs_bps: tuple[float, ...],
    required_positive_net_spread_bps: float,
) -> None:
    if tuple(int(value) for value in horizons) != (5, 20):
        raise ValueError("Dynamic-peer prescreen horizons must remain frozen at (5, 20)")
    if int(primary_horizon) != 5 or int(diagnostic_horizon) != 20:
        raise ValueError("Dynamic-peer primary and diagnostic horizons are frozen at 5 and 20")
    costs = tuple(float(value) for value in one_way_costs_bps)
    if costs != (5.0, 10.0):
        raise ValueError("Dynamic-peer one-way costs must remain frozen at 5 and 10 bps")
    if float(required_positive_net_spread_bps) != 10.0:
        raise ValueError("Dynamic-peer stressed positive-net gate must remain frozen at 10 bps")


def _rows_by_key(rows: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
    return {
        (str(row["factor_name"]), int(row["horizon"])): dict(row)
        for row in rows
    }


def _normalise_keys(keys: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market"]
    missing = [column for column in required if column not in keys.columns]
    if missing:
        raise ValueError("Evaluation keys are missing columns: " + ", ".join(missing))
    frame = keys[required].copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str)
    if frame.duplicated(required).any():
        raise ValueError("Evaluation keys contain duplicate rows")
    return frame


def _mean_net_column(cost_bps: float) -> str:
    return f"mean_net_top_minus_bottom_{_format_bps(cost_bps)}bps"


def _format_bps(cost_bps: float) -> str:
    if float(cost_bps).is_integer():
        return str(int(cost_bps))
    return format(cost_bps, "g").replace(".", "p")


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values))


def _stable_frame(rows: Any) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    sort_columns = [
        column
        for column in ("factor_name", "horizon", "date", "candidate_factor_name", "reference_factor_name", "exposure_name", "asset_id")
        if column in frame.columns
    ]
    if sort_columns and not frame.empty:
        frame = frame.sort_values(sort_columns, kind="stable").reset_index(drop=True)
    return frame


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if isinstance(value, (pd.Timestamp, date)):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value
