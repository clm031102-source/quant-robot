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
    summarize_capacity_safe_price_volume_prescreen,
)
from quant_robot.ops.profitability_event_revision_matrix_label_smoke import (
    FORMULA_COLUMNS,
    _align_factor_values_to_labels,
    _split_candidates,
    compute_profitability_event_revision_factor_frame,
)
from quant_robot.ops.profitability_event_revision_preregistration import (
    SAFETY,
    STATIC_ROUND96_NAMES,
)
from quant_robot.ops.profitability_quality_factor_matrix_smoke import _calculate_candidate_values
from quant_robot.ops.profitability_quality_preregistration import _load_fina_indicator_inputs, _sanitize
from quant_robot.research.labels import make_forward_returns
from quant_robot.storage.factor_inputs import load_factor_inputs


STAGE = "profitability_event_revision_controlled_ic_neutral_prescreen"
NEXT_DIRECTION_WITH_LEADS = "round154_pit_profitability_event_revision_reference_dedup_and_walk_forward_preflight"
NEXT_DIRECTION_WITHOUT_LEADS = "round154_rotate_or_repair_profitability_event_revision_after_neutral_prescreen_failure"
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
    "industry_neutral_observations",
    "mean_industry_neutral_rank_ic",
    "industry_neutral_rank_ic_t_stat",
    "industry_neutral_retention_ratio",
    "size_neutral_observations",
    "mean_size_neutral_rank_ic",
    "size_neutral_rank_ic_t_stat",
    "size_neutral_retention_ratio",
    "liquidity_neutral_observations",
    "mean_liquidity_neutral_rank_ic",
    "liquidity_neutral_rank_ic_t_stat",
    "liquidity_neutral_retention_ratio",
    "reference_max_abs_correlation",
    "reference_mean_abs_correlation",
    "reference_top_match",
    "research_lead",
    "promotion_allowed",
    "blockers",
]
NEUTRAL_OBSERVATION_COLUMNS = [
    "factor_name",
    "horizon",
    "date",
    "industry_neutral_rank_ic",
    "size_neutral_rank_ic",
    "liquidity_neutral_rank_ic",
    "cross_section",
    "industry_count",
    "size_exposure",
    "liquidity_exposure",
]
REFERENCE_CORRELATION_COLUMNS = [
    "factor_name",
    "reference_factor_name",
    "correlation_observations",
    "mean_correlation",
    "mean_abs_correlation",
    "max_abs_correlation",
    "median_cross_section",
    "dedup_blocker",
]


