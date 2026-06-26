from __future__ import annotations

from dataclasses import asdict
from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
    load_capacity_safe_bars,
    summarize_capacity_safe_price_volume_prescreen,
)
from quant_robot.ops.event_factor_preregistration import (
    SAFETY,
    EventFactorCandidateSpec,
    default_event_factor_candidate_specs,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "event_factor_pit_ic_prescreen"
NEXT_DIRECTION_WITH_LEADS = "round148_event_factor_neutral_lead_dedup_before_portfolio_conversion"
NEXT_DIRECTION_WITHOUT_LEADS = "round148_rotate_or_repair_event_factor_after_pit_ic_prescreen_failure"
AVAILABLE_ROUND146_EVENT_FACTORS = {
    "event_forecast_profit_revision_1q",
    "event_express_profit_surprise_1q",
    "event_dividend_cash_yield_announced_1y",
    "event_repurchase_amount_to_mv_20",
    "event_repurchase_amount_to_adv20_industry_relative_20",
    "event_repurchase_amount_to_adv20_liquidity_residual_20",
    "event_holder_number_contraction_2q",
    "event_share_unlock_pressure_60",
    "event_top_holder_concentration_change_1q",
    "event_pledge_ratio_relief_1q",
}
REPURCHASE_AMOUNT_TO_ADV20_FACTORS = {
    "event_repurchase_amount_to_mv_20",
    "event_repurchase_amount_to_adv20_industry_relative_20",
    "event_repurchase_amount_to_adv20_liquidity_residual_20",
}
REPURCHASE_CONTEXTUAL_REPAIR_FACTORS = {
    "event_repurchase_amount_to_adv20_industry_relative_20",
    "event_repurchase_amount_to_adv20_liquidity_residual_20",
}
FORECAST_GUIDANCE_UNCERTAINTY_FACTORS = {
    "event_forecast_guidance_confidence_1q",
    "event_forecast_uncertainty_compression_1q",
    "event_forecast_positive_floor_skew_1q",
}
FORECAST_EXPRESS_DISAGREEMENT_FACTORS = {
    "event_forecast_express_disagreement_1q",
    "event_forecast_express_disagreement_industry_relative_1q",
    "event_forecast_express_stale_forecast_correction_1q",
}
RESULT_COLUMNS = [
    "factor_name",
    "horizon",
    "ic_observations",
    "mean_spearman_ic",
    "icir",
    "ic_t_stat",
    "ic_p_value",
    "fdr_significant",
    "ic_positive_rate",
    "quantile_spread",
    "quantile_monotonicity",
    "avg_top_quantile_turnover",
    "industry_neutral_observations",
    "mean_industry_neutral_rank_ic",
    "industry_neutral_rank_ic_t_stat",
    "industry_neutral_rank_ic_p_value",
    "industry_neutral_retention_ratio",
    "size_neutral_observations",
    "mean_size_neutral_rank_ic",
    "size_neutral_rank_ic_t_stat",
    "size_neutral_rank_ic_p_value",
    "size_neutral_retention_ratio",
    "median_cross_section",
    "unique_dates",
    "unique_assets",
    "ic_year_count",
    "mean_yearly_ic",
    "yearly_positive_ic_year_rate",
    "yearly_ic_failure_count",
    "research_lead",
    "promotion_allowed",
    "blockers",
]


def build_event_factor_pit_ic_prescreen(
    *,
    event_frames: dict[str, pd.DataFrame],
    stock_basic: pd.DataFrame,
    bars: pd.DataFrame | None = None,
    bars_roots: Iterable[str | Path] | None = None,
    candidate_specs: Sequence[EventFactorCandidateSpec] | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    pit_lag_trade_days: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 8,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
    min_neutral_rank_ic: float = 0.01,
    min_neutral_ic_t_stat: float = 2.0,
    min_neutral_retention: float = 0.50,
    min_ic_years: int = 5,
    min_yearly_positive_ic_year_rate: float = 0.60,
    report_title: str = "Event Factor PIT/IC Prescreen Round147",
    next_direction_with_leads: str = NEXT_DIRECTION_WITH_LEADS,
    next_direction_without_leads: str = NEXT_DIRECTION_WITHOUT_LEADS,
) -> dict[str, Any]:
    if bars is None:
        if bars_roots is None:
            raise ValueError("Either bars or bars_roots must be provided")
        bars = load_capacity_safe_bars(
            bars_roots,
            analysis_start_date=analysis_start_date,
            analysis_end_date=analysis_end_date,
            include_final_holdout=include_final_holdout,
        )
    clean_bars = _normalise_bars(bars)
    factor_frame = compute_event_factor_frame(
        event_frames,
        clean_bars,
        stock_basic,
        candidate_specs=candidate_specs,
        pit_lag_trade_days=pit_lag_trade_days,
    )
    factor_frame = _filter_date_window(
        factor_frame,
        start_date=analysis_start_date,
        end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    labels = make_forward_returns(
        clean_bars[["date", "asset_id", "market", "adj_close"]],
        horizons=horizons,
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_event_factor_pit_ic_prescreen(
        factor_frame,
        labels,
        stock_basic,
        expected_candidate_count=len(_available_specs(candidate_specs)),
        candidate_specs=_available_specs(candidate_specs),
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
        min_neutral_rank_ic=min_neutral_rank_ic,
        min_neutral_ic_t_stat=min_neutral_ic_t_stat,
        min_neutral_retention=min_neutral_retention,
        min_ic_years=min_ic_years,
        min_yearly_positive_ic_year_rate=min_yearly_positive_ic_year_rate,
        report_title=report_title,
        next_direction_with_leads=next_direction_with_leads,
        next_direction_without_leads=next_direction_without_leads,
    )
    result["data_window"] = _data_window(clean_bars, factor_frame, labels, event_frames)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "blocked_until_oos_and_neutral_ic_clearance",
    }
    result["pit_policy"] = {
        "pit_lag_trade_days": int(pit_lag_trade_days),
        "event_signal_date_rule": "first_trade_date_strictly_after_event_date_plus_extra_lag",
        "execution_lag": int(execution_lag),
        "same_day_event_trading_allowed": False,
    }
    result["event_snapshot_audit"] = _event_snapshot_audit(event_frames)
    result["markdown"] = render_event_factor_pit_ic_prescreen_markdown(result)
    return result


def compute_event_factor_frame(
    event_frames: dict[str, pd.DataFrame],
    bars: pd.DataFrame,
    stock_basic: pd.DataFrame,
    *,
    candidate_specs: Sequence[EventFactorCandidateSpec] | None = None,
    pit_lag_trade_days: int = 1,
) -> pd.DataFrame:
    specs = _available_specs(candidate_specs)
    clean_bars = _normalise_bars(bars)
    metadata = _normalise_stock_basic(stock_basic)
    pieces: list[pd.DataFrame] = []
    for spec in specs:
        if spec.factor_name == "event_forecast_profit_revision_1q":
            pieces.append(_forecast_factor(event_frames.get("forecast"), spec, metadata))
        elif spec.factor_name in FORECAST_GUIDANCE_UNCERTAINTY_FACTORS:
            pieces.append(_forecast_guidance_uncertainty_factor(event_frames.get("forecast"), spec, metadata))
        elif spec.factor_name in FORECAST_EXPRESS_DISAGREEMENT_FACTORS:
            pieces.append(
                _forecast_express_disagreement_factor(
                    event_frames.get("forecast"),
                    event_frames.get("express"),
                    spec,
                    metadata,
                )
            )
        elif spec.factor_name == "event_express_profit_surprise_1q":
            pieces.append(_express_profit_surprise_factor(event_frames.get("express"), spec, metadata))
        elif spec.factor_name == "event_dividend_cash_yield_announced_1y":
            pieces.append(_dividend_factor(event_frames.get("dividend"), spec, clean_bars, metadata))
        elif spec.factor_name in REPURCHASE_AMOUNT_TO_ADV20_FACTORS:
            pieces.append(_repurchase_factor(event_frames.get("repurchase"), spec, metadata))
        elif spec.factor_name == "event_holder_number_contraction_2q":
            pieces.append(_holder_number_factor(event_frames.get("stk_holdernumber"), spec, metadata))
        elif spec.factor_name == "event_share_unlock_pressure_60":
            pieces.append(_share_unlock_factor(event_frames.get("share_float"), spec, metadata, clean_bars))
        elif spec.factor_name == "event_top_holder_concentration_change_1q":
            pieces.append(
                _top_holder_concentration_factor(
                    event_frames.get("top10_holders"),
                    event_frames.get("top10_floatholders"),
                    spec,
                    metadata,
                )
            )
        elif spec.factor_name == "event_pledge_ratio_relief_1q":
            pieces.append(_pledge_ratio_relief_factor(event_frames.get("pledge_stat"), spec, metadata))
    pieces = [piece for piece in pieces if piece is not None and not piece.empty]
    if not pieces:
        return _empty_factor_frame()
    frame = _attach_or_keep_signal_dates(
        pd.concat(pieces, ignore_index=True),
        clean_bars,
        pit_lag_trade_days=pit_lag_trade_days,
    )
    frame = _attach_bar_context(frame, clean_bars)
    if frame.empty:
        return _empty_factor_frame()
    frame["factor_value"] = pd.to_numeric(frame["factor_value"], errors="coerce")
    frame = frame.dropna(subset=["date", "event_date", "asset_id", "factor_name", "factor_value"])
    grouped = (
        frame.groupby(["date", "asset_id", "market", "factor_name"], as_index=False, dropna=False)
        .agg(
            factor_value=("factor_value", "mean"),
            event_date=("event_date", "min"),
            amount=("amount", "median"),
            adv20_amount=("adv20_amount", "median"),
            log_adv20=("log_adv20", "median"),
            pit_lag_trade_days=("pit_lag_trade_days", "max"),
            source_event_count=("source_event_count", "sum"),
        )
        .sort_values(["factor_name", "date", "asset_id"])
        .reset_index(drop=True)
    )
    grouped = _apply_repurchase_contextual_repairs(grouped, metadata)
    return grouped


def summarize_event_factor_pit_ic_prescreen(
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    stock_basic: pd.DataFrame,
    *,
    expected_candidate_count: int | None = None,
    candidate_specs: Sequence[EventFactorCandidateSpec] | None = None,
    horizons: tuple[int, ...] | None = None,
    min_cross_section: int = 30,
    min_ic_observations: int = 8,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
    min_neutral_rank_ic: float = 0.01,
    min_neutral_ic_t_stat: float = 2.0,
    min_neutral_retention: float = 0.50,
    min_ic_years: int = 5,
    min_yearly_positive_ic_year_rate: float = 0.60,
    alpha: float = 0.05,
    min_abs_ic: float = 0.02,
    min_abs_icir: float = 0.30,
    min_positive_ic_rate: float = 0.55,
    report_title: str = "Event Factor PIT/IC Prescreen Round147",
    next_direction_with_leads: str = NEXT_DIRECTION_WITH_LEADS,
    next_direction_without_leads: str = NEXT_DIRECTION_WITHOUT_LEADS,
) -> dict[str, Any]:
    factors = _normalise_factor_frame(factor_frame)
    labels = labels.copy()
    if not labels.empty:
        labels["date"] = pd.to_datetime(labels["date"])
    base = summarize_capacity_safe_price_volume_prescreen(
        factors,
        labels,
        expected_candidate_count=expected_candidate_count,
        candidate_specs=candidate_specs or _available_specs(None),
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        alpha=alpha,
        min_abs_ic=min_abs_ic,
        min_abs_icir=min_abs_icir,
        min_positive_ic_rate=min_positive_ic_rate,
        max_top_quantile_turnover=1.0,
    )
    neutral_rows, neutral_observations = _neutral_rows(
        factors,
        labels,
        stock_basic,
        horizons=tuple(horizons or base["summary"].get("horizons", [])),
        min_cross_section=min_cross_section,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
    )
    neutral_by_key = {
        (row["factor_name"], int(row["horizon"])): row
        for row in neutral_rows
    }
    yearly_by_key = _yearly_ic_by_key(base.get("ic_observations", []))
    for row in base.get("results", []):
        neutral = neutral_by_key.get((row["factor_name"], int(row["horizon"])), _empty_neutral_summary(row))
        row.update(neutral)
        yearly = yearly_by_key.get((row["factor_name"], int(row["horizon"])), _empty_yearly_summary())
        row.update(yearly)
        industry_pass = _neutral_gate_pass(
            row,
            prefix="industry_neutral",
            min_neutral_rank_ic=min_neutral_rank_ic,
            min_neutral_ic_t_stat=min_neutral_ic_t_stat,
            min_neutral_retention=min_neutral_retention,
        )
        size_pass = _neutral_gate_pass(
            row,
            prefix="size_neutral",
            min_neutral_rank_ic=min_neutral_rank_ic,
            min_neutral_ic_t_stat=min_neutral_ic_t_stat,
            min_neutral_retention=min_neutral_retention,
        )
        yearly_pass = (
            int(row.get("ic_year_count", 0)) >= int(min_ic_years)
            and _gate_number(row.get("yearly_positive_ic_year_rate")) >= float(min_yearly_positive_ic_year_rate)
        )
        blockers = [
            blocker
            for blocker in row.get("blockers", [])
            if blocker != "top_quantile_turnover_too_high"
        ]
        row["event_turnover_diagnostic"] = {
            "avg_top_quantile_turnover": row.get("avg_top_quantile_turnover", 0.0),
            "used_as_gate": False,
            "reason": "Sparse event cohorts naturally rotate; turnover is gated during portfolio conversion, not PIT/IC prescreen.",
        }
        if not industry_pass:
            blockers.append("industry_neutral_ic_below_gate")
        if not size_pass:
            blockers.append("size_neutral_ic_below_gate")
        if int(row.get("ic_year_count", 0)) < int(min_ic_years):
            blockers.append("ic_year_coverage_below_gate")
        elif not yearly_pass:
            blockers.append("yearly_ic_stability_below_gate")
        blockers.append("promotion_requires_later_walk_forward_cost_capacity_regime_final_holdout")
        row["blockers"] = _dedupe(blockers)
        row["research_lead"] = bool(
            row.get("fdr_significant")
            and row.get("mean_spearman_ic", 0.0) >= min_abs_ic
            and row.get("icir", 0.0) >= min_abs_icir
            and row.get("ic_positive_rate", 0.0) >= min_positive_ic_rate
            and row.get("quantile_spread", 0.0) > 0.0
            and row.get("quantile_monotonicity", 0.0) >= 0.70
            and industry_pass
            and size_pass
            and yearly_pass
        )
        row["promotion_allowed"] = False
    base["results"] = sorted(base.get("results", []), key=lambda item: (not item["research_lead"], -abs(item["mean_spearman_ic"])))
    summary = base["summary"]
    summary["research_lead_count"] = sum(1 for row in base["results"] if row["research_lead"])
    summary["neutral_gate_pass_count"] = sum(
        1
        for row in base["results"]
        if "industry_neutral_ic_below_gate" not in row["blockers"]
        and "size_neutral_ic_below_gate" not in row["blockers"]
    )
    summary["year_coverage_pass_count"] = sum(
        1
        for row in base["results"]
        if "ic_year_coverage_below_gate" not in row["blockers"]
        and "yearly_ic_stability_below_gate" not in row["blockers"]
    )
    summary["promotion_allowed_candidates"] = 0
    summary["industry_neutral_observation_rows"] = sum(
        int(row.get("industry_neutral_observations", 0)) for row in base["results"]
    )
    summary["size_neutral_observation_rows"] = sum(
        int(row.get("size_neutral_observations", 0)) for row in base["results"]
    )
    summary["next_direction"] = next_direction_with_leads if summary["research_lead_count"] else next_direction_without_leads
    base.update(
        {
            "stage": STAGE,
            "report_title": report_title,
            "neutral_policy": {
                "min_neutral_rank_ic": min_neutral_rank_ic,
                "min_neutral_ic_t_stat": min_neutral_ic_t_stat,
                "min_neutral_retention": min_neutral_retention,
                "min_industries": min_industries,
                "min_assets_per_industry": min_assets_per_industry,
                "min_ic_years": int(min_ic_years),
                "min_yearly_positive_ic_year_rate": float(min_yearly_positive_ic_year_rate),
                "industry_neutral_method": "within_industry_rank_ic_by_date",
                "size_neutral_method": "daily_residual_rank_ic_against_log_adv20",
                "event_top_quantile_turnover_used_as_gate": False,
            },
            "multiple_testing_policy": {
                "alpha": alpha,
                "method": "Bonferroni and Benjamini-Hochberg FDR across event factor x horizon tests",
            },
            "promotion_policy": {
                "promotion_allowed": False,
                "portfolio_backtest_allowed_before_prescreen": False,
                "requires_next_gate": "event_neutral_lead_dedup_before_portfolio_conversion",
                "reason": "This is an event PIT/IC prescreen. Portfolio grids remain blocked until neutral IC, de-dup, walk-forward, cost/capacity, regime, and final-holdout gates clear.",
            },
            "candidate_specs": [_spec_payload(spec) for spec in (candidate_specs or _available_specs(None))],
            "neutral_observations": neutral_observations,
            "live_boundary_allowed": False,
            "safety": SAFETY,
        }
    )
    base["markdown"] = render_event_factor_pit_ic_prescreen_markdown(base)
    return base


def write_event_factor_pit_ic_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "event_factor_pit_ic_prescreen.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "event_factor_pit_ic_prescreen.md").write_text(
        render_event_factor_pit_ic_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "event_factor_pit_ic_prescreen_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(
        output_path / "event_factor_pit_ic_prescreen_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )
    _write_csv(
        output_path / "event_factor_pit_ic_prescreen_neutral_observations.csv",
        result.get("neutral_observations", []),
        [
            "factor_name",
            "horizon",
            "date",
            "industry_neutral_rank_ic",
            "size_neutral_rank_ic",
            "cross_section",
            "industry_count",
        ],
    )


def render_event_factor_pit_ic_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    neutral = result.get("neutral_policy", {})
    lines = [
        f"# {result.get('report_title', 'Event Factor PIT/IC Prescreen Round147')}",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Aligned rows: {summary.get('aligned_rows', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- FDR-significant tests: {summary.get('multiple_testing_lead_count', 0)}",
        f"- Neutral-gate pass tests: {summary.get('neutral_gate_pass_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Next direction: {summary.get('next_direction', NEXT_DIRECTION_WITHOUT_LEADS)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Neutral Policy",
        "",
        f"- Min neutral RankIC: {neutral.get('min_neutral_rank_ic', 0):.4f}",
        f"- Min neutral t-stat: {neutral.get('min_neutral_ic_t_stat', 0):.2f}",
        f"- Min neutral retention: {neutral.get('min_neutral_retention', 0):.2f}",
        "",
        "## Top Results",
        "",
        "| Factor | Horizon | IC | ICIR | t | IC>0 | Q5-Q1 | IndNeuIC | IndT | SizeNeuIC | SizeT | Lead |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in result.get("results", [])[:25]:
        lines.append(
            "| {factor_name} | {horizon} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {spread:.4f} | {ind:.4f} | {indt:.2f} | {size:.4f} | {sizet:.2f} | {lead} |".format(
                factor_name=row.get("factor_name", ""),
                horizon=int(row.get("horizon", 0)),
                ic=_number(row.get("mean_spearman_ic")),
                icir=_number(row.get("icir")),
                t=_number(row.get("ic_t_stat")),
                pos=_number(row.get("ic_positive_rate")),
                spread=_number(row.get("quantile_spread")),
                ind=_number(row.get("mean_industry_neutral_rank_ic")),
                indt=_number(row.get("industry_neutral_rank_ic_t_stat")),
                size=_number(row.get("mean_size_neutral_rank_ic")),
                sizet=_number(row.get("size_neutral_rank_ic_t_stat")),
                lead="yes" if row.get("research_lead") else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Event Snapshot Audit",
            "",
            "| Endpoint | Rows | Duplicate Rows | Date Ranges |",
            "|---|---:|---:|---|",
        ]
    )
    for endpoint, audit in result.get("event_snapshot_audit", {}).items():
        date_ranges = "; ".join(
            f"{column}:{value.get('min')}..{value.get('max')}"
            for column, value in audit.get("date_ranges", {}).items()
        )
        lines.append(
            "| {endpoint} | {rows} | {duplicates} | {ranges} |".format(
                endpoint=endpoint,
                rows=audit.get("rows", 0),
                duplicates=audit.get("duplicate_rows", 0),
                ranges=date_ranges or "none",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This stage tests event data as point-in-time signals only; it is not a portfolio backtest.",
            "- Event rows are shifted to a later tradable signal date before labels are joined.",
            "- Leads must survive industry and size neutral IC before any portfolio conversion is allowed.",
        ]
    )
    return "\n".join(lines) + "\n"


def _forecast_factor(frame: pd.DataFrame | None, spec: EventFactorCandidateSpec, metadata: pd.DataFrame) -> pd.DataFrame:
    base = _event_base(frame, metadata, event_date_column="ann_date")
    if base.empty:
        return _empty_raw_event_frame()
    p_mid = (_num(base, "p_change_min") + _num(base, "p_change_max")) / 2.0
    profit_mid = (_num(base, "net_profit_min") + _num(base, "net_profit_max")) / 2.0
    base["factor_value"] = p_mid.combine_first(profit_mid)
    return _raw_event_output(base, spec.factor_name, "forecast")


def _forecast_guidance_uncertainty_factor(
    frame: pd.DataFrame | None,
    spec: EventFactorCandidateSpec,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    base = _event_base(frame, metadata, event_date_column="ann_date")
    if base.empty:
        return _empty_raw_event_frame()
    p_min = _num(base, "p_change_min")
    p_max = _num(base, "p_change_max")
    profit_min = _num(base, "net_profit_min")
    profit_max = _num(base, "net_profit_max")
    midpoint = ((p_min + p_max) / 2.0).combine_first((profit_min + profit_max) / 2.0)
    width = (p_max - p_min).abs().combine_first((profit_max - profit_min).abs())
    floor = p_min.combine_first(profit_min)
    ceiling_abs = p_max.abs().combine_first(profit_max.abs())
    if spec.factor_name == "event_forecast_guidance_confidence_1q":
        base["factor_value"] = midpoint.clip(lower=0.0) / (width + 1.0)
    elif spec.factor_name == "event_forecast_uncertainty_compression_1q":
        base["factor_value"] = -width / (midpoint.abs() + 1.0)
    elif spec.factor_name == "event_forecast_positive_floor_skew_1q":
        base["factor_value"] = floor / (ceiling_abs + 1.0)
    else:
        return _empty_raw_event_frame()
    return _raw_event_output(base, spec.factor_name, "forecast")


def _forecast_express_disagreement_factor(
    forecast_frame: pd.DataFrame | None,
    express_frame: pd.DataFrame | None,
    spec: EventFactorCandidateSpec,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    forecast = _event_base(forecast_frame, metadata, event_date_column="ann_date")
    express = _event_base(express_frame, metadata, event_date_column="ann_date")
    if forecast.empty or express.empty:
        return _empty_raw_event_frame()

    forecast = forecast.copy()
    express = express.copy()
    forecast["end_date"] = _datetime_series(forecast, "end_date")
    express["end_date"] = _datetime_series(express, "end_date")
    forecast["forecast_midpoint"] = (_num(forecast, "p_change_min") + _num(forecast, "p_change_max")) / 2.0
    express["express_yoy_net_profit"] = _num(express, "yoy_net_profit")
    forecast = forecast.dropna(subset=["asset_id", "market", "event_date", "end_date", "forecast_midpoint"]).copy()
    express = express.dropna(subset=["asset_id", "market", "event_date", "end_date", "express_yoy_net_profit"]).copy()
    if forecast.empty or express.empty:
        return _empty_raw_event_frame()

    express = express.reset_index(drop=True)
    express["_express_row_id"] = express.index
    paired = express[
        ["_express_row_id", "asset_id", "market", "event_date", "end_date", "express_yoy_net_profit"]
    ].merge(
        forecast[["asset_id", "market", "event_date", "end_date", "forecast_midpoint"]].rename(
            columns={"event_date": "forecast_event_date"}
        ),
        on=["asset_id", "market", "end_date"],
        how="inner",
    )
    paired = paired[paired["forecast_event_date"] <= paired["event_date"]].copy()
    if paired.empty:
        return _empty_raw_event_frame()

    paired = (
        paired.sort_values(["_express_row_id", "forecast_event_date"])
        .groupby("_express_row_id", as_index=False, group_keys=False)
        .tail(1)
        .copy()
    )
    paired["disagreement"] = paired["express_yoy_net_profit"] - paired["forecast_midpoint"]
    if spec.factor_name == "event_forecast_express_disagreement_1q":
        paired["factor_value"] = paired["disagreement"]
    elif spec.factor_name == "event_forecast_express_disagreement_industry_relative_1q":
        industry = metadata[["asset_id", "industry"]].drop_duplicates("asset_id", keep="last")
        paired = paired.merge(industry, on="asset_id", how="left")
        paired["industry"] = paired["industry"].fillna("").astype(str)
        median = paired.groupby(["event_date", "industry"])["disagreement"].transform("median")
        paired["factor_value"] = paired["disagreement"] - median
    elif spec.factor_name == "event_forecast_express_stale_forecast_correction_1q":
        forecast_age = (paired["event_date"] - paired["forecast_event_date"]).dt.days.clip(lower=0)
        paired["factor_value"] = paired["disagreement"] * forecast_age.map(math.log1p)
    else:
        return _empty_raw_event_frame()

    paired["factor_name"] = spec.factor_name
    paired["endpoint"] = "forecast_express"
    paired["source_event_count"] = 2
    return paired[
        ["asset_id", "market", "event_date", "factor_name", "factor_value", "endpoint", "source_event_count"]
    ]


def _express_profit_surprise_factor(
    frame: pd.DataFrame | None,
    spec: EventFactorCandidateSpec,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    base = _event_base(frame, metadata, event_date_column="ann_date")
    if base.empty:
        return _empty_raw_event_frame()
    profit_z = _event_date_zscore(base, "yoy_net_profit")
    roe_z = _event_date_zscore(base, "diluted_roe")
    base["factor_value"] = (0.6 * profit_z + 0.4 * roe_z).combine_first(profit_z).combine_first(roe_z)
    return _raw_event_output(base, spec.factor_name, "express")


def _dividend_factor(
    frame: pd.DataFrame | None,
    spec: EventFactorCandidateSpec,
    bars: pd.DataFrame,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    base = _event_base(frame, metadata, event_date_column="ann_date")
    if base.empty:
        return _empty_raw_event_frame()
    cash = _num(base, "cash_div_tax").combine_first(_num(base, "cash_div"))
    prior_close = _prior_adj_close(base, bars)
    base["factor_value"] = cash / prior_close.where(prior_close > 0)
    return _raw_event_output(base, spec.factor_name, "dividend")


def _repurchase_factor(frame: pd.DataFrame | None, spec: EventFactorCandidateSpec, metadata: pd.DataFrame) -> pd.DataFrame:
    base = _event_base(frame, metadata, event_date_column="ann_date")
    if base.empty:
        return _empty_raw_event_frame()
    amount = _num(base, "amount")
    grouped = base.assign(amount_value=amount).groupby(["asset_id", "market", "event_date"], as_index=False)
    output = grouped.agg(factor_value=("amount_value", "sum"), source_event_count=("amount_value", "size"))
    output["factor_name"] = spec.factor_name
    output["endpoint"] = "repurchase"
    return output


def _holder_number_factor(frame: pd.DataFrame | None, spec: EventFactorCandidateSpec, metadata: pd.DataFrame) -> pd.DataFrame:
    base = _event_base(frame, metadata, event_date_column="ann_date")
    if base.empty:
        return _empty_raw_event_frame()
    base["end_date"] = pd.to_datetime(base.get("end_date"), errors="coerce")
    base["holder_num"] = _num(base, "holder_num")
    base = base.dropna(subset=["end_date", "holder_num"]).sort_values(["asset_id", "end_date", "event_date"])
    base["holder_change"] = base.groupby("asset_id")["holder_num"].pct_change()
    base["factor_value"] = -base["holder_change"]
    return _raw_event_output(base, spec.factor_name, "stk_holdernumber")


def _share_unlock_factor(
    frame: pd.DataFrame | None,
    spec: EventFactorCandidateSpec,
    metadata: pd.DataFrame,
    bars: pd.DataFrame,
) -> pd.DataFrame:
    base = _event_base(frame, metadata, event_date_column="ann_date")
    if base.empty:
        return _empty_raw_event_frame()
    base["float_date"] = pd.to_datetime(base.get("float_date"), errors="coerce")
    base["float_ratio_value"] = _num(base, "float_ratio")
    base["float_share_value"] = _num(base, "float_share")
    valid = base.dropna(subset=["float_date"]).copy()
    if valid.empty:
        return _empty_raw_event_frame()
    grouped = (
        valid.groupby(["asset_id", "market", "event_date", "float_date"], as_index=False)
        .agg(
            float_ratio=("float_ratio_value", "sum"),
            float_share=("float_share_value", "sum"),
            source_event_count=("float_share_value", "size"),
        )
        .sort_values(["asset_id", "event_date", "float_date"])
    )
    unlock_pressure = grouped["float_ratio"].combine_first(grouped["float_share"])
    grouped["factor_value"] = -unlock_pressure
    grouped["factor_name"] = spec.factor_name
    grouped["endpoint"] = "share_float"
    expanded = _expand_share_unlock_window(grouped, bars, window=int(spec.windows[0]) if spec.windows else 60)
    if expanded.empty:
        return _empty_raw_event_frame()
    expanded = (
        expanded.groupby(["date", "asset_id", "market", "event_date", "factor_name", "endpoint"], as_index=False)
        .agg(factor_value=("factor_value", "sum"), source_event_count=("source_event_count", "sum"))
        .sort_values(["factor_name", "date", "asset_id"])
    )
    expanded["pit_lag_trade_days"] = 1
    return expanded[
        [
            "date",
            "asset_id",
            "market",
            "event_date",
            "factor_name",
            "factor_value",
            "endpoint",
            "source_event_count",
            "pit_lag_trade_days",
        ]
    ]


def _expand_share_unlock_window(frame: pd.DataFrame, bars: pd.DataFrame, *, window: int) -> pd.DataFrame:
    if frame.empty:
        return _empty_raw_event_frame()
    trade_dates = pd.Index(sorted(pd.to_datetime(bars["date"]).dropna().unique()))
    if trade_dates.empty:
        return _empty_raw_event_frame()
    rows: list[dict[str, Any]] = []
    lookback = max(int(window), 1)
    for row in frame.itertuples(index=False):
        ann_date = pd.Timestamp(getattr(row, "event_date"))
        float_date = pd.Timestamp(getattr(row, "float_date"))
        if pd.isna(ann_date) or pd.isna(float_date) or float_date <= ann_date:
            continue
        first_after_announcement = trade_dates.searchsorted(ann_date, side="right")
        first_after_float = trade_dates.searchsorted(float_date, side="right")
        start_index = max(first_after_announcement, first_after_float - lookback)
        if start_index >= first_after_float:
            continue
        for signal_date in trade_dates[start_index:first_after_float]:
            rows.append(
                {
                    "date": pd.Timestamp(signal_date),
                    "asset_id": str(getattr(row, "asset_id")),
                    "market": str(getattr(row, "market")),
                    "event_date": ann_date,
                    "factor_name": str(getattr(row, "factor_name")),
                    "factor_value": float(getattr(row, "factor_value")),
                    "endpoint": str(getattr(row, "endpoint")),
                    "source_event_count": int(getattr(row, "source_event_count")),
                }
            )
    if not rows:
        return _empty_raw_event_frame()
    return pd.DataFrame(rows)


def _top_holder_concentration_factor(
    holders: pd.DataFrame | None,
    floatholders: pd.DataFrame | None,
    spec: EventFactorCandidateSpec,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    pieces = []
    for frame, source, weight in [(holders, "top10_holders", 0.5), (floatholders, "top10_floatholders", 0.5)]:
        base = _event_base(frame, metadata, event_date_column="ann_date")
        if base.empty:
            continue
        base["end_date"] = pd.to_datetime(base.get("end_date"), errors="coerce")
        base["hold_ratio"] = _num(base, "hold_ratio")
        grouped = (
            base.dropna(subset=["end_date", "hold_ratio"])
            .groupby(["asset_id", "market", "event_date", "end_date"], as_index=False)
            .agg(concentration=("hold_ratio", "sum"))
        )
        grouped["source"] = source
        grouped["weighted_concentration"] = grouped["concentration"] * weight
        pieces.append(grouped)
    if not pieces:
        return _empty_raw_event_frame()
    combined = (
        pd.concat(pieces, ignore_index=True)
        .groupby(["asset_id", "market", "event_date", "end_date"], as_index=False)
        .agg(concentration=("weighted_concentration", "sum"))
        .sort_values(["asset_id", "end_date", "event_date"])
    )
    combined["factor_value"] = combined.groupby("asset_id")["concentration"].diff()
    combined["factor_name"] = spec.factor_name
    combined["endpoint"] = "top_holder_concentration"
    combined["source_event_count"] = 1
    return combined[["asset_id", "market", "event_date", "factor_name", "factor_value", "endpoint", "source_event_count"]]


def _pledge_ratio_relief_factor(frame: pd.DataFrame | None, spec: EventFactorCandidateSpec, metadata: pd.DataFrame) -> pd.DataFrame:
    base = _event_base(frame, metadata, event_date_column="end_date")
    if base.empty:
        return _empty_raw_event_frame()
    base["end_date"] = pd.to_datetime(base.get("end_date"), errors="coerce")
    base["pledge_ratio"] = _num(base, "pledge_ratio")
    base = base.dropna(subset=["end_date", "pledge_ratio"]).sort_values(["asset_id", "end_date", "event_date"])
    if base.empty:
        return _empty_raw_event_frame()
    grouped = (
        base.groupby(["asset_id", "market", "event_date", "end_date"], as_index=False)
        .agg(pledge_ratio=("pledge_ratio", "mean"), source_event_count=("pledge_ratio", "size"))
        .sort_values(["asset_id", "end_date", "event_date"])
    )
    grouped["pledge_ratio_change"] = grouped.groupby("asset_id")["pledge_ratio"].diff()
    grouped["factor_value"] = -grouped["pledge_ratio_change"]
    grouped["factor_name"] = spec.factor_name
    grouped["endpoint"] = "pledge_stat"
    return grouped[["asset_id", "market", "event_date", "factor_name", "factor_value", "endpoint", "source_event_count"]]


def _event_base(frame: pd.DataFrame | None, metadata: pd.DataFrame, *, event_date_column: str) -> pd.DataFrame:
    if frame is None or frame.empty:
        return _empty_raw_event_frame()
    source = frame.copy()
    if "ts_code" not in source.columns and "symbol" in source.columns:
        source["ts_code"] = source["symbol"]
    if event_date_column not in source.columns and "event_date" in source.columns:
        event_date_column = "event_date"
    if "ts_code" not in source.columns or event_date_column not in source.columns:
        return _empty_raw_event_frame()
    symbol_map = dict(zip(metadata["symbol"], metadata["asset_id"]))
    source["asset_id"] = source["ts_code"].astype(str).map(symbol_map)
    missing = source["asset_id"].isna()
    if missing.any():
        source.loc[missing, "asset_id"] = source.loc[missing, "ts_code"].map(_symbol_to_asset_id)
    source["market"] = "CN"
    source["event_date"] = pd.to_datetime(source[event_date_column], errors="coerce")
    source = source.dropna(subset=["asset_id", "event_date"]).copy()
    source["asset_id"] = source["asset_id"].astype(str)
    return source


def _raw_event_output(base: pd.DataFrame, factor_name: str, endpoint: str) -> pd.DataFrame:
    output = base.copy()
    output["factor_name"] = factor_name
    output["endpoint"] = endpoint
    output["source_event_count"] = 1
    return output[["asset_id", "market", "event_date", "factor_name", "factor_value", "endpoint", "source_event_count"]]


def _attach_or_keep_signal_dates(frame: pd.DataFrame, bars: pd.DataFrame, *, pit_lag_trade_days: int) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    if "date" not in frame:
        return _attach_signal_dates(frame, bars, pit_lag_trade_days=pit_lag_trade_days)
    dated = frame[frame["date"].notna()].copy()
    undated = frame[frame["date"].isna()].drop(columns=["date"]).copy()
    pieces = []
    if not dated.empty:
        dated["date"] = pd.to_datetime(dated["date"])
        if "pit_lag_trade_days" not in dated:
            dated["pit_lag_trade_days"] = int(pit_lag_trade_days)
        dated["pit_lag_trade_days"] = dated["pit_lag_trade_days"].fillna(int(pit_lag_trade_days)).astype(int)
        pieces.append(dated)
    if not undated.empty:
        pieces.append(_attach_signal_dates(undated, bars, pit_lag_trade_days=pit_lag_trade_days))
    if not pieces:
        return frame.iloc[0:0].copy()
    return pd.concat(pieces, ignore_index=True).reset_index(drop=True)


def _attach_signal_dates(frame: pd.DataFrame, bars: pd.DataFrame, *, pit_lag_trade_days: int) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    trade_dates = pd.Index(sorted(pd.to_datetime(bars["date"]).dropna().unique()))
    if trade_dates.empty:
        return frame.iloc[0:0].copy()
    output = frame.copy()
    event_dates = pd.to_datetime(output["event_date"], errors="coerce")
    signal_dates = []
    extra_lag = max(int(pit_lag_trade_days), 1) - 1
    for event_date in event_dates:
        if pd.isna(event_date):
            signal_dates.append(pd.NaT)
            continue
        index = trade_dates.searchsorted(event_date, side="right") + extra_lag
        signal_dates.append(trade_dates[index] if index < len(trade_dates) else pd.NaT)
    output["date"] = pd.to_datetime(signal_dates)
    output["pit_lag_trade_days"] = int(pit_lag_trade_days)
    return output.dropna(subset=["date"]).reset_index(drop=True)


def _attach_bar_context(frame: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    context = _bar_context(bars)
    output = frame.merge(context, on=["date", "asset_id", "market"], how="left", validate="many_to_one")
    if "factor_name" in output:
        mask = output["factor_name"].isin(REPURCHASE_AMOUNT_TO_ADV20_FACTORS)
        output.loc[mask, "factor_value"] = (
            pd.to_numeric(output.loc[mask, "factor_value"], errors="coerce")
            / pd.to_numeric(output.loc[mask, "adv20_amount"], errors="coerce").where(output.loc[mask, "adv20_amount"] > 0)
        )
    return output


def _apply_repurchase_contextual_repairs(frame: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or not set(frame["factor_name"]).intersection(REPURCHASE_CONTEXTUAL_REPAIR_FACTORS):
        return frame
    output = frame.copy()
    industry_meta = metadata[["asset_id", "industry"]].drop_duplicates("asset_id", keep="last")
    if "industry" in output:
        output = output.drop(columns=["industry"])
    output = output.merge(industry_meta, on="asset_id", how="left", validate="many_to_one")
    output["industry"] = output["industry"].fillna("").astype(str)

    industry_mask = output["factor_name"] == "event_repurchase_amount_to_adv20_industry_relative_20"
    if industry_mask.any():
        eligible = industry_mask & (output["industry"].str.strip() != "")
        industry_median = output.loc[eligible].groupby(["date", "market", "industry"])["factor_value"].transform("median")
        output.loc[eligible, "factor_value"] = output.loc[eligible, "factor_value"] - industry_median
        output.loc[industry_mask & ~eligible, "factor_value"] = pd.NA

    residual_mask = output["factor_name"] == "event_repurchase_amount_to_adv20_liquidity_residual_20"
    if residual_mask.any():
        for (_, _), index in output.loc[residual_mask].groupby(["date", "market"], sort=False).groups.items():
            group = output.loc[index]
            residual = _simple_residual(
                pd.to_numeric(group["factor_value"], errors="coerce").rank(method="average"),
                pd.to_numeric(group["log_adv20"], errors="coerce"),
            )
            output.loc[index, "factor_value"] = residual

    return (
        output.drop(columns=["industry"])
        .dropna(subset=["factor_value"])
        .sort_values(["factor_name", "date", "asset_id"])
        .reset_index(drop=True)
    )


def _bar_context(bars: pd.DataFrame) -> pd.DataFrame:
    frame = _normalise_bars(bars).sort_values(["asset_id", "date"]).copy()
    frame["adv20_amount"] = frame.groupby("asset_id")["amount"].transform(lambda item: item.rolling(20, min_periods=5).mean())
    frame["log_adv20"] = pd.to_numeric(frame["adv20_amount"], errors="coerce").where(frame["adv20_amount"] > 0).map(
        lambda value: math.log(value) if _is_finite(value) and value > 0 else pd.NA
    )
    return frame[["date", "asset_id", "market", "amount", "adv20_amount", "log_adv20"]]


def _prior_adj_close(events: pd.DataFrame, bars: pd.DataFrame) -> pd.Series:
    clean_bars = _normalise_bars(bars)
    by_asset = {
        asset_id: group.sort_values("date")[["date", "adj_close"]].reset_index(drop=True)
        for asset_id, group in clean_bars.groupby("asset_id", sort=False)
    }
    values = []
    for row in events.itertuples(index=False):
        group = by_asset.get(str(getattr(row, "asset_id")))
        event_date = pd.Timestamp(getattr(row, "event_date"))
        if group is None or group.empty:
            values.append(float("nan"))
            continue
        dates = pd.Index(group["date"])
        index = dates.searchsorted(event_date, side="right") - 1
        values.append(float(group.iloc[index]["adj_close"]) if index >= 0 else float("nan"))
    return pd.Series(values, index=events.index, dtype=float)


def _neutral_rows(
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    stock_basic: pd.DataFrame,
    *,
    horizons: tuple[int, ...],
    min_cross_section: int,
    min_industries: int,
    min_assets_per_industry: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if factor_frame.empty or labels.empty:
        return [], []
    metadata = _normalise_stock_basic(stock_basic)[["asset_id", "industry"]].drop_duplicates("asset_id", keep="last")
    rows: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    labels_by_horizon = {
        int(horizon): group.drop(columns=["horizon"]).copy()
        for horizon, group in labels[labels["horizon"].isin(horizons)].groupby("horizon", sort=False)
    }
    for factor_name, factor_group in factor_frame.groupby("factor_name", sort=False):
        for horizon in horizons:
            label_group = labels_by_horizon.get(int(horizon), pd.DataFrame())
            merged = factor_group.merge(label_group, on=["date", "asset_id", "market"], how="inner")
            merged = merged.merge(metadata, on="asset_id", how="left")
            ind_values: list[float] = []
            size_values: list[float] = []
            for signal_date, date_frame in merged.groupby("date", sort=True):
                valid = date_frame.dropna(subset=["factor_value", "forward_return"]).copy()
                if len(valid) < min_cross_section:
                    continue
                industry_ic = _industry_neutral_rank_ic(
                    valid,
                    min_industries=min_industries,
                    min_assets_per_industry=min_assets_per_industry,
                )
                size_ic = _size_neutral_rank_ic(valid)
                if _is_finite(industry_ic):
                    ind_values.append(float(industry_ic))
                if _is_finite(size_ic):
                    size_values.append(float(size_ic))
                observations.append(
                    {
                        "factor_name": str(factor_name),
                        "horizon": int(horizon),
                        "date": pd.Timestamp(signal_date).date().isoformat(),
                        "industry_neutral_rank_ic": float(industry_ic) if _is_finite(industry_ic) else None,
                        "size_neutral_rank_ic": float(size_ic) if _is_finite(size_ic) else None,
                        "cross_section": int(len(valid)),
                        "industry_count": int(valid["industry"].nunique()) if "industry" in valid else 0,
                    }
                )
            row = {
                "factor_name": str(factor_name),
                "horizon": int(horizon),
                **_neutral_summary("industry_neutral", ind_values),
                **_neutral_summary("size_neutral", size_values),
            }
            rows.append(row)
    return rows, observations


def _yearly_ic_by_key(observations: Sequence[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
    values: dict[tuple[str, int], dict[str, list[float]]] = {}
    for row in observations:
        factor_name = str(row.get("factor_name", ""))
        horizon = int(_number(row.get("horizon")))
        date_value = str(row.get("date", ""))
        year = date_value[:4]
        ic = _gate_number(row.get("spearman_ic"))
        if not factor_name or not year or not _is_finite(ic):
            continue
        values.setdefault((factor_name, horizon), {}).setdefault(year, []).append(float(ic))
    output: dict[tuple[str, int], dict[str, Any]] = {}
    for key, by_year in values.items():
        yearly_means = [float(pd.Series(items, dtype=float).mean()) for items in by_year.values() if items]
        if not yearly_means:
            output[key] = _empty_yearly_summary()
            continue
        positive_years = sum(1 for value in yearly_means if value > 0.0)
        output[key] = {
            "ic_year_count": int(len(yearly_means)),
            "mean_yearly_ic": float(pd.Series(yearly_means, dtype=float).mean()),
            "yearly_positive_ic_year_rate": float(positive_years / len(yearly_means)),
            "yearly_ic_failure_count": int(len(yearly_means) - positive_years),
        }
    return output


def _empty_yearly_summary() -> dict[str, Any]:
    return {
        "ic_year_count": 0,
        "mean_yearly_ic": 0.0,
        "yearly_positive_ic_year_rate": 0.0,
        "yearly_ic_failure_count": 0,
    }


def _industry_neutral_rank_ic(
    frame: pd.DataFrame,
    *,
    min_industries: int,
    min_assets_per_industry: int,
) -> float:
    valid = frame[frame["industry"].notna() & (frame["industry"].astype(str).str.strip() != "")].copy()
    if valid.empty:
        return float("nan")
    counts = valid.groupby("industry")["asset_id"].nunique()
    eligible = valid[valid["industry"].isin(set(counts[counts >= min_assets_per_industry].index))].copy()
    if eligible["industry"].nunique() < min_industries:
        return float("nan")
    eligible["factor_rank_within_industry"] = eligible.groupby("industry")["factor_value"].rank(method="average")
    eligible["return_rank_within_industry"] = eligible.groupby("industry")["forward_return"].rank(method="average")
    return _spearman(eligible["factor_rank_within_industry"], eligible["return_rank_within_industry"])


def _size_neutral_rank_ic(frame: pd.DataFrame) -> float:
    working = frame.dropna(subset=["factor_value", "forward_return"]).copy()
    if len(working) < 3:
        return float("nan")
    size = pd.to_numeric(working.get("log_adv20", pd.Series(index=working.index, dtype=float)), errors="coerce")
    if size.notna().sum() < 3 or size.nunique(dropna=True) < 2:
        return _spearman(working["factor_value"], working["forward_return"])
    factor_resid = _simple_residual(working["factor_value"].rank(method="average"), size)
    return_resid = _simple_residual(working["forward_return"].rank(method="average"), size)
    return _spearman(factor_resid, return_resid)


def _simple_residual(y: pd.Series, x: pd.Series) -> pd.Series:
    frame = pd.DataFrame({"y": pd.to_numeric(y, errors="coerce"), "x": pd.to_numeric(x, errors="coerce")}).dropna()
    output = pd.Series(index=y.index, dtype=float)
    if len(frame) < 3 or frame["x"].nunique() < 2:
        output.loc[frame.index] = frame["y"] - frame["y"].mean()
        return output
    x_centered = frame["x"] - frame["x"].mean()
    denominator = float((x_centered * x_centered).sum())
    if denominator == 0.0:
        output.loc[frame.index] = frame["y"] - frame["y"].mean()
        return output
    beta = float(((frame["y"] - frame["y"].mean()) * x_centered).sum() / denominator)
    alpha = float(frame["y"].mean() - beta * frame["x"].mean())
    output.loc[frame.index] = frame["y"] - (alpha + beta * frame["x"])
    return output


def _neutral_summary(prefix: str, values: list[float]) -> dict[str, Any]:
    series = pd.Series([value for value in values if _is_finite(value)], dtype=float)
    if series.empty:
        mean = 0.0
        t_stat = 0.0
        p_value = 1.0
    else:
        mean = float(series.mean())
        std = float(series.std(ddof=1)) if len(series) > 1 else 0.0
        t_stat = _t_stat(mean, std, len(series))
        p_value = _normal_two_sided_p_value(t_stat)
    return {
        f"{prefix}_observations": int(len(series)),
        f"mean_{prefix}_rank_ic": mean,
        f"{prefix}_rank_ic_t_stat": t_stat,
        f"{prefix}_rank_ic_p_value": p_value,
    }


def _empty_neutral_summary(row: dict[str, Any]) -> dict[str, Any]:
    output = {
        **_neutral_summary("industry_neutral", []),
        **_neutral_summary("size_neutral", []),
    }
    output["industry_neutral_retention_ratio"] = 0.0
    output["size_neutral_retention_ratio"] = 0.0
    return output


def _neutral_gate_pass(
    row: dict[str, Any],
    *,
    prefix: str,
    min_neutral_rank_ic: float,
    min_neutral_ic_t_stat: float,
    min_neutral_retention: float,
) -> bool:
    mean_key = f"mean_{prefix}_rank_ic"
    t_key = f"{prefix}_rank_ic_t_stat"
    obs_key = f"{prefix}_observations"
    retention_key = f"{prefix}_retention_ratio"
    mean = _gate_number(row.get(mean_key))
    t_stat = _gate_number(row.get(t_key))
    retention = _retention(mean, _gate_number(row.get("mean_spearman_ic")))
    row[retention_key] = retention
    return bool(
        int(row.get(obs_key, 0)) > 0
        and mean >= min_neutral_rank_ic
        and t_stat >= min_neutral_ic_t_stat
        and retention >= min_neutral_retention
    )


def _normalise_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return _empty_factor_frame()
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"])
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].fillna("CN").astype(str).str.upper()
    output["factor_name"] = output["factor_name"].astype(str)
    output["factor_value"] = pd.to_numeric(output["factor_value"], errors="coerce")
    for column in ["amount", "adv20_amount", "log_adv20"]:
        if column not in output:
            output[column] = pd.NA
        output[column] = pd.to_numeric(output[column], errors="coerce")
    return output.dropna(subset=["date", "asset_id", "market", "factor_name", "factor_value"]).reset_index(drop=True)


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing required columns: {', '.join(missing)}")
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    for column in ["adj_close", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    for column in ["high", "low"]:
        if column not in frame:
            frame[column] = frame["adj_close"]
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return (
        frame[(frame["market"] == "CN") & (frame["adj_close"] > 0)]
        .dropna(subset=required)
        .drop_duplicates(["date", "asset_id", "market"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _normalise_stock_basic(stock_basic: pd.DataFrame) -> pd.DataFrame:
    frame = stock_basic.copy()
    if "asset_id" not in frame and "ts_code" in frame:
        frame["asset_id"] = frame["ts_code"].map(_symbol_to_asset_id)
    for column in ["asset_id", "symbol", "industry"]:
        if column not in frame:
            frame[column] = ""
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["symbol"] = frame["symbol"].astype(str)
    frame["industry"] = frame["industry"].fillna("").astype(str)
    return frame.drop_duplicates("asset_id", keep="last").reset_index(drop=True)


def _filter_date_window(
    frame: pd.DataFrame,
    *,
    start_date: str,
    end_date: str,
    include_final_holdout: bool,
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"])
    end = output["date"].max() if include_final_holdout else pd.Timestamp(end_date)
    return output[(output["date"] >= pd.Timestamp(start_date)) & (output["date"] <= end)].reset_index(drop=True)


def _available_specs(candidate_specs: Sequence[EventFactorCandidateSpec] | None) -> list[EventFactorCandidateSpec]:
    specs = list(candidate_specs or default_event_factor_candidate_specs())
    allowed = AVAILABLE_ROUND146_EVENT_FACTORS | FORECAST_GUIDANCE_UNCERTAINTY_FACTORS | FORECAST_EXPRESS_DISAGREEMENT_FACTORS
    return [spec for spec in specs if spec.factor_name in allowed]


def _event_snapshot_audit(event_frames: dict[str, pd.DataFrame]) -> dict[str, dict[str, Any]]:
    audit: dict[str, dict[str, Any]] = {}
    for endpoint, frame in sorted(event_frames.items()):
        if not isinstance(frame, pd.DataFrame):
            audit[str(endpoint)] = {"rows": 0, "columns": [], "duplicate_rows": 0, "date_ranges": {}}
            continue
        audit[str(endpoint)] = {
            "rows": int(len(frame)),
            "columns": [str(column) for column in frame.columns],
            "duplicate_rows": int(len(frame) - len(frame.drop_duplicates())) if not frame.empty else 0,
            "date_ranges": _date_ranges(frame),
        }
    return audit


def _date_ranges(frame: pd.DataFrame) -> dict[str, dict[str, str | None]]:
    ranges: dict[str, dict[str, str | None]] = {}
    for column in ("ann_date", "end_date", "float_date", "ex_date", "pay_date", "trade_date"):
        if column not in frame:
            continue
        dates = pd.to_datetime(frame[column], errors="coerce").dropna()
        if dates.empty:
            continue
        ranges[column] = {
            "min": pd.Timestamp(dates.min()).date().isoformat(),
            "max": pd.Timestamp(dates.max()).date().isoformat(),
        }
    return ranges


def _data_window(
    bars: pd.DataFrame,
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    event_frames: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "min_signal_date": _min_date(factor_frame, "date"),
        "max_signal_date": _max_date(factor_frame, "date"),
        "min_label_date": _min_date(labels, "date"),
        "max_label_date": _max_date(labels, "date"),
        "bar_rows": int(len(bars)),
        "bar_assets": int(bars["asset_id"].nunique()) if not bars.empty else 0,
        "factor_rows": int(len(factor_frame)),
        "event_rows_by_endpoint": {endpoint: int(len(frame)) for endpoint, frame in event_frames.items()},
    }


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "event_date",
            "asset_id",
            "market",
            "factor_name",
            "factor_value",
            "amount",
            "adv20_amount",
            "log_adv20",
            "pit_lag_trade_days",
            "source_event_count",
        ]
    )


def _empty_raw_event_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["asset_id", "market", "event_date", "factor_name", "factor_value", "endpoint", "source_event_count"])


def _symbol_to_asset_id(symbol: Any) -> str | None:
    text = str(symbol).strip()
    if not text or "." not in text:
        return None
    code, suffix = text.split(".", 1)
    exchange = {"SZ": "XSHE", "SH": "XSHG", "BJ": "XBEI"}.get(suffix.upper())
    if not exchange:
        return None
    return f"CN_{exchange}_{code}"


def _spearman(left: pd.Series, right: pd.Series) -> float:
    aligned = pd.concat([left, right], axis=1).dropna()
    if len(aligned) < 2:
        return float("nan")
    lval = aligned.iloc[:, 0]
    rval = aligned.iloc[:, 1]
    if lval.nunique() < 2 or rval.nunique() < 2:
        return float("nan")
    return float(lval.rank(method="average").corr(rval.rank(method="average")))


def _t_stat(mean: float, std: float, observations: int) -> float:
    if observations <= 1:
        return 0.0
    if std == 0:
        if mean > 0:
            return float("inf")
        if mean < 0:
            return float("-inf")
        return 0.0
    return float(mean / (std / math.sqrt(observations)))


def _normal_two_sided_p_value(t_stat: float) -> float:
    if math.isinf(t_stat):
        return 0.0
    if not math.isfinite(t_stat):
        return 1.0
    return float(math.erfc(abs(t_stat) / math.sqrt(2.0)))


def _retention(neutral: float, overall: float) -> float:
    if not _is_finite(neutral) or not _is_finite(overall) or overall == 0.0:
        return 0.0
    return float(abs(neutral) / abs(overall))


def _num(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _datetime_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(pd.NaT, index=frame.index, dtype="datetime64[ns]")
    return pd.to_datetime(frame[column], errors="coerce")


def _event_date_zscore(frame: pd.DataFrame, column: str) -> pd.Series:
    values = _num(frame, column)

    def normalize(group: pd.Series) -> pd.Series:
        valid = group.dropna()
        if valid.empty:
            return pd.Series(pd.NA, index=group.index, dtype="Float64")
        std = float(valid.std(ddof=0))
        if not _is_finite(std) or std == 0.0:
            return pd.Series(0.0, index=group.index, dtype=float).where(group.notna(), pd.NA)
        return (group - float(valid.mean())) / std

    return values.groupby(pd.to_datetime(frame["event_date"]), group_keys=False).apply(normalize)


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _gate_number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _is_finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()


def _spec_payload(spec: Any) -> dict[str, Any]:
    if hasattr(spec, "__dataclass_fields__"):
        payload = asdict(spec)
        for key, value in list(payload.items()):
            if isinstance(value, tuple):
                payload[key] = list(value)
        return payload
    return dict(spec)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
