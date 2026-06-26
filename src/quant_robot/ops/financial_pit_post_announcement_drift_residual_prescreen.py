from __future__ import annotations

import csv
from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
)
from quant_robot.ops.financial_pit_post_announcement_drift_matrix_label_smoke import (
    FORMULA_COLUMNS,
    compute_financial_pit_post_announcement_drift_factor_frame,
)
from quant_robot.ops.financial_pit_post_announcement_drift_preregistration import (
    SAFETY,
    _filter_date_window as _filter_financial_date_window,
    _load_bars,
    _load_json,
    _next_trade_dates,
)
from quant_robot.ops.profitability_event_revision_controlled_ic_neutral_prescreen import (
    NEUTRAL_OBSERVATION_COLUMNS,
    REFERENCE_CORRELATION_COLUMNS,
    RESULT_COLUMNS,
    _attach_market_context,
    _candidate_brief,
    _data_window,
    _filter_date_window,
    _load_daily_basic_context,
    _load_stock_basic,
    _split_candidates,
    summarize_profitability_event_revision_controlled_ic_neutral_prescreen,
)
from quant_robot.ops.profitability_event_revision_preregistration import STATIC_ROUND96_NAMES
from quant_robot.ops.profitability_quality_factor_matrix_smoke import _calculate_candidate_values
from quant_robot.ops.profitability_quality_preregistration import _load_fina_indicator_inputs, _sanitize
from quant_robot.research.labels import make_forward_returns


STAGE = "financial_pit_post_announcement_drift_residual_prescreen"
NEXT_DIRECTION_WITH_LEADS = "round223_financial_pit_post_announcement_drift_reference_dedup_walk_forward_preflight"
NEXT_DIRECTION_WITHOUT_LEADS = "round223_rotate_or_repair_financial_pit_post_announcement_drift_after_residual_failure"