def build_profitability_event_revision_controlled_ic_neutral_prescreen(
    *,
    financial_root: str | Path,
    bars_roots: Iterable[str | Path],
    preregistration_json: str | Path,
    candidate_plan_gate_json: str | Path | None = None,
    stock_basic_path: str | Path | None = None,
    daily_basic_roots: Iterable[str | Path] | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 8,
    min_neutral_rank_ic: float = 0.01,
    min_neutral_ic_t_stat: float = 2.0,
    min_neutral_retention: float = 0.35,
    reference_high_corr_threshold: float = 0.90,
    reference_mean_abs_corr_threshold: float = 0.70,
    alpha: float = 0.05,
) -> dict[str, Any]:
    financial = _load_fina_indicator_inputs(Path(financial_root))
    preregistration = _load_json(preregistration_json)
    gate_packet = _load_json(candidate_plan_gate_json)
    active_candidates, frozen_candidates = _split_candidates(preregistration, gate_packet)
    active_candidates = [candidate for candidate in active_candidates if candidate.get("factor_name") in FORMULA_COLUMNS]
    assets = sorted(financial["asset_id"].dropna().astype(str).unique()) if "asset_id" in financial.columns else []
    bars = load_capacity_safe_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    if assets:
        bars = bars[bars["asset_id"].astype(str).isin(set(assets))].reset_index(drop=True)
    factor_frame = compute_profitability_event_revision_factor_frame(financial, active_candidates, bars)
    factor_frame = _filter_date_window(
        _attach_market_context(
            factor_frame,
            bars,
            daily_basic=_load_daily_basic_context(daily_basic_roots),
        ),
        start_date=analysis_start_date,
        end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=tuple(horizons),
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    stock_basic = _load_stock_basic(stock_basic_path)
    reference_frame = compute_static_profitability_reference_frame(financial, bars)
    result = summarize_profitability_event_revision_controlled_ic_neutral_prescreen(
        factor_frame,
        labels,
        stock_basic,
        reference_factor_frame=reference_frame,
        expected_candidate_count=len(active_candidates),
        candidate_specs=active_candidates,
        frozen_candidate_count=len(frozen_candidates),
        horizons=tuple(horizons),
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_neutral_rank_ic=min_neutral_rank_ic,
        min_neutral_ic_t_stat=min_neutral_ic_t_stat,
        min_neutral_retention=min_neutral_retention,
        reference_high_corr_threshold=reference_high_corr_threshold,
        reference_mean_abs_corr_threshold=reference_mean_abs_corr_threshold,
        alpha=alpha,
    )
    result.update(
        {
            "financial_root": str(Path(financial_root)),
            "bars_roots": [str(Path(root)) for root in bars_roots],
            "preregistration_json": str(Path(preregistration_json)),
            "candidate_plan_gate_json": str(Path(candidate_plan_gate_json)) if candidate_plan_gate_json else None,
            "stock_basic_path": str(Path(stock_basic_path)) if stock_basic_path else None,
            "daily_basic_roots": [str(Path(root)) for root in daily_basic_roots] if daily_basic_roots else [],
            "data_window": _data_window(bars, factor_frame, labels, reference_frame),
            "holdout_policy": {
                "final_holdout_included": include_final_holdout,
                "analysis_start_date": analysis_start_date,
                "analysis_end_date": analysis_end_date,
                "final_holdout_start": "2026-01-01",
                "final_holdout_use": "blocked_until_oos_clearance_after_walk_forward",
            },
            "pit_policy": {
                "signal_date_rule": "first_trade_date_strictly_after_ann_date",
                "same_day_announcement_trading_allowed": False,
                "execution_lag": int(execution_lag),
            },
            "active_candidates": [_candidate_brief(candidate) for candidate in active_candidates],
            "frozen_candidates": [_candidate_brief(candidate) for candidate in frozen_candidates],
            "live_boundary_allowed": False,
            "safety": SAFETY,
        }
    )
    result["markdown"] = render_profitability_event_revision_controlled_ic_neutral_prescreen_markdown(result)
    return result


def summarize_profitability_event_revision_controlled_ic_neutral_prescreen(
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    stock_basic: pd.DataFrame,
    *,
    reference_factor_frame: pd.DataFrame | None = None,
    expected_candidate_count: int | None = None,
    candidate_specs: Sequence[dict[str, Any]] | None = None,
    frozen_candidate_count: int = 0,
    horizons: tuple[int, ...] | None = None,
    min_cross_section: int = 30,
    min_ic_observations: int = 8,
    min_neutral_rank_ic: float = 0.01,
    min_neutral_ic_t_stat: float = 2.0,
    min_neutral_retention: float = 0.35,
    reference_high_corr_threshold: float = 0.90,
    reference_mean_abs_corr_threshold: float = 0.70,
    alpha: float = 0.05,
    min_abs_ic: float = 0.02,
    min_abs_icir: float = 0.30,
    min_positive_ic_rate: float = 0.55,
) -> dict[str, Any]:
    factors = _normalise_factor_frame(factor_frame)
    labels = labels.copy()
    if not labels.empty:
        labels["date"] = pd.to_datetime(labels["date"], errors="coerce")
    requested_horizons = tuple(horizons or tuple(sorted(labels["horizon"].unique()))) if not labels.empty else tuple()
    base = summarize_capacity_safe_price_volume_prescreen(
        factors,
        labels,
        expected_candidate_count=expected_candidate_count,
        candidate_specs=candidate_specs or [],
        horizons=requested_horizons,
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
        horizons=requested_horizons,
        min_cross_section=min_cross_section,
        min_industries=2,
        min_assets_per_industry=2,
    )
    neutral_by_key = {
        (row["factor_name"], int(row["horizon"])): row
        for row in neutral_rows
    }
    reference_rows = _reference_correlation_rows(
        factors,
        reference_factor_frame if reference_factor_frame is not None else pd.DataFrame(),
        min_cross_section=min_cross_section,
        high_corr_threshold=reference_high_corr_threshold,
        mean_abs_corr_threshold=reference_mean_abs_corr_threshold,
    )
    reference_by_factor = _reference_summary_by_factor(reference_rows)
    for row in base.get("results", []):
        neutral = neutral_by_key.get((row["factor_name"], int(row["horizon"])), _empty_neutral_summary())
        row.update(neutral)
        reference = reference_by_factor.get(row["factor_name"], _empty_reference_summary())
        row.update(reference)
        blockers = [
            blocker
            for blocker in row.get("blockers", [])
            if blocker not in {"top_quantile_turnover_too_high"}
        ]
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
        liquidity_pass = _neutral_gate_pass(
            row,
            prefix="liquidity_neutral",
            min_neutral_rank_ic=min_neutral_rank_ic,
            min_neutral_ic_t_stat=min_neutral_ic_t_stat,
            min_neutral_retention=min_neutral_retention,
        )
        if not industry_pass:
            blockers.append("industry_neutral_ic_below_gate")
        if not size_pass:
            blockers.append("size_neutral_ic_below_gate")
        if not liquidity_pass:
            blockers.append("liquidity_neutral_ic_below_gate")
        if row.get("reference_dedup_blocker"):
            blockers.append("high_correlation_with_round96_static_profitability")
        blockers.append("promotion_requires_walk_forward_cost_capacity_regime_final_holdout")
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
            and liquidity_pass
            and not row.get("reference_dedup_blocker")
        )
        row["promotion_allowed"] = False
    base["results"] = sorted(
        base.get("results", []),
        key=lambda item: (not item.get("research_lead", False), -abs(float(item.get("mean_spearman_ic", 0.0)))),
    )
    summary = base["summary"]
    summary["frozen_candidate_count"] = int(frozen_candidate_count)
    summary["research_lead_count"] = sum(1 for row in base["results"] if row["research_lead"])
    summary["neutral_gate_pass_count"] = sum(
        1
        for row in base["results"]
        if "industry_neutral_ic_below_gate" not in row["blockers"]
        and "size_neutral_ic_below_gate" not in row["blockers"]
        and "liquidity_neutral_ic_below_gate" not in row["blockers"]
    )
    summary["reference_dedup_pass_count"] = sum(
        1 for row in base["results"] if "high_correlation_with_round96_static_profitability" not in row["blockers"]
    )
    summary["promotion_allowed_candidates"] = 0
    summary["industry_neutral_observation_rows"] = sum(
        int(row.get("industry_neutral_observations", 0)) for row in base["results"]
    )
    summary["size_neutral_observation_rows"] = sum(int(row.get("size_neutral_observations", 0)) for row in base["results"])
    summary["liquidity_neutral_observation_rows"] = sum(
        int(row.get("liquidity_neutral_observations", 0)) for row in base["results"]
    )
    summary["next_direction"] = NEXT_DIRECTION_WITH_LEADS if summary["research_lead_count"] else NEXT_DIRECTION_WITHOUT_LEADS
    base.update(
        {
            "stage": STAGE,
            "generated_at": date.today().isoformat(),
            "neutral_policy": {
                "min_neutral_rank_ic": float(min_neutral_rank_ic),
                "min_neutral_ic_t_stat": float(min_neutral_ic_t_stat),
                "min_neutral_retention": float(min_neutral_retention),
                "industry_neutral_method": "within_industry_rank_ic_by_signal_date",
                "size_neutral_method": "rank_residual_ic_against_log_circ_mv_or_log_total_mv_or_log_adv20",
                "liquidity_neutral_method": "rank_residual_ic_against_turnover_rate_f_or_turnover_rate_or_volume_ratio",
            },
            "reference_dedup_policy": {
                "reference_family": "round96_static_profitability_quality",
                "reference_names": sorted(STATIC_ROUND96_NAMES),
                "high_corr_threshold": float(reference_high_corr_threshold),
                "mean_abs_corr_threshold": float(reference_mean_abs_corr_threshold),
            },
            "multiple_testing_policy": {
                "alpha": float(alpha),
                "method": "Bonferroni and Benjamini-Hochberg FDR across profitability event/revision factor x horizon tests",
            },
            "promotion_policy": {
                "promotion_allowed": False,
                "portfolio_backtest_allowed_before_prescreen": False,
                "requires_next_gate": "walk_forward_cost_capacity_regime_preflight_after_neutral_prescreen_lead",
                "reason": "This is a controlled IC/neutral prescreen, not a portfolio or paper-ready validation.",
            },
            "neutral_observations": neutral_observations,
            "reference_correlations": reference_rows,
            "live_boundary_allowed": False,
            "safety": SAFETY,
        }
    )
    base["markdown"] = render_profitability_event_revision_controlled_ic_neutral_prescreen_markdown(base)
    return base


