from __future__ import annotations

from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    load_capacity_safe_bars,
)
from quant_robot.ops.daily_basic_non_price_public_carry_lead_dedup import (
    DEFAULT_HORIZON,
    DEFAULT_LEAD_FACTOR_NAME,
    DEFAULT_RESIDUAL_EXPOSURES,
    build_daily_basic_lead_exposure_frame,
    residualize_daily_basic_lead,
    _merge_lead_exposures,
    _normalise_exposure_frame,
    _normalise_lead,
)
from quant_robot.ops.daily_basic_non_price_public_carry_preregistration import SAFETY
from quant_robot.ops.daily_basic_non_price_public_carry_prescreen import (
    _data_window,
    _sanitize,
    attach_daily_basic_capacity_fields,
    compute_daily_basic_non_price_public_carry_factors,
    load_daily_basic_non_price_public_carry_inputs,
)
from quant_robot.ops.market_residual_lead_exposure_dedup import (
    IC_OBSERVATION_COLUMNS,
    MONTHLY_IC_COLUMNS,
    YEARLY_IC_COLUMNS,
    _lead_ic_observations,
    _lead_ic_summary,
    _load_report,
    _period_ic,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "daily_basic_free_float_supply_quality_residual_stability_audit"
NEXT_REVIEW_DIRECTION = "round135_round132_134_three_round_review_before_next_action"
POST_REVIEW_STRICT_PREFLIGHT_DIRECTION = (
    "round135_daily_basic_free_float_supply_quality_strict_clean_portfolio_preflight_after_review"
)
POST_REVIEW_HIBERNATE_DIRECTION = (
    "round135_daily_basic_share_structure_family_hibernation_or_rotation_after_review"
)
RESIDUAL_FACTOR_NAME = f"{DEFAULT_LEAD_FACTOR_NAME}_implementation_residual"
STRICT_RESIDUAL_FACTOR_NAME = f"{DEFAULT_LEAD_FACTOR_NAME}_strict_clean_implementation_residual"
STATE_AUDIT_COLUMNS = [
    "group_name",
    "group_value",
    "ic_observations",
    "mean_spearman_ic",
    "icir",
    "positive_ic_rate",
    "failure",
]
MONTHLY_STATE_AUDIT_COLUMNS = [
    "month",
    "ic_observations",
    "mean_spearman_ic",
    "positive_ic_rate",
    "failure",
    "dominant_trend_state",
    "dominant_breadth_state",
    "dominant_volatility_state",
    "post_onset_observation_count",
    "onset_observation_count",
]
ONSET_AUDIT_COLUMNS = [
    "coverage_phase",
    "ic_observations",
    "mean_spearman_ic",
    "icir",
    "positive_ic_rate",
    "failure",
]


def build_daily_basic_free_float_supply_quality_residual_stability_audit(
    *,
    bars_roots: Iterable[str | Path],
    daily_basic_roots: Iterable[str | Path],
    prescreen_report: dict[str, Any] | str | Path,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    horizon: int = DEFAULT_HORIZON,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    min_field_coverage_ratio: float = 0.95,
    coverage_onset_observations: int = 63,
) -> dict[str, Any]:
    report = _load_report(prescreen_report)
    bars = load_capacity_safe_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    daily_basic = load_daily_basic_non_price_public_carry_inputs(
        daily_basic_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    lead_specs = [
        spec
        for spec in _default_daily_basic_non_price_public_carry_specs()
        if spec.factor_name == lead_factor_name
    ]
    lead_frame = compute_daily_basic_non_price_public_carry_factors(daily_basic, candidate_specs=lead_specs)
    lead_frame = attach_daily_basic_capacity_fields(lead_frame, bars)
    exposure_frame = build_daily_basic_lead_exposure_frame(daily_basic, bars)
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=(horizon,),
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    lead = _normalise_lead(lead_frame, lead_factor_name=lead_factor_name)
    exposures = _normalise_exposure_frame(exposure_frame)
    lead_with_exposures = _merge_lead_exposures(lead, exposures)
    residual_frame = residualize_daily_basic_lead(
        lead_with_exposures,
        exposure_names=DEFAULT_RESIDUAL_EXPOSURES,
        residual_factor_name=RESIDUAL_FACTOR_NAME,
        min_cross_section=min_cross_section,
    )
    strict_lead = _strict_clean_lead_frame(
        lead_with_exposures,
        min_field_coverage_ratio=min_field_coverage_ratio,
        min_signal_date_amount=min_signal_date_amount,
    )
    strict_residual_frame = residualize_daily_basic_lead(
        strict_lead,
        exposure_names=DEFAULT_RESIDUAL_EXPOSURES,
        residual_factor_name=STRICT_RESIDUAL_FACTOR_NAME,
        min_cross_section=min_cross_section,
    )
    raw_ic_observations = _lead_ic_observations(
        lead,
        labels,
        lead_factor_name=lead_factor_name,
        horizon=horizon,
        min_cross_section=min_cross_section,
    )
    residual_ic_observations = _lead_ic_observations(
        residual_frame,
        labels,
        lead_factor_name=RESIDUAL_FACTOR_NAME,
        horizon=horizon,
        min_cross_section=min_cross_section,
    )
    strict_clean_residual_ic_observations = _lead_ic_observations(
        strict_residual_frame,
        labels,
        lead_factor_name=STRICT_RESIDUAL_FACTOR_NAME,
        horizon=horizon,
        min_cross_section=min_cross_section,
    )
    result = summarize_daily_basic_free_float_supply_quality_residual_stability_audit(
        raw_ic_observations=raw_ic_observations,
        residual_ic_observations=residual_ic_observations,
        market_state_frame=build_market_state_frame(bars),
        strict_clean_residual_ic_observations=strict_clean_residual_ic_observations,
        lead_factor_name=lead_factor_name,
        horizon=horizon,
        min_ic_observations=min_ic_observations,
        coverage_onset_observations=coverage_onset_observations,
    )
    window = _data_window(bars, daily_basic, lead_frame, labels)
    result["data_window"] = window | {
        "min_factor_date": window.get("min_signal_date"),
        "max_factor_date": window.get("max_signal_date"),
        "factor_rows": int(len(lead_frame)),
        "strict_clean_factor_rows": int(len(strict_lead)),
        "residual_rows": int(len(residual_frame)),
        "strict_clean_residual_rows": int(len(strict_residual_frame)),
        "label_rows": int(len(labels)),
    }
    result["source_reports"] = {
        "prescreen_report_present": bool(report),
        "round133_precondition": "daily_basic_free_float_supply_quality_residual_ic_survived_size_value_capacity_neutralization",
    }
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_clearance_only",
    }
    result["capacity_policy"] = {
        "min_signal_date_amount": min_signal_date_amount,
        "min_field_coverage_ratio": min_field_coverage_ratio,
        "strict_clean_mask_enabled": True,
    }
    result["markdown"] = render_daily_basic_free_float_supply_quality_residual_stability_audit_markdown(result)
    return result


def summarize_daily_basic_free_float_supply_quality_residual_stability_audit(
    *,
    raw_ic_observations: list[dict[str, Any]],
    residual_ic_observations: list[dict[str, Any]],
    market_state_frame: pd.DataFrame | None = None,
    strict_clean_residual_ic_observations: list[dict[str, Any]] | None = None,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    horizon: int = DEFAULT_HORIZON,
    min_ic_observations: int = 20,
    coverage_onset_observations: int = 63,
    min_strict_mean_ic: float = 0.02,
    min_strict_icir: float = 0.20,
    min_strict_positive_ic_rate: float = 0.55,
) -> dict[str, Any]:
    strict_clean_residual_ic_observations = strict_clean_residual_ic_observations or []
    raw_ic_summary = _lead_ic_summary(raw_ic_observations, min_ic_observations=min_ic_observations)
    residual_ic_summary = _lead_ic_summary(residual_ic_observations, min_ic_observations=min_ic_observations)
    strict_clean_residual_ic_summary = _lead_ic_summary(
        strict_clean_residual_ic_observations,
        min_ic_observations=min_ic_observations,
    )
    residual_with_state = _attach_market_state(
        residual_ic_observations,
        market_state_frame,
        coverage_onset_observations=coverage_onset_observations,
    )
    residual_monthly_ic = _period_ic(residual_ic_observations, period="month")
    raw_monthly_ic = _period_ic(raw_ic_observations, period="month")
    residual_yearly_ic = _period_ic(residual_ic_observations, period="year")
    raw_yearly_ic = _period_ic(raw_ic_observations, period="year")
    monthly_state_audit = _monthly_state_audit(residual_with_state)
    onset_audit = _onset_audit(residual_with_state)
    state_audit = (
        _state_audit(residual_with_state, "trend_state")
        + _state_audit(residual_with_state, "breadth_state")
        + _state_audit(residual_with_state, "volatility_state")
    )
    post_onset_observations = [
        row
        for row in residual_with_state
        if row.get("coverage_phase") == "post_onset"
    ]
    post_onset_monthly_ic = _period_ic(post_onset_observations, period="month")
    post_onset_failed_months = [row for row in post_onset_monthly_ic if row.get("failure")]
    weak_months = [row for row in residual_monthly_ic if row.get("failure")]
    non_stress_failed_months = [
        row
        for row in monthly_state_audit
        if row.get("failure") and row.get("dominant_trend_state") != "stress"
    ]
    raw_failure_months = {row.get("month") for row in raw_monthly_ic if row.get("failure")}
    residual_only_failed_months = [
        row.get("month") for row in weak_months if row.get("month") not in raw_failure_months
    ]
    blockers = _gate_blockers(
        residual_ic_summary=residual_ic_summary,
        strict_clean_residual_ic_summary=strict_clean_residual_ic_summary,
        post_onset_failed_months=post_onset_failed_months,
        non_stress_failed_months=non_stress_failed_months,
        min_ic_observations=min_ic_observations,
        min_strict_mean_ic=min_strict_mean_ic,
        min_strict_icir=min_strict_icir,
        min_strict_positive_ic_rate=min_strict_positive_ic_rate,
    )
    observations = []
    if weak_months and not non_stress_failed_months:
        observations.append("coverage_onset_or_stress_only_residual_failure")
    if residual_only_failed_months:
        observations.append("raw_pass_residual_fail_neutralization_sensitivity")
    stability_repair_candidate = bool(weak_months and not blockers)
    recommended_post_review_direction = (
        POST_REVIEW_STRICT_PREFLIGHT_DIRECTION
        if stability_repair_candidate
        else POST_REVIEW_HIBERNATE_DIRECTION
    )
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "lead_factor_name": lead_factor_name,
        "horizon": int(horizon),
        "raw_ic_summary": raw_ic_summary,
        "residual_ic_summary": residual_ic_summary,
        "strict_clean_residual_ic_summary": strict_clean_residual_ic_summary,
        "summary": {
            "raw_ic_observations": int(raw_ic_summary.get("ic_observations", 0)),
            "residual_ic_observations": int(residual_ic_summary.get("ic_observations", 0)),
            "strict_clean_residual_ic_observations": int(
                strict_clean_residual_ic_summary.get("ic_observations", 0)
            ),
            "residual_failed_month_count": int(len(weak_months)),
            "post_onset_failed_month_count": int(len(post_onset_failed_months)),
            "non_stress_failed_month_count": int(len(non_stress_failed_months)),
            "residual_only_failed_month_count": int(len(residual_only_failed_months)),
            "promotion_allowed_candidates": 0,
        },
        "thresholds": {
            "min_ic_observations": min_ic_observations,
            "coverage_onset_observations": coverage_onset_observations,
            "min_strict_mean_ic": min_strict_mean_ic,
            "min_strict_icir": min_strict_icir,
            "min_strict_positive_ic_rate": min_strict_positive_ic_rate,
        },
        "gate": {
            "blockers": blockers,
            "observations": observations,
            "required_before": [
                "round134_explains_round133_residual_yearly_instability_before_portfolio_grid",
                "strict_clean_field_coverage_and_amount_mask_before_portfolio_conversion",
                "market_state_and_coverage_onset_audit_before_more_daily_basic_sweeps",
                "three_round_review_required_after_round132_134",
            ],
            "drawdown_policy": (
                "A roughly 30% drawdown tolerance can be used in later portfolio risk settings, but it does "
                "not waive residual stability, capacity, data cleanliness, or walk-forward gates."
            ),
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed": False,
            "reason": (
                "Round134 is a residual-stability and data-cleanliness audit only. It can route the next "
                "research step, but cannot promote a factor without costed portfolio, walk-forward, "
                "capacity, regime, and holdout gates."
            ),
        },
        "stability_repair_candidate": stability_repair_candidate,
        "next_direction": NEXT_REVIEW_DIRECTION,
        "recommended_post_review_direction": recommended_post_review_direction,
        "weak_months": weak_months,
        "residual_only_failed_months": residual_only_failed_months,
        "raw_yearly_ic": raw_yearly_ic,
        "raw_monthly_ic": raw_monthly_ic,
        "residual_yearly_ic": residual_yearly_ic,
        "residual_monthly_ic": residual_monthly_ic,
        "residual_monthly_state_audit": monthly_state_audit,
        "residual_onset_audit": onset_audit,
        "residual_state_audit": state_audit,
        "raw_ic_observations": raw_ic_observations,
        "residual_ic_observations": residual_ic_observations,
        "strict_clean_residual_ic_observations": strict_clean_residual_ic_observations,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_daily_basic_free_float_supply_quality_residual_stability_audit_markdown(result)
    return result


def build_market_state_frame(bars: pd.DataFrame) -> pd.DataFrame:
    if bars is None or bars.empty:
        return pd.DataFrame(columns=["date", "trend_state", "breadth_state", "volatility_state"])
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    frame = frame.sort_values(["asset_id", "date"])
    frame["return_1d"] = frame.groupby("asset_id")["adj_close"].pct_change()
    daily = (
        frame.dropna(subset=["return_1d"])
        .groupby("date", sort=True)
        .agg(
            market_return_1d=("return_1d", "mean"),
            breadth_positive_rate=("return_1d", lambda values: float((values > 0).mean())),
        )
        .reset_index()
    )
    if daily.empty:
        return pd.DataFrame(columns=["date", "trend_state", "breadth_state", "volatility_state"])
    daily["market_return_20"] = (1.0 + daily["market_return_1d"]).rolling(20, min_periods=5).apply(np.prod, raw=True) - 1.0
    daily["market_volatility_20"] = daily["market_return_1d"].rolling(20, min_periods=5).std(ddof=1) * math.sqrt(252.0)
    daily["trend_state"] = np.select(
        [
            (daily["market_return_20"] <= -0.05) | (daily["breadth_positive_rate"] <= 0.45),
            (daily["market_return_20"] >= 0.05) & (daily["breadth_positive_rate"] >= 0.55),
        ],
        ["stress", "strong"],
        default="neutral",
    )
    daily["breadth_state"] = np.select(
        [
            daily["breadth_positive_rate"] <= 0.45,
            daily["breadth_positive_rate"] >= 0.55,
        ],
        ["weak", "strong"],
        default="mixed",
    )
    daily["volatility_state"] = np.select(
        [
            daily["market_volatility_20"] >= 0.25,
            daily["market_volatility_20"] <= 0.15,
        ],
        ["high_vol", "low_vol"],
        default="normal_vol",
    )
    return daily[
        [
            "date",
            "market_return_1d",
            "market_return_20",
            "market_volatility_20",
            "breadth_positive_rate",
            "trend_state",
            "breadth_state",
            "volatility_state",
        ]
    ].reset_index(drop=True)


def write_daily_basic_free_float_supply_quality_residual_stability_audit(
    output_dir: str | Path,
    result: dict[str, Any],
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "daily_basic_free_float_supply_quality_residual_stability_audit.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "daily_basic_free_float_supply_quality_residual_stability_audit.md").write_text(
        render_daily_basic_free_float_supply_quality_residual_stability_audit_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "daily_basic_free_float_raw_yearly_ic.csv", result.get("raw_yearly_ic", []), YEARLY_IC_COLUMNS)
    _write_csv(output_path / "daily_basic_free_float_raw_monthly_ic.csv", result.get("raw_monthly_ic", []), MONTHLY_IC_COLUMNS)
    _write_csv(
        output_path / "daily_basic_free_float_residual_yearly_ic.csv",
        result.get("residual_yearly_ic", []),
        YEARLY_IC_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_free_float_residual_monthly_ic.csv",
        result.get("residual_monthly_ic", []),
        MONTHLY_IC_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_free_float_residual_monthly_state_audit.csv",
        result.get("residual_monthly_state_audit", []),
        MONTHLY_STATE_AUDIT_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_free_float_residual_onset_audit.csv",
        result.get("residual_onset_audit", []),
        ONSET_AUDIT_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_free_float_residual_state_audit.csv",
        result.get("residual_state_audit", []),
        STATE_AUDIT_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_free_float_raw_ic_observations.csv",
        result.get("raw_ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_free_float_residual_ic_observations.csv",
        result.get("residual_ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_free_float_strict_clean_residual_ic_observations.csv",
        result.get("strict_clean_residual_ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )


def render_daily_basic_free_float_supply_quality_residual_stability_audit_markdown(
    result: dict[str, Any],
) -> str:
    summary = result.get("summary", {})
    residual_ic = result.get("residual_ic_summary", {})
    strict_ic = result.get("strict_clean_residual_ic_summary", {})
    gate = result.get("gate", {})
    lines = [
        "# Daily-Basic Free-Float Supply Quality Residual Stability Audit",
        "",
        "## Summary",
        "",
        f"- Lead: `{result.get('lead_factor_name')}` horizon {result.get('horizon')}",
        f"- Residual mean IC: {residual_ic.get('mean_spearman_ic', 0.0):.4f}",
        f"- Residual ICIR: {residual_ic.get('icir', 0.0):.3f}",
        f"- Residual IC observations: {residual_ic.get('ic_observations', 0)}",
        f"- Strict-clean residual mean IC: {strict_ic.get('mean_spearman_ic', 0.0):.4f}",
        f"- Strict-clean residual ICIR: {strict_ic.get('icir', 0.0):.3f}",
        f"- Failed residual months: {summary.get('residual_failed_month_count', 0)}",
        f"- Post-onset failed months: {summary.get('post_onset_failed_month_count', 0)}",
        f"- Non-stress failed months: {summary.get('non_stress_failed_month_count', 0)}",
        f"- Stability repair candidate: {result.get('stability_repair_candidate', False)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Next direction: `{result.get('next_direction')}`",
        f"- Recommended post-review direction: `{result.get('recommended_post_review_direction')}`",
        "",
        "## Gate",
        "",
        f"- Blockers: {', '.join(gate.get('blockers', [])) if gate.get('blockers') else 'none'}",
        f"- Observations: {', '.join(gate.get('observations', [])) if gate.get('observations') else 'none'}",
        "",
        "## Residual Monthly State Audit",
        "",
        "| Month | Obs | Mean IC | IC+ | Trend | Breadth | Vol | Post-Onset Obs | Failure |",
        "|---|---:|---:|---:|---|---|---|---:|---|",
    ]
    for row in result.get("residual_monthly_state_audit", []):
        lines.append(
            "| {month} | {obs} | {mean:.4f} | {pos:.1%} | {trend} | {breadth} | {vol} | {post} | {failure} |".format(
                month=row.get("month"),
                obs=row.get("ic_observations", 0),
                mean=row.get("mean_spearman_ic", 0.0),
                pos=row.get("positive_ic_rate", 0.0),
                trend=row.get("dominant_trend_state", "unknown"),
                breadth=row.get("dominant_breadth_state", "unknown"),
                vol=row.get("dominant_volatility_state", "unknown"),
                post=row.get("post_onset_observation_count", 0),
                failure=row.get("failure", False),
            )
        )
    lines.extend(
        [
            "",
            "## Onset Audit",
            "",
            "| Phase | Obs | Mean IC | ICIR | IC+ | Failure |",
            "|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in result.get("residual_onset_audit", []):
        lines.append(
            "| {phase} | {obs} | {mean:.4f} | {icir:.3f} | {pos:.1%} | {failure} |".format(
                phase=row.get("coverage_phase"),
                obs=row.get("ic_observations", 0),
                mean=row.get("mean_spearman_ic", 0.0),
                icir=row.get("icir", 0.0),
                pos=row.get("positive_ic_rate", 0.0),
                failure=row.get("failure", False),
            )
        )
    return "\n".join(lines)


def _strict_clean_lead_frame(
    lead_with_exposures: pd.DataFrame,
    *,
    min_field_coverage_ratio: float,
    min_signal_date_amount: float,
) -> pd.DataFrame:
    if lead_with_exposures.empty:
        return lead_with_exposures.copy()
    frame = lead_with_exposures.copy()
    if "field_coverage_ratio" in frame:
        frame["field_coverage_ratio"] = pd.to_numeric(frame["field_coverage_ratio"], errors="coerce")
        frame = frame[frame["field_coverage_ratio"] >= min_field_coverage_ratio]
    for column in ["amount", "adv20_amount"]:
        if column in frame:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
            frame = frame[frame[column] >= min_signal_date_amount]
    return frame.reset_index(drop=True)


def _attach_market_state(
    ic_observations: list[dict[str, Any]],
    market_state_frame: pd.DataFrame | None,
    *,
    coverage_onset_observations: int,
) -> list[dict[str, Any]]:
    if not ic_observations:
        return []
    frame = pd.DataFrame(ic_observations).copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values("date").reset_index(drop=True)
    if market_state_frame is not None and not market_state_frame.empty:
        state = market_state_frame.copy()
        state["date"] = pd.to_datetime(state["date"])
        state_columns = [
            column
            for column in [
                "date",
                "trend_state",
                "breadth_state",
                "volatility_state",
                "market_return_20",
                "market_volatility_20",
                "breadth_positive_rate",
            ]
            if column in state.columns
        ]
        frame = frame.merge(state[state_columns], on="date", how="left", validate="many_to_one")
    for column, default in [
        ("trend_state", "unknown"),
        ("breadth_state", "unknown"),
        ("volatility_state", "unknown"),
    ]:
        if column not in frame:
            frame[column] = default
        frame[column] = frame[column].fillna(default).astype(str)
    frame["coverage_phase"] = np.where(
        frame.index < max(0, int(coverage_onset_observations)),
        "coverage_onset",
        "post_onset",
    )
    frame["date"] = frame["date"].dt.date.astype(str)
    return frame.to_dict("records")


def _monthly_state_audit(residual_with_state: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not residual_with_state:
        return []
    frame = pd.DataFrame(residual_with_state)
    frame["date"] = pd.to_datetime(frame["date"])
    frame["spearman_ic"] = pd.to_numeric(frame["spearman_ic"], errors="coerce")
    frame["month"] = frame["date"].dt.to_period("M").astype(str)
    rows = []
    for month, group in frame.groupby("month", sort=True):
        values = group["spearman_ic"].dropna()
        if values.empty:
            continue
        mean_ic = float(values.mean())
        positive_rate = float((values > 0).mean())
        rows.append(
            {
                "month": month,
                "ic_observations": int(len(values)),
                "mean_spearman_ic": mean_ic,
                "positive_ic_rate": positive_rate,
                "failure": bool(mean_ic <= 0.0 or positive_rate < 0.50),
                "dominant_trend_state": _dominant(group["trend_state"]),
                "dominant_breadth_state": _dominant(group["breadth_state"]),
                "dominant_volatility_state": _dominant(group["volatility_state"]),
                "post_onset_observation_count": int((group["coverage_phase"] == "post_onset").sum()),
                "onset_observation_count": int((group["coverage_phase"] == "coverage_onset").sum()),
            }
        )
    return rows


def _onset_audit(residual_with_state: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not residual_with_state:
        return []
    frame = pd.DataFrame(residual_with_state)
    rows = []
    for phase, group in frame.groupby("coverage_phase", sort=True):
        rows.append(_summary_row(group, group_name="coverage_phase", group_value=phase) | {"coverage_phase": phase})
    return [
        {
            "coverage_phase": row["coverage_phase"],
            "ic_observations": row["ic_observations"],
            "mean_spearman_ic": row["mean_spearman_ic"],
            "icir": row["icir"],
            "positive_ic_rate": row["positive_ic_rate"],
            "failure": row["failure"],
        }
        for row in rows
    ]


def _state_audit(residual_with_state: list[dict[str, Any]], column: str) -> list[dict[str, Any]]:
    if not residual_with_state:
        return []
    frame = pd.DataFrame(residual_with_state)
    if column not in frame:
        return []
    rows = []
    for value, group in frame.groupby(column, sort=True):
        rows.append(_summary_row(group, group_name=column, group_value=str(value)))
    return rows


def _summary_row(group: pd.DataFrame, *, group_name: str, group_value: str) -> dict[str, Any]:
    values = pd.to_numeric(group["spearman_ic"], errors="coerce").dropna()
    std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    mean_ic = float(values.mean()) if len(values) else 0.0
    return {
        "group_name": group_name,
        "group_value": group_value,
        "ic_observations": int(len(values)),
        "mean_spearman_ic": mean_ic,
        "icir": _safe_ratio(mean_ic, std),
        "positive_ic_rate": float((values > 0).mean()) if len(values) else 0.0,
        "failure": bool(mean_ic <= 0.0 or (float((values > 0).mean()) if len(values) else 0.0) < 0.50),
    }


def _gate_blockers(
    *,
    residual_ic_summary: dict[str, Any],
    strict_clean_residual_ic_summary: dict[str, Any],
    post_onset_failed_months: list[dict[str, Any]],
    non_stress_failed_months: list[dict[str, Any]],
    min_ic_observations: int,
    min_strict_mean_ic: float,
    min_strict_icir: float,
    min_strict_positive_ic_rate: float,
) -> list[str]:
    blockers = []
    if int(residual_ic_summary.get("ic_observations", 0)) < min_ic_observations:
        blockers.append("residual_ic_observations_below_threshold")
    if post_onset_failed_months and non_stress_failed_months:
        blockers.append("residual_failure_persists_after_coverage_onset")
    if non_stress_failed_months:
        blockers.append("residual_failure_in_non_stress_regime")
    if int(strict_clean_residual_ic_summary.get("ic_observations", 0)) < min_ic_observations:
        blockers.append("strict_clean_residual_ic_observations_below_threshold")
    elif (
        float(strict_clean_residual_ic_summary.get("mean_spearman_ic", 0.0)) < min_strict_mean_ic
        or float(strict_clean_residual_ic_summary.get("icir", 0.0)) < min_strict_icir
        or float(strict_clean_residual_ic_summary.get("positive_ic_rate", 0.0)) < min_strict_positive_ic_rate
    ):
        blockers.append("strict_clean_residual_ic_below_threshold")
    return _dedupe(blockers)


def _default_daily_basic_non_price_public_carry_specs() -> list[Any]:
    from quant_robot.ops.daily_basic_non_price_public_carry_preregistration import (
        default_daily_basic_non_price_public_carry_specs,
    )

    return default_daily_basic_non_price_public_carry_specs()


def _dominant(values: pd.Series) -> str:
    counts = values.fillna("unknown").astype(str).value_counts()
    if counts.empty:
        return "unknown"
    return str(counts.index[0])


def _safe_ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) <= 1e-12:
        return 0.0
    return float(numerator / denominator)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return ";".join(str(item) for item in value)
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
