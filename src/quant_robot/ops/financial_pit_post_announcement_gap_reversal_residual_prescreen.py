from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.financial_pit_post_announcement_drift_preregistration import SAFETY
from quant_robot.ops.financial_pit_post_announcement_drift_residual_prescreen import (
    build_financial_pit_post_announcement_drift_residual_prescreen,
)
from quant_robot.ops.profitability_event_revision_controlled_ic_neutral_prescreen import (
    NEUTRAL_OBSERVATION_COLUMNS,
    REFERENCE_CORRELATION_COLUMNS,
    RESULT_COLUMNS,
)
from quant_robot.ops.profitability_quality_preregistration import _sanitize


STAGE = "financial_pit_post_announcement_gap_reversal_residual_prescreen"
NEXT_DIRECTION_WITH_LEADS = "round224_financial_pit_post_announcement_gap_reversal_reference_dedup_walk_forward_preflight"
NEXT_DIRECTION_WITHOUT_LEADS = "round224_rotate_or_repair_financial_pit_post_announcement_gap_reversal_after_residual_failure"


def build_financial_pit_post_announcement_gap_reversal_residual_prescreen(
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
    horizons: tuple[int, ...] = (5,),
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
    result = build_financial_pit_post_announcement_drift_residual_prescreen(
        financial_root=financial_root,
        bars_roots=bars_roots,
        preregistration_json=preregistration_json,
        candidate_plan_gate_json=candidate_plan_gate_json,
        stock_basic_path=stock_basic_path,
        daily_basic_roots=daily_basic_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        horizons=horizons,
        execution_lag=execution_lag,
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
    result["stage"] = STAGE
    result["summary"]["next_direction"] = (
        NEXT_DIRECTION_WITH_LEADS if research_lead_count else NEXT_DIRECTION_WITHOUT_LEADS
    )
    result["promotion_policy"] = {
        "promotion_allowed": False,
        "portfolio_backtest_allowed_before_prescreen": False,
        "requires_next_gate": "walk_forward_cost_capacity_regime_preflight_after_gap_reversal_residual_lead",
        "reason": "This is a residual IC/neutral prescreen, not portfolio or paper-ready validation.",
    }
    result["gap_reversal_policy"] = {
        "source_failure": "round222_pead_event_gap_underreaction_wrong_signed_after_residual_prescreen",
        "fresh_preregistration_required": True,
        "portfolio_grid_allowed_before_residual_prescreen": False,
    }
    result["markdown"] = render_financial_pit_post_announcement_gap_reversal_residual_prescreen_markdown(result)
    return result


def write_financial_pit_post_announcement_gap_reversal_residual_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "financial_pit_post_announcement_gap_reversal_residual_prescreen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "financial_pit_post_announcement_gap_reversal_residual_prescreen.md").write_text(
        render_financial_pit_post_announcement_gap_reversal_residual_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "financial_pit_post_announcement_gap_reversal_residual_ic_results.csv", result.get("results", []) or [], RESULT_COLUMNS)
    _write_csv(
        output_path / "financial_pit_post_announcement_gap_reversal_residual_ic_observations.csv",
        result.get("ic_observations", []) or [],
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )
    _write_csv(
        output_path / "financial_pit_post_announcement_gap_reversal_neutral_observations.csv",
        result.get("neutral_observations", []) or [],
        NEUTRAL_OBSERVATION_COLUMNS,
    )
    _write_csv(
        output_path / "financial_pit_post_announcement_gap_reversal_reference_correlations.csv",
        result.get("reference_correlations", []) or [],
        REFERENCE_CORRELATION_COLUMNS,
    )


def render_financial_pit_post_announcement_gap_reversal_residual_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {}) or {}
    lines = [
        "# Financial PIT Post-Announcement Gap Reversal Residual Prescreen",
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
            "- It tests a fresh inverse-sign gap reversal hypothesis after Round222 rejected the underreaction sign.",
            "- Portfolio grids, Sharpe, win rate, profit rate, total return, drawdown, and promotion remain blocked.",
        ]
    )
    return "\n".join(lines) + "\n"


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