def compute_static_profitability_reference_frame(financial: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    if financial.empty or bars.empty:
        return _empty_reference_frame()
    frame = financial.copy()
    for column in ["date", "ann_date", "end_date"]:
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    for column in ["asset_id", "market"]:
        if column not in frame:
            frame[column] = "CN" if column == "market" else ""
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    frame = frame.sort_values(["asset_id", "end_date", "ann_date"]).reset_index(drop=True)
    trade_dates = {
        asset_id: pd.DatetimeIndex(group["date"].sort_values().dropna().unique())
        for asset_id, group in _bar_prices(bars).groupby("asset_id")
    }
    signal_dates = []
    for row in frame.itertuples(index=False):
        dates = trade_dates.get(str(getattr(row, "asset_id")))
        ann_date = pd.Timestamp(getattr(row, "ann_date")) if hasattr(row, "ann_date") else pd.NaT
        if dates is None or pd.isna(ann_date):
            signal_dates.append(pd.NaT)
            continue
        position = dates.searchsorted(ann_date, side="right")
        signal_dates.append(dates[position] if position < len(dates) else pd.NaT)
    frame["date"] = signal_dates
    frame = frame.dropna(subset=["date", "asset_id", "ann_date"])
    pieces = []
    for name in sorted(STATIC_ROUND96_NAMES):
        values = _calculate_candidate_values(frame, name)
        piece = pd.DataFrame(
            {
                "date": frame["date"],
                "asset_id": frame["asset_id"],
                "market": frame["market"],
                "reference_factor_name": name,
                "reference_factor_value": pd.to_numeric(values, errors="coerce"),
            }
        ).dropna(subset=["date", "asset_id", "reference_factor_value"])
        pieces.append(piece)
    if not pieces:
        return _empty_reference_frame()
    return (
        pd.concat(pieces, ignore_index=True)
        .sort_values(["reference_factor_name", "date", "asset_id"])
        .reset_index(drop=True)
    )


def write_profitability_event_revision_controlled_ic_neutral_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "profitability_event_revision_controlled_ic_neutral_prescreen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "profitability_event_revision_controlled_ic_neutral_prescreen.md").write_text(
        render_profitability_event_revision_controlled_ic_neutral_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "profitability_event_revision_controlled_ic_results.csv",
        result.get("results", []) or [],
        RESULT_COLUMNS,
    )
    _write_csv(
        output_path / "profitability_event_revision_controlled_ic_observations.csv",
        result.get("ic_observations", []) or [],
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )
    _write_csv(
        output_path / "profitability_event_revision_neutral_observations.csv",
        result.get("neutral_observations", []) or [],
        NEUTRAL_OBSERVATION_COLUMNS,
    )
    _write_csv(
        output_path / "profitability_event_revision_reference_correlations.csv",
        result.get("reference_correlations", []) or [],
        REFERENCE_CORRELATION_COLUMNS,
    )


