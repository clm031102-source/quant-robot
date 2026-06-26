from __future__ import annotations

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
)
from quant_robot.ops.event_factor_pit_ic_prescreen import (
    RESULT_COLUMNS,
    _data_window,
    _filter_date_window,
    _normalise_bars,
    compute_event_factor_frame,
    render_event_factor_pit_ic_prescreen_markdown,
    summarize_event_factor_pit_ic_prescreen,
)
from quant_robot.ops.event_factor_preregistration import (
    EventFactorCandidateSpec,
    SAFETY,
    default_event_factor_candidate_specs,
)
from quant_robot.ops.profitability_quality_preregistration import _sanitize
from quant_robot.research.labels import make_forward_returns


STAGE = "event_contextual_underreaction_prescreen"
ROUND_CONTEXT = {
    "round": "round248",
    "source_review": "docs/research/cn_stock_round245_247_three_round_review_2026-06-25.md",
    "required_rotation": "external_revision_or_nonfinancial_event_context",
    "blocked_reentry_families": [
        "accounting_quality_realized_statement_formula_mutations",
        "statement_cash_conversion_muted_reaction",
        "statement_profitability_revision_without_external_expectation_data",
    ],
}
NEXT_DIRECTION_WITH_LEADS = "round249_event_contextual_underreaction_reference_dedup_walk_forward_preflight"
NEXT_DIRECTION_WITHOUT_LEADS = "round249_rotate_or_repair_event_contextual_underreaction_after_long_cycle_prescreen_failure"
BASE_EVENT_FACTORS = (
    "event_repurchase_amount_to_mv_20",
    "event_holder_number_contraction_2q",
)
CONTEXTUAL_EVENT_FACTOR_NAMES = (
    "event_repurchase_underreaction_20",
    "event_repurchase_quiet_volume_20",
    "event_holder_contraction_underreaction_20",
    "event_holder_contraction_low_vol_20",
)
CONTEXT_COLUMNS = [
    "pre_signal_return_20",
    "amount_trend_5_20",
    "realized_vol_20",
]


def default_event_contextual_underreaction_candidate_specs() -> list[EventFactorCandidateSpec]:
    controls = (
        "event_signal_date_after_ann_date",
        "signal_uses_close_available_before_next_execution",
        "same_parameter_2015_2025_long_cycle_required",
        "industry_and_size_neutral_gate_required",
        "fdr_multiple_testing_gate_required",
        "portfolio_grid_blocked_before_walk_forward",
    )
    return [
        EventFactorCandidateSpec(
            factor_name="event_repurchase_underreaction_20",
            family="buyback_event_context",
            formula_template="0.65*cs_z(repurchase_amount/adv20) + 0.35*cs_z(-pre_signal_return_20)",
            direction="higher_is_better",
            required_endpoints=("repurchase",),
            required_fields=("ann_date", "amount"),
            event_date_fields=("ann_date",),
            windows=(20,),
            economic_rationale=(
                "Buyback announcements have better economic intuition when the stock has not already rallied "
                "before the next executable signal date."
            ),
            public_reference_tags=("buyback_anomaly", "event_study", "underreaction"),
            expected_failure_modes=("size_tail", "announced_not_executed", "event_reaction_already_priced"),
            pit_controls=controls,
        ),
        EventFactorCandidateSpec(
            factor_name="event_repurchase_quiet_volume_20",
            family="buyback_event_context",
            formula_template="0.65*cs_z(repurchase_amount/adv20) + 0.35*cs_z(-amount_trend_5_20)",
            direction="higher_is_better",
            required_endpoints=("repurchase",),
            required_fields=("ann_date", "amount"),
            event_date_fields=("ann_date",),
            windows=(20,),
            economic_rationale=(
                "A repurchase signal is more likely to be incremental when announcement interest has not "
                "already produced a short-term volume crowding spike."
            ),
            public_reference_tags=("buyback_anomaly", "event_study", "crowding_filter"),
            expected_failure_modes=("low_liquidity_artifact", "crowding_filter_overfit", "announcement_clustering"),
            pit_controls=controls,
        ),
        EventFactorCandidateSpec(
            factor_name="event_holder_contraction_underreaction_20",
            family="ownership_event_context",
            formula_template="0.65*cs_z(-holder_number_change) + 0.35*cs_z(-pre_signal_return_20)",
            direction="higher_is_better",
            required_endpoints=("stk_holdernumber",),
            required_fields=("ann_date", "end_date", "holder_num"),
            event_date_fields=("ann_date",),
            windows=(20,),
            economic_rationale=(
                "Falling shareholder count may proxy ownership concentration, but it is only useful if the "
                "price has not already reacted into the signal date."
            ),
            public_reference_tags=("ownership_concentration", "underreaction", "event_study"),
            expected_failure_modes=("quarterly_staleness", "small_cap_crowding_artifact", "reporting_lag"),
            pit_controls=controls,
        ),
        EventFactorCandidateSpec(
            factor_name="event_holder_contraction_low_vol_20",
            family="ownership_event_context",
            formula_template="0.65*cs_z(-holder_number_change) + 0.35*cs_z(-realized_vol_20)",
            direction="higher_is_better",
            required_endpoints=("stk_holdernumber",),
            required_fields=("ann_date", "end_date", "holder_num"),
            event_date_fields=("ann_date",),
            windows=(20,),
            economic_rationale=(
                "Ownership concentration is less likely to be a crash-risk artifact when paired with lower "
                "recent realized volatility."
            ),
            public_reference_tags=("ownership_concentration", "low_volatility", "event_study"),
            expected_failure_modes=("low_vol_beta", "quarterly_staleness", "industry_concentration"),
            pit_controls=controls,
        ),
    ]


