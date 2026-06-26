from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_preregistration import (
    DEFAULT_CAPACITY_FILTERS,
    SAFETY,
)
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
    RESULT_COLUMNS,
    load_capacity_safe_bars,
    summarize_capacity_safe_price_volume_prescreen,
)
from quant_robot.ops.capacity_safe_trend_accumulation_prescreen import (
    _add_cross_sectional_features,
    _data_window,
    _feature_frame,
    _sanitize,
    _spec_payload,
    _write_csv,
)
from quant_robot.ops.negative_ic_trend_accumulation_preregistration import (
    ROUND105_SOURCE_AUDIT,
    default_negative_ic_trend_accumulation_candidate_specs,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "negative_ic_trend_accumulation_prescreen"


def build_negative_ic_trend_accumulation_prescreen(
    *,
    bars_roots: Iterable[str | Path],
    candidate_specs: Sequence[Any] | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = DEFAULT_CAPACITY_FILTERS["min_signal_date_amount"],
) -> dict[str, Any]:
    specs = list(candidate_specs or default_negative_ic_trend_accumulation_candidate_specs())
    bars = load_capacity_safe_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    factor_frame = compute_negative_ic_trend_accumulation_factors(
        bars,
        candidate_specs=specs,
        min_signal_date_amount=min_signal_date_amount,
    )
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=horizons,
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_capacity_safe_price_volume_prescreen(
        factor_frame,
        labels,
        expected_candidate_count=len(specs),
        candidate_specs=specs,
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
    )
    result["stage"] = STAGE
    result["data_window"] = _data_window(bars, factor_frame, labels)
    result["negative_ic_context"] = {
        "source_audit": ROUND105_SOURCE_AUDIT,
        "source_round": "round105_capacity_safe_trend_accumulation_prescreen",
        "source_evidence_status": "hypothesis_evidence_not_promotion_evidence",
        "policy": "Round107 can create prescreen research leads only; no inverse promotion is allowed.",
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
        "adv20_amount_filter_enabled": True,
        "extreme_daily_return_guard_abs_max": 0.50,
        "drawdown_tolerance_is_not_capacity_waiver": True,
        "portfolio_backtest_allowed_before_prescreen_lead": False,
    }
    result["promotion_policy"] = {
        "promotion_allowed": False,
        "portfolio_backtest_allowed_before_prescreen": False,
        "requires_next_gate": "candidate_correlation_dedup_before_portfolio_grid",
        "next_allowed_action": "candidate_correlation_dedup_if_research_leads_survive",
        "reason": (
            "Round107 is a long-cycle statistical prescreen for pre-registered inverse trend/amount hypotheses. "
            "It does not prove tradable profitability."
        ),
    }
    result["candidate_specs"] = [_spec_payload(spec) for spec in specs]
    result["live_boundary_allowed"] = False
    result["safety"] = SAFETY
    result["markdown"] = render_negative_ic_trend_accumulation_prescreen_markdown(result)
    return result


def compute_negative_ic_trend_accumulation_factors(
    bars: pd.DataFrame,
    *,
    candidate_specs: Sequence[Any] | None = None,
    min_signal_date_amount: float = DEFAULT_CAPACITY_FILTERS["min_signal_date_amount"],
) -> pd.DataFrame:
    specs = list(candidate_specs or default_negative_ic_trend_accumulation_candidate_specs())
    features = _feature_frame(bars)
    if features.empty:
        return pd.DataFrame(
            columns=["date", "asset_id", "market", "factor_name", "factor_value", "amount", "adv20_amount"]
        )
    features = _add_cross_sectional_features(features)
    candidate_values = {
        "anti_volume_weighted_momentum_quality_20": (
            -0.50 * features["z_volume_weighted_return_20"]
            - 0.30 * features["z_return_efficiency_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "anti_money_pressure_efficiency_20": (
            -0.55 * features["z_money_pressure_20"]
            - 0.25 * features["z_return_efficiency_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "anti_accumulation_distribution_pressure_20": (
            -0.50 * features["z_accumulation_distribution_20"]
            - 0.30 * features["z_momentum_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "anti_turnover_expansion_momentum_10_40": (
            -0.45 * features["z_momentum_20"]
            - 0.35 * features["z_amount_expansion_10_40"]
            + 0.20 * features["z_log_adv20"]
        ),
        "anti_amount_accumulation_breakout_20_60": (
            -0.45 * features["z_price_breakout_20"]
            - 0.35 * features["z_amount_trend_20_60"]
            + 0.20 * features["z_log_adv20"]
        ),
        "anti_obv_late_accumulation_20": (
            -0.50 * features["z_obv_slope_20"]
            - 0.30 * features["z_momentum_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "overheat_avoidance_high_volume_breakout_20": (
            -0.45 * features["z_close_to_20d_high"]
            - 0.35 * features["z_amount_zscore_20"]
            + 0.20 * features["z_return_efficiency_20"]
        ),
        "overheat_avoidance_relative_strength_60": (
            -0.55 * features["z_momentum_60"]
            - 0.25 * features["z_amount_percentile_60"]
            + 0.20 * features["z_log_adv20"]
        ),
        "amount_exhaustion_pullback_20_60": (
            -0.40 * features["z_amount_trend_20_60"]
            - 0.35 * features["z_price_breakout_20"]
            + 0.25 * features["z_log_adv20"]
        ),
        "overheat_avoidance_composite_20_60": (
            -0.25 * features["z_money_pressure_20"]
            - 0.25 * features["z_accumulation_distribution_20"]
            - 0.25 * features["z_momentum_60"]
            - 0.15 * features["z_amount_trend_20_60"]
            + 0.10 * features["z_log_adv20"]
        ),
    }
    allowed_names = {spec.factor_name for spec in specs}
    rows: list[pd.DataFrame] = []
    base_columns = ["date", "asset_id", "market", "amount", "adv20_amount"]
    capacity_mask = (
        (features["amount"] >= min_signal_date_amount)
        & (features["adv20_amount"] >= min_signal_date_amount)
        & (features["return_1d"].abs() <= 0.50)
    )
    for factor_name, values in candidate_values.items():
        if factor_name not in allowed_names:
            continue
        frame = features.loc[capacity_mask, base_columns].copy()
        frame["factor_name"] = factor_name
        frame["factor_value"] = values.loc[capacity_mask]
        frame = frame.dropna(subset=["factor_value", "amount", "adv20_amount"])
        rows.append(frame)
    if not rows:
        return pd.DataFrame(
            columns=["date", "asset_id", "market", "factor_name", "factor_value", "amount", "adv20_amount"]
        )
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def write_negative_ic_trend_accumulation_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "negative_ic_trend_accumulation_prescreen.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "negative_ic_trend_accumulation_prescreen.md").write_text(
        render_negative_ic_trend_accumulation_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "negative_ic_trend_accumulation_prescreen_results.csv",
        result.get("results", []),
        RESULT_COLUMNS,
    )
    _write_csv(
        output_path / "negative_ic_trend_accumulation_prescreen_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )


def render_negative_ic_trend_accumulation_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    context = result.get("negative_ic_context", {})
    capacity = result.get("capacity_policy", {})
    lines = [
        "# Negative-IC Trend Accumulation Prescreen",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Aligned rows: {summary.get('aligned_rows', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- FDR-significant tests: {summary.get('multiple_testing_lead_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Final holdout included: {result.get('holdout_policy', {}).get('final_holdout_included', False)}",
        f"- Source audit: {context.get('source_audit', ROUND105_SOURCE_AUDIT)}",
        f"- Minimum signal-date amount: {capacity.get('min_signal_date_amount', '')}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Top Results",
        "",
        "| Factor | Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Mono | Turnover | FDR | Lead |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("results", [])[:20]:
        lines.append(
            "| {factor_name} | {horizon} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {spread:.4f} | {mono:.3f} | {turnover:.1%} | {fdr} | {lead} |".format(
                factor_name=row["factor_name"],
                horizon=row["horizon"],
                ic=row["mean_spearman_ic"],
                icir=row["icir"],
                t=row["ic_t_stat"],
                pos=row["ic_positive_rate"],
                spread=row["quantile_spread"],
                mono=row["quantile_monotonicity"],
                turnover=row["avg_top_quantile_turnover"],
                fdr="yes" if row["fdr_significant"] else "no",
                lead="yes" if row["research_lead"] else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This stage can create research leads only; it cannot promote a factor to paper-ready or live use.",
            "- A drawdown tolerance near 30 percent is not a capacity, cost, extreme-trade, or lookahead waiver.",
            "- Any surviving lead must next pass correlation de-duplication before portfolio grids.",
            "- If no lead survives, this family should rotate rather than receive same-family parameter tuning.",
        ]
    )
    return "\n".join(lines) + "\n"