def render_profitability_event_revision_controlled_ic_neutral_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    neutral = result.get("neutral_policy", {})
    lines = [
        "# PIT Profitability Event Revision Controlled IC Neutral Prescreen Round153",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Frozen candidates: {summary.get('frozen_candidate_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Aligned rows: {summary.get('aligned_rows', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- FDR-significant tests: {summary.get('multiple_testing_lead_count', 0)}",
        f"- Neutral-gate pass tests: {summary.get('neutral_gate_pass_count', 0)}",
        f"- Reference de-dup pass tests: {summary.get('reference_dedup_pass_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Next direction: {summary.get('next_direction', NEXT_DIRECTION_WITHOUT_LEADS)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Neutral And De-Dup Policy",
        "",
        f"- Min neutral RankIC: {float(neutral.get('min_neutral_rank_ic', 0.0)):.4f}",
        f"- Min neutral t-stat: {float(neutral.get('min_neutral_ic_t_stat', 0.0)):.2f}",
        f"- Min neutral retention: {float(neutral.get('min_neutral_retention', 0.0)):.2f}",
        "- De-dup reference: Round96 static profitability-quality factor family.",
        "",
        "## Top Results",
        "",
        "| Factor | H | IC | ICIR | t | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | LiqNeuIC | RefAbs | Lead |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in result.get("results", [])[:25]:
        lines.append(
            "| {factor_name} | {horizon} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {spread:.4f} | {ind:.4f} | {size:.4f} | {liq:.4f} | {ref:.3f} | {lead} |".format(
                factor_name=row.get("factor_name", ""),
                horizon=int(row.get("horizon", 0)),
                ic=_number(row.get("mean_spearman_ic")),
                icir=_number(row.get("icir")),
                t=_number(row.get("ic_t_stat")),
                pos=_number(row.get("ic_positive_rate")),
                spread=_number(row.get("quantile_spread")),
                ind=_number(row.get("mean_industry_neutral_rank_ic")),
                size=_number(row.get("mean_size_neutral_rank_ic")),
                liq=_number(row.get("mean_liquidity_neutral_rank_ic")),
                ref=_number(row.get("reference_max_abs_correlation")),
                lead="yes" if row.get("research_lead") else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This stage computes IC, FDR, industry-neutral IC, size-neutral IC, liquidity-neutral IC, and Round96 static-factor de-duplication.",
            "- It does not compute Sharpe, total return, annual return, win rate, drawdown, or any portfolio claim.",
            "- Any lead still needs walk-forward, cost/capacity, regime, and final-holdout checks before a paper-ready claim.",
        ]
    )
    return "\n".join(lines) + "\n"


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
    labels_by_horizon = {
        int(horizon): group.drop(columns=["horizon"]).copy()
        for horizon, group in labels[labels["horizon"].isin(horizons)].groupby("horizon", sort=False)
    }
    rows: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    for factor_name, factor_group in factor_frame.groupby("factor_name", sort=False):
        for horizon in horizons:
            label_group = labels_by_horizon.get(int(horizon), pd.DataFrame())
            merged = factor_group.merge(label_group, on=["date", "asset_id", "market"], how="inner")
            merged = merged.merge(metadata, on="asset_id", how="left")
            ind_values: list[float] = []
            size_values: list[float] = []
            liquidity_values: list[float] = []
            for signal_date, date_frame in merged.groupby("date", sort=True):
                valid = date_frame.dropna(subset=["factor_value", "forward_return"]).copy()
                if len(valid) < min_cross_section:
                    continue
                size_exposure = _best_exposure(valid, ("log_circ_mv", "log_total_mv", "log_adv20_amount", "log_adv20"))
                liquidity_exposure = _best_exposure(valid, ("turnover_rate_f", "turnover_rate", "volume_ratio", "log_amount"))
                industry_ic = _industry_neutral_rank_ic(
                    valid,
                    min_industries=min_industries,
                    min_assets_per_industry=min_assets_per_industry,
                )
                size_ic = _residual_neutral_rank_ic(valid, size_exposure)
                liquidity_ic = _residual_neutral_rank_ic(valid, liquidity_exposure)
                if _is_finite(industry_ic):
                    ind_values.append(float(industry_ic))
                if _is_finite(size_ic):
                    size_values.append(float(size_ic))
                if _is_finite(liquidity_ic):
                    liquidity_values.append(float(liquidity_ic))
                observations.append(
                    {
                        "factor_name": str(factor_name),
                        "horizon": int(horizon),
                        "date": pd.Timestamp(signal_date).date().isoformat(),
                        "industry_neutral_rank_ic": float(industry_ic) if _is_finite(industry_ic) else None,
                        "size_neutral_rank_ic": float(size_ic) if _is_finite(size_ic) else None,
                        "liquidity_neutral_rank_ic": float(liquidity_ic) if _is_finite(liquidity_ic) else None,
                        "cross_section": int(len(valid)),
                        "industry_count": int(valid["industry"].nunique()) if "industry" in valid else 0,
                        "size_exposure": size_exposure,
                        "liquidity_exposure": liquidity_exposure,
                    }
                )
            rows.append(
                {
                    "factor_name": str(factor_name),
                    "horizon": int(horizon),
                    **_neutral_summary("industry_neutral", ind_values),
                    **_neutral_summary("size_neutral", size_values),
                    **_neutral_summary("liquidity_neutral", liquidity_values),
                }
            )
    return rows, observations


def _reference_correlation_rows(
    factor_frame: pd.DataFrame,
    reference_factor_frame: pd.DataFrame,
    *,
    min_cross_section: int,
    high_corr_threshold: float,
    mean_abs_corr_threshold: float,
) -> list[dict[str, Any]]:
    if factor_frame.empty or reference_factor_frame.empty:
        return []
    factors = factor_frame[["date", "asset_id", "market", "factor_name", "factor_value"]].copy()
    refs = reference_factor_frame.copy()
    rows: list[dict[str, Any]] = []
    for factor_name, factor_group in factors.groupby("factor_name", sort=False):
        for reference_name, reference_group in refs.groupby("reference_factor_name", sort=False):
            merged = factor_group.merge(reference_group, on=["date", "asset_id", "market"], how="inner")
            correlations: list[float] = []
            cross_sections: list[int] = []
            for _, date_frame in merged.groupby("date", sort=True):
                valid = date_frame.dropna(subset=["factor_value", "reference_factor_value"])
                if len(valid) < min_cross_section:
                    continue
                corr = _spearman(valid["factor_value"], valid["reference_factor_value"])
                if _is_finite(corr):
                    correlations.append(float(corr))
                    cross_sections.append(int(len(valid)))
            series = pd.Series(correlations, dtype=float)
            mean_corr = float(series.mean()) if not series.empty else 0.0
            mean_abs = float(series.abs().mean()) if not series.empty else 0.0
            max_abs = float(series.abs().max()) if not series.empty else 0.0
            rows.append(
                {
                    "factor_name": str(factor_name),
                    "reference_factor_name": str(reference_name),
                    "correlation_observations": int(len(series)),
                    "mean_correlation": mean_corr,
                    "mean_abs_correlation": mean_abs,
                    "max_abs_correlation": max_abs,
                    "median_cross_section": float(pd.Series(cross_sections).median()) if cross_sections else 0.0,
                    "dedup_blocker": bool(max_abs >= high_corr_threshold or mean_abs >= mean_abs_corr_threshold),
                }
            )
    return rows


def _reference_summary_by_factor(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["factor_name"], []).append(row)
    output = {}
    for factor_name, factor_rows in grouped.items():
        top = max(factor_rows, key=lambda row: row.get("max_abs_correlation", 0.0))
        output[factor_name] = {
            "reference_max_abs_correlation": float(top.get("max_abs_correlation", 0.0)),
            "reference_mean_abs_correlation": float(top.get("mean_abs_correlation", 0.0)),
            "reference_top_match": str(top.get("reference_factor_name", "")),
            "reference_dedup_blocker": bool(any(row.get("dedup_blocker") for row in factor_rows)),
        }
    return output


def _attach_market_context(
    factor_frame: pd.DataFrame,
    bars: pd.DataFrame,
    *,
    daily_basic: pd.DataFrame,
) -> pd.DataFrame:
    if factor_frame.empty:
        return _empty_factor_frame()
    output = factor_frame.copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].fillna("CN").astype(str).str.upper()
    context = _bar_context(bars)
    output = output.merge(context, on=["date", "asset_id", "market"], how="left", validate="many_to_one")
    if not daily_basic.empty:
        output = output.merge(daily_basic, on=["date", "asset_id", "market"], how="left", validate="many_to_one")
    for column in ["amount", "adv20_amount", "log_adv20", "log_amount", "total_mv", "circ_mv", "turnover_rate", "turnover_rate_f", "volume_ratio"]:
        if column not in output:
            output[column] = pd.NA
    output["log_total_mv"] = _safe_log(output["total_mv"]) if "total_mv" in output else pd.NA
    output["log_circ_mv"] = _safe_log(output["circ_mv"]) if "circ_mv" in output else pd.NA
    return output


def _bar_context(bars: pd.DataFrame) -> pd.DataFrame:
    if bars.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "amount", "adv20_amount", "log_adv20", "log_amount"])
    frame = bars[["date", "asset_id", "market", "amount"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    frame = frame.dropna(subset=["date", "asset_id", "market"])
    frame = frame.sort_values(["asset_id", "date"]).drop_duplicates(["date", "asset_id", "market"], keep="last")
    frame["adv20_amount"] = frame.groupby("asset_id")["amount"].transform(lambda item: item.rolling(20, min_periods=5).mean())
    frame["log_adv20"] = _safe_log(frame["adv20_amount"])
    frame["log_amount"] = _safe_log(frame["amount"])
    return frame


def _load_daily_basic_context(roots: Iterable[str | Path] | None) -> pd.DataFrame:
    if not roots:
        return pd.DataFrame()
    frames = []
    for root in roots:
        try:
            frames.append(load_factor_inputs(root, "CN"))
        except FileNotFoundError:
            continue
    if not frames:
        return pd.DataFrame()
    frame = pd.concat(frames, ignore_index=True)
    required = ["date", "asset_id", "market"]
    for column in required:
        if column not in frame:
            return pd.DataFrame()
    keep = [
        column
        for column in [
            "date",
            "asset_id",
            "market",
            "turnover_rate",
            "turnover_rate_f",
            "volume_ratio",
            "total_mv",
            "circ_mv",
        ]
        if column in frame.columns
    ]
    frame = frame[keep].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    for column in keep:
        if column not in {"date", "asset_id", "market"}:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=required).drop_duplicates(["date", "asset_id", "market"], keep="last").reset_index(drop=True)


def _load_stock_basic(path: str | Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame(columns=["asset_id", "industry"])
    root = Path(path)
    files = [root] if root.is_file() else sorted([*root.rglob("*.parquet"), *root.rglob("*.csv")])
    frames = []
    for file in files:
        try:
            frame = pd.read_parquet(file) if file.suffix.lower() == ".parquet" else pd.read_csv(file)
        except Exception:
            continue
        if {"asset_id", "industry"}.issubset(frame.columns):
            frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=["asset_id", "industry"])
    return pd.concat(frames, ignore_index=True)


def _normalise_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return _empty_factor_frame()
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].fillna("CN").astype(str).str.upper()
    output["factor_name"] = output["factor_name"].astype(str)
    output["factor_value"] = pd.to_numeric(output["factor_value"], errors="coerce")
    for column in [
        "amount",
        "adv20_amount",
        "log_adv20",
        "log_amount",
        "turnover_rate",
        "turnover_rate_f",
        "volume_ratio",
        "total_mv",
        "circ_mv",
        "log_total_mv",
        "log_circ_mv",
    ]:
        if column not in output:
            output[column] = pd.NA
        output[column] = pd.to_numeric(output[column], errors="coerce")
    return output.dropna(subset=["date", "asset_id", "market", "factor_name", "factor_value"]).reset_index(drop=True)