def build_financial_pit_post_announcement_drift_residual_prescreen(
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
    financial = _filter_financial_date_window(
        _load_fina_indicator_inputs(Path(financial_root)),
        start_date=analysis_start_date,
        end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        preferred_date_column="signal_date",
    )
    preregistration = _load_json(preregistration_json)
    gate_packet = _load_json(candidate_plan_gate_json)
    active_candidates, frozen_candidates = _split_candidates(preregistration, gate_packet)
    active_candidates = [candidate for candidate in active_candidates if candidate.get("factor_name") in FORMULA_COLUMNS]
    assets = sorted(financial["asset_id"].dropna().astype(str).unique()) if "asset_id" in financial.columns else []
    bars = _filter_financial_date_window(
        _load_bars([Path(root) for root in bars_roots], assets),
        start_date=analysis_start_date,
        end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        preferred_date_column="date",
    )
    raw_factor_frame = compute_financial_pit_post_announcement_drift_factor_frame(financial, active_candidates, bars)
    factor_frame = _filter_date_window(
        _attach_market_context(
            raw_factor_frame,
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
    if not include_final_holdout and not labels.empty:
        labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    stock_basic = _load_stock_basic(stock_basic_path)
    reference_frame = compute_static_profitability_reference_frame_on_reaction_available_date(financial, bars)
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
    research_lead_count = int(result.get("summary", {}).get("research_lead_count", 0))
    result.update(
        {
            "stage": STAGE,
            "generated_at": date.today().isoformat(),
            "financial_root": str(Path(financial_root)),
            "bars_roots": [str(Path(root)) for root in bars_roots],
            "preregistration_json": str(Path(preregistration_json)),
            "candidate_plan_gate_json": str(Path(candidate_plan_gate_json)) if candidate_plan_gate_json else None,
            "stock_basic_path": str(Path(stock_basic_path)) if stock_basic_path else None,
            "daily_basic_roots": [str(Path(root)) for root in daily_basic_roots] if daily_basic_roots else [],
            "data_window": _data_window(bars, factor_frame, labels, reference_frame),
            "holdout_policy": {
                "final_holdout_included": bool(include_final_holdout),
                "analysis_start_date": str(analysis_start_date),
                "analysis_end_date": str(analysis_end_date),
                "final_holdout_start": "2026-01-01",
                "final_holdout_use": "blocked_until_oos_clearance_after_walk_forward",
            },
            "pit_policy": {
                "announcement_signal_rule": "signal_date must be strictly after ann_date",
                "event_reaction_date_rule": "event reaction is measured on signal_date only after announcement availability",
                "factor_date_rule": "factor date equals first trade date strictly after event_reaction_date",
                "same_day_announcement_trading_allowed": False,
                "same_day_event_reaction_trading_allowed": False,
                "execution_lag": int(execution_lag),
            },
            "active_candidates": [_candidate_brief(candidate) for candidate in active_candidates],
            "frozen_candidates": [_candidate_brief(candidate) for candidate in frozen_candidates],
            "live_boundary_allowed": False,
            "safety": SAFETY,
        }
    )
    result["summary"]["next_direction"] = (
        NEXT_DIRECTION_WITH_LEADS if research_lead_count else NEXT_DIRECTION_WITHOUT_LEADS
    )
    result["promotion_policy"] = {
        "promotion_allowed": False,
        "portfolio_backtest_allowed_before_prescreen": False,
        "requires_next_gate": "walk_forward_cost_capacity_regime_preflight_after_residual_prescreen_lead",
        "reason": "This is a residual IC/neutral prescreen, not portfolio or paper-ready validation.",
    }
    result["markdown"] = render_financial_pit_post_announcement_drift_residual_prescreen_markdown(result)
    return result


def compute_static_profitability_reference_frame_on_reaction_available_date(
    financial: pd.DataFrame,
    bars: pd.DataFrame,
) -> pd.DataFrame:
    if financial.empty or bars.empty:
        return _empty_reference_frame()
    frame = financial.copy()
    for column in ["date", "ann_date", "end_date", "available_date", "signal_date"]:
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    if "signal_date" not in frame and "available_date" in frame:
        frame["signal_date"] = frame["available_date"]
    for column in ["asset_id", "market"]:
        if column not in frame:
            frame[column] = "CN" if column == "market" else ""
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    frame["event_reaction_date"] = pd.to_datetime(frame["signal_date"], errors="coerce")
    frame["reaction_available_date"] = _next_trade_dates(frame, bars, "event_reaction_date")
    frame = frame.dropna(subset=["ann_date", "event_reaction_date", "reaction_available_date", "asset_id"])
    frame = frame[
        (frame["event_reaction_date"] > frame["ann_date"])
        & (frame["reaction_available_date"] > frame["event_reaction_date"])
    ].reset_index(drop=True)
    if frame.empty:
        return _empty_reference_frame()
    pieces = []
    for name in sorted(STATIC_ROUND96_NAMES):
        try:
            values = _calculate_candidate_values(frame, name)
        except KeyError:
            continue
        piece = pd.DataFrame(
            {
                "date": frame["reaction_available_date"],
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


def write_financial_pit_post_announcement_drift_residual_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "financial_pit_post_announcement_drift_residual_prescreen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "financial_pit_post_announcement_drift_residual_prescreen.md").write_text(
        render_financial_pit_post_announcement_drift_residual_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "financial_pit_post_announcement_drift_residual_ic_results.csv", result.get("results", []) or [], RESULT_COLUMNS)
    _write_csv(
        output_path / "financial_pit_post_announcement_drift_residual_ic_observations.csv",
        result.get("ic_observations", []) or [],
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )
    _write_csv(
        output_path / "financial_pit_post_announcement_drift_neutral_observations.csv",
        result.get("neutral_observations", []) or [],
        NEUTRAL_OBSERVATION_COLUMNS,
    )
    _write_csv(
        output_path / "financial_pit_post_announcement_drift_reference_correlations.csv",
        result.get("reference_correlations", []) or [],
        REFERENCE_CORRELATION_COLUMNS,
    )


def render_financial_pit_post_announcement_drift_residual_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {}) or {}
    lines = [
        "# Financial PIT Post-Announcement Drift Residual Prescreen",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- Neutral gate passes: {summary.get('neutral_gate_pass_count', 0)}",
        f"- Reference dedup passes: {summary.get('reference_dedup_pass_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Next direction: `{summary.get('next_direction', '')}`",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Results",
        "",
        "| Factor | H | IC | ICIR | t | Pos IC | QSpread | Mono | IndNeuIC | SizeNeuIC | LiqNeuIC | Lead |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in result.get("results", []) or []:
        lines.append(
            "| {factor} | {horizon} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {spread:.4f} | {mono:.3f} | {ind:.4f} | {size:.4f} | {liq:.4f} | {lead} |".format(
                factor=row.get("factor_name", ""),
                horizon=int(row.get("horizon", 0)),
                ic=_number(row.get("mean_spearman_ic")),
                icir=_number(row.get("icir")),
                t=_number(row.get("ic_t_stat")),
                pos=_number(row.get("ic_positive_rate")),
                spread=_number(row.get("quantile_spread")),
                mono=_number(row.get("quantile_monotonicity")),
                ind=_number(row.get("mean_industry_neutral_rank_ic")),
                size=_number(row.get("mean_size_neutral_rank_ic")),
                liq=_number(row.get("mean_liquidity_neutral_rank_ic")),
                lead="yes" if row.get("research_lead") else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is residual IC, neutralization, quantile-shape, and reference-dedup screening only.",
            "- Portfolio grids, Sharpe, win rate, profit rate, total return, drawdown, and promotion remain blocked.",
            "- Event-day reaction is still only used on the next tradable factor date.",
        ]
    )
    return "\n".join(lines) + "\n"


def _empty_reference_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "asset_id", "market", "reference_factor_name", "reference_factor_value"])


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


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if pd.notna(number) else 0.0