def build_event_contextual_underreaction_prescreen(
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
    alpha: float = 0.05,
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
    specs = tuple(candidate_specs or default_event_contextual_underreaction_candidate_specs())
    factor_frame = compute_event_contextual_underreaction_factor_frame(
        event_frames,
        clean_bars,
        stock_basic,
        candidate_specs=specs,
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
        expected_candidate_count=len(specs),
        candidate_specs=specs,
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
        min_neutral_rank_ic=min_neutral_rank_ic,
        min_neutral_ic_t_stat=min_neutral_ic_t_stat,
        min_neutral_retention=min_neutral_retention,
        alpha=alpha,
    )
    result["stage"] = STAGE
    result["generated_at"] = date.today().isoformat()
    result["round_context"] = ROUND_CONTEXT
    result["summary"]["next_direction"] = (
        NEXT_DIRECTION_WITH_LEADS
        if int(result["summary"].get("research_lead_count", 0))
        else NEXT_DIRECTION_WITHOUT_LEADS
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
        "context_close_used_before_next_execution": True,
    }
    result["context_policy"] = {
        "context_columns": CONTEXT_COLUMNS,
        "context_available_at_signal_close": True,
        "trade_entry_after_signal": "controlled_by_execution_lag",
        "raw_event_families_reused": list(BASE_EVENT_FACTORS),
        "blocked_family_reentry": ROUND_CONTEXT["blocked_reentry_families"],
    }
    result["promotion_policy"] = {
        "promotion_allowed": False,
        "portfolio_backtest_allowed_before_prescreen": False,
        "requires_next_gate": "reference_dedup_walk_forward_cost_capacity_regime_after_contextual_event_lead",
        "reason": "Round248 is a long-cycle residual IC/neutral prescreen. Portfolio grids remain blocked.",
    }
    result["candidate_specs"] = [_spec_payload(spec) for spec in specs]
    result["live_boundary_allowed"] = False
    result["safety"] = SAFETY
    result["markdown"] = render_event_contextual_underreaction_markdown(result)
    return result


def compute_event_contextual_underreaction_factor_frame(
    event_frames: dict[str, pd.DataFrame],
    bars: pd.DataFrame,
    stock_basic: pd.DataFrame,
    *,
    candidate_specs: Sequence[EventFactorCandidateSpec] | None = None,
    pit_lag_trade_days: int = 1,
) -> pd.DataFrame:
    clean_bars = _normalise_bars(bars)
    base_specs = [spec for spec in default_event_factor_candidate_specs() if spec.factor_name in BASE_EVENT_FACTORS]
    base = compute_event_factor_frame(
        event_frames,
        clean_bars,
        stock_basic,
        candidate_specs=base_specs,
        pit_lag_trade_days=pit_lag_trade_days,
    )
    if base.empty:
        return _empty_contextual_factor_frame()
    context = _signal_context_frame(clean_bars)
    base = base.merge(context, on=["date", "asset_id", "market"], how="left", validate="many_to_one")
    specs = tuple(candidate_specs or default_event_contextual_underreaction_candidate_specs())
    allowed = {spec.factor_name for spec in specs}
    pieces = [
        _contextual_variant(
            base,
            source_factor="event_repurchase_amount_to_mv_20",
            output_factor="event_repurchase_underreaction_20",
            context_column="pre_signal_return_20",
            invert_context=True,
            allowed=allowed,
        ),
        _contextual_variant(
            base,
            source_factor="event_repurchase_amount_to_mv_20",
            output_factor="event_repurchase_quiet_volume_20",
            context_column="amount_trend_5_20",
            invert_context=True,
            allowed=allowed,
        ),
        _contextual_variant(
            base,
            source_factor="event_holder_number_contraction_2q",
            output_factor="event_holder_contraction_underreaction_20",
            context_column="pre_signal_return_20",
            invert_context=True,
            allowed=allowed,
        ),
        _contextual_variant(
            base,
            source_factor="event_holder_number_contraction_2q",
            output_factor="event_holder_contraction_low_vol_20",
            context_column="realized_vol_20",
            invert_context=True,
            allowed=allowed,
        ),
    ]
    pieces = [piece for piece in pieces if not piece.empty]
    if not pieces:
        return _empty_contextual_factor_frame()
    output = pd.concat(pieces, ignore_index=True)
    return (
        output.dropna(subset=["date", "event_date", "asset_id", "market", "factor_name", "factor_value"])
        .sort_values(["factor_name", "date", "asset_id"])
        .reset_index(drop=True)
    )


def write_event_contextual_underreaction_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "event_contextual_underreaction_prescreen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "event_contextual_underreaction_prescreen.md").write_text(
        render_event_contextual_underreaction_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "event_contextual_underreaction_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(
        output_path / "event_contextual_underreaction_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )
    _write_csv(
        output_path / "event_contextual_underreaction_neutral_observations.csv",
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


def render_event_contextual_underreaction_markdown(result: dict[str, Any]) -> str:
    base = render_event_factor_pit_ic_prescreen_markdown(result)
    summary = result.get("summary", {})
    lines = [
        "# Event Contextual Underreaction Prescreen Round248",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Round: {result.get('round_context', {}).get('round', 'round248')}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- Neutral gate passes: {summary.get('neutral_gate_pass_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Next direction: `{summary.get('next_direction', '')}`",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Round248 Context",
        "",
        "- Forced rotation after Round245-247: no more realized statement formula mutations.",
        "- Tested family: nonfinancial events plus price/liquidity context.",
        "- Context is measured at the signal close and execution is still delayed by the configured lag.",
        "",
    ]
    if "## Top Results" in base:
        lines.append(base.split("## Top Results", 1)[1].lstrip())
    else:
        lines.append(base)
    return "\n".join(lines)


def _contextual_variant(
    base: pd.DataFrame,
    *,
    source_factor: str,
    output_factor: str,
    context_column: str,
    invert_context: bool,
    allowed: set[str],
) -> pd.DataFrame:
    if output_factor not in allowed:
        return _empty_contextual_factor_frame()
    source = base[base["factor_name"] == source_factor].copy()
    if source.empty or context_column not in source:
        return _empty_contextual_factor_frame()
    source["base_event_z"] = _daily_zscore(source, source["factor_value"])
    context_values = pd.to_numeric(source[context_column], errors="coerce")
    if invert_context:
        context_values = -context_values
    source["context_z"] = _daily_zscore(source, context_values)
    source["factor_value"] = 0.65 * source["base_event_z"] + 0.35 * source["context_z"]
    source["factor_name"] = output_factor
    return source[
        [
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
            "pre_signal_return_20",
            "amount_trend_5_20",
            "realized_vol_20",
        ]
    ]


def _signal_context_frame(bars: pd.DataFrame) -> pd.DataFrame:
    frame = _normalise_bars(bars).sort_values(["asset_id", "date"]).copy()
    pieces = []
    for _, group in frame.groupby("asset_id", sort=False):
        group = group.copy()
        close = group["adj_close"]
        amount = group["amount"]
        returns = close.pct_change()
        adv20 = amount.rolling(20, min_periods=5).mean()
        amount_ma5 = amount.rolling(5, min_periods=3).mean()
        amount_ma20 = amount.rolling(20, min_periods=5).mean()
        output = group[["date", "asset_id", "market"]].copy()
        output["pre_signal_return_20"] = close.pct_change(20)
        output["amount_trend_5_20"] = amount_ma5 / amount_ma20.replace(0, pd.NA) - 1.0
        output["realized_vol_20"] = returns.rolling(20, min_periods=5).std(ddof=0)
        output["adv20_amount_context"] = adv20
        output["log_adv20_context"] = adv20.where(adv20 > 0).map(
            lambda value: math.log(value) if pd.notna(value) and value > 0 else pd.NA
        )
        pieces.append(output)
    if not pieces:
        return pd.DataFrame(
            columns=["date", "asset_id", "market", "pre_signal_return_20", "amount_trend_5_20", "realized_vol_20"]
        )
    context = pd.concat(pieces, ignore_index=True)
    return context.replace([float("inf"), float("-inf")], pd.NA)


def _daily_zscore(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    grouped = numeric.groupby(pd.to_datetime(frame["date"]))
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    zscore = (numeric - mean) / std.replace(0, pd.NA)
    rank = numeric.groupby(pd.to_datetime(frame["date"])).rank(pct=True)
    fallback = (rank - 0.5) * 2.0
    return zscore.combine_first(fallback).replace([float("inf"), float("-inf")], pd.NA)


def _empty_contextual_factor_frame() -> pd.DataFrame:
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
            "pre_signal_return_20",
            "amount_trend_5_20",
            "realized_vol_20",
        ]
    )


def _spec_payload(spec: EventFactorCandidateSpec) -> dict[str, Any]:
    return {
        "factor_name": spec.factor_name,
        "family": spec.family,
        "formula_template": spec.formula_template,
        "direction": spec.direction,
        "required_endpoints": list(spec.required_endpoints),
        "required_fields": list(spec.required_fields),
        "event_date_fields": list(spec.event_date_fields),
        "windows": list(spec.windows),
        "economic_rationale": spec.economic_rationale,
        "public_reference_tags": list(spec.public_reference_tags),
        "expected_failure_modes": list(spec.expected_failure_modes),
        "pit_controls": list(spec.pit_controls),
        "source_evidence_status": spec.source_evidence_status,
        "portfolio_backtest_allowed": bool(spec.portfolio_backtest_allowed),
        "promotion_allowed": bool(spec.promotion_allowed),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if isinstance(value, float) and pd.isna(value):
        return ""
    return value