def _normalise_stock_basic(stock_basic: pd.DataFrame) -> pd.DataFrame:
    frame = stock_basic.copy()
    for column in ["asset_id", "industry"]:
        if column not in frame:
            frame[column] = ""
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["industry"] = frame["industry"].fillna("").astype(str)
    return frame.drop_duplicates("asset_id", keep="last").reset_index(drop=True)


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


def _residual_neutral_rank_ic(frame: pd.DataFrame, exposure_column: str | None) -> float:
    working = frame.dropna(subset=["factor_value", "forward_return"]).copy()
    if len(working) < 3:
        return float("nan")
    if not exposure_column or exposure_column not in working:
        return _spearman(working["factor_value"], working["forward_return"])
    exposure = pd.to_numeric(working[exposure_column], errors="coerce")
    if exposure.notna().sum() < 3 or exposure.nunique(dropna=True) < 2:
        return _spearman(working["factor_value"], working["forward_return"])
    factor_resid = _simple_residual(working["factor_value"].rank(method="average"), exposure)
    return_resid = _simple_residual(working["forward_return"].rank(method="average"), exposure)
    return _spearman(factor_resid, return_resid)


def _best_exposure(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    best_column = None
    best_count = -1
    for column in candidates:
        if column not in frame:
            continue
        values = pd.to_numeric(frame[column], errors="coerce")
        count = int(values.notna().sum())
        if count > best_count and values.nunique(dropna=True) >= 2:
            best_column = column
            best_count = count
    return best_column


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


def _empty_neutral_summary() -> dict[str, Any]:
    return {
        **_neutral_summary("industry_neutral", []),
        **_neutral_summary("size_neutral", []),
        **_neutral_summary("liquidity_neutral", []),
        "industry_neutral_retention_ratio": 0.0,
        "size_neutral_retention_ratio": 0.0,
        "liquidity_neutral_retention_ratio": 0.0,
    }


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


def _empty_reference_summary() -> dict[str, Any]:
    return {
        "reference_max_abs_correlation": 0.0,
        "reference_mean_abs_correlation": 0.0,
        "reference_top_match": "",
        "reference_dedup_blocker": False,
    }


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
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    end = output["date"].max() if include_final_holdout else pd.Timestamp(end_date)
    return output[(output["date"] >= pd.Timestamp(start_date)) & (output["date"] <= end)].reset_index(drop=True)


def _bar_prices(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        return pd.DataFrame(columns=required)
    frame = bars[required].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    return frame.dropna(subset=required).drop_duplicates(["asset_id", "date"], keep="last")


def _safe_log(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.where(values > 0).map(lambda value: math.log(value) if _is_finite(value) and value > 0 else pd.NA)


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


def _data_window(
    bars: pd.DataFrame,
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    reference_frame: pd.DataFrame,
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
        "reference_factor_rows": int(len(reference_frame)),
    }


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "ann_date",
            "end_date",
            "asset_id",
            "market",
            "factor_name",
            "factor_value",
            "amount",
            "adv20_amount",
            "log_adv20",
            "log_amount",
            "turnover_rate",
            "turnover_rate_f",
            "volume_ratio",
            "total_mv",
            "circ_mv",
            "log_total_mv",
            "log_circ_mv",
        ]
    )


def _empty_reference_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "asset_id", "market", "reference_factor_name", "reference_factor_value"])


def _load_json(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _candidate_brief(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "factor_name": str(candidate.get("factor_name", "")),
        "family": str(candidate.get("family", "")),
        "registration_status": str(candidate.get("registration_status", "")),
        "portfolio_backtest_allowed": bool(candidate.get("portfolio_backtest_allowed")),
        "promotion_allowed": bool(candidate.get("promotion_allowed")),
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
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


def _dedupe(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value not in output:
            output.append(value)
    return output
