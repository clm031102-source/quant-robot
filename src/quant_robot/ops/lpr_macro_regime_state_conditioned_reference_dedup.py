from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.lpr_macro_regime_factor_value_reconstruction_smoke import (
    STAGE as SMOKE_STAGE,
    rebuild_lpr_representative_residual_factor_values,
    _align_factor_values_to_lpr_states,
)
from quant_robot.ops.lpr_macro_regime_state_prescreen import (
    FINAL_HOLDOUT_START,
    SAFETY,
    build_lpr_macro_regime_state_frame,
    _read_processed_dataset,
)
from quant_robot.ops.market_residual_lead_exposure_dedup import (
    REFERENCE_CORRELATION_COLUMNS,
    _reference_correlations,
)
from quant_robot.ops.public_reference_multi_family_prescreen import load_public_reference_multi_family_bars
from quant_robot.ops.public_technical_failure_reversal_neutral_dedup import (
    DEFAULT_EXPOSURE_COLUMNS,
    EXPOSURE_CORRELATION_COLUMNS,
    _merge_lead_exposures,
    _technical_exposure_correlations,
)
from quant_robot.ops.public_trend_strength_state_residual_prescreen import (
    build_public_trend_strength_state_bar_features,
    build_public_trend_strength_state_exposure_frame,
    build_public_trend_strength_state_reference_frame,
    _stock_basic_frame,
)


STAGE = "lpr_macro_regime_state_conditioned_reference_dedup"
MACRO_DATASET = "external_macro_rates"
STATE_COLUMN = "lpr_shibor_gap_state"
CANDIDATE_COLUMNS = [
    "source_id",
    "factor_name",
    "base_factor_name",
    "horizon",
    "state",
    "state_factor_rows",
    "state_dates",
    "median_cross_section",
    "reference_redundancy_class",
    "high_reference_count",
    "moderate_reference_count",
    "max_reference_abs_correlation",
    "max_reference_factor_name",
    "exposure_class",
    "high_exposure_count",
    "moderate_exposure_count",
    "max_exposure_abs_correlation",
    "max_exposure_name",
    "state_conditioned_reference_dedup_pass",
    "walk_forward_preflight_allowed_next",
    "walk_forward_preflight_allowed",
    "blockers",
    "requirements",
]
REFERENCE_COLUMNS = [
    "source_id",
    "lead_factor_name",
    "base_factor_name",
    "state",
    "horizon",
    *REFERENCE_CORRELATION_COLUMNS,
]
EXPOSURE_COLUMNS = [
    "source_id",
    "lead_factor_name",
    "base_factor_name",
    "state",
    "horizon",
    *EXPOSURE_CORRELATION_COLUMNS,
]


def run_lpr_macro_regime_state_conditioned_reference_dedup(
    *,
    processed_root: str | Path,
    smoke_path: str | Path,
    bars_roots: Sequence[str | Path],
    daily_basic_roots: Sequence[str | Path],
    stock_basic: str | Path | pd.DataFrame | None,
    output_dir: str | Path,
    market: str = "CN",
    analysis_start_date: str = "2024-07-01",
    analysis_end_date: str = "2025-12-31",
    lookback_days: int = 60,
    min_abs_gap_change: float = 0.01,
    min_signal_date_amount: float = 10_000_000,
    min_cross_section: int = 30,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
    min_state_dates: int = 20,
    min_median_cross_section: int = 100,
    high_reference_corr_threshold: float = 0.85,
    high_reference_mean_abs_corr_threshold: float = 0.70,
    moderate_reference_corr_threshold: float = 0.70,
    moderate_reference_mean_abs_corr_threshold: float = 0.50,
    high_exposure_corr_threshold: float = 0.85,
    high_exposure_mean_abs_corr_threshold: float = 0.50,
) -> dict[str, Any]:
    smoke = json.loads(Path(smoke_path).read_text(encoding="utf-8"))
    macro_rates = _read_processed_dataset(Path(processed_root), MACRO_DATASET, market)
    state_frame = build_lpr_macro_regime_state_frame(
        macro_rates,
        lookback_days=lookback_days,
        min_abs_gap_change=min_abs_gap_change,
        market=market,
    )
    factor_frame = rebuild_lpr_representative_residual_factor_values(
        _reconstruction_preflight_from_smoke(smoke),
        bars_roots=bars_roots,
        daily_basic_roots=daily_basic_roots,
        stock_basic=stock_basic,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        min_signal_date_amount=min_signal_date_amount,
        min_cross_section=min_cross_section,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
    )
    candidates = _candidate_inputs(smoke)
    horizons = tuple(sorted({int(row["horizon"]) for row in candidates if int(row["horizon"]) > 0})) or (20,)
    bars = load_public_reference_multi_family_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=False,
    )
    features = build_public_trend_strength_state_bar_features(bars, horizons=horizons, execution_lag=1)
    exposure_frame = build_public_trend_strength_state_exposure_frame(features, _stock_basic_frame(stock_basic))
    reference_frame = build_public_trend_strength_state_reference_frame(bars, exposure_frame)
    result = summarize_lpr_macro_regime_state_conditioned_reference_dedup(
        smoke,
        factor_frame,
        reference_frame,
        exposure_frame,
        state_frame,
        processed_root=processed_root,
        smoke_path=smoke_path,
        bars_roots=bars_roots,
        daily_basic_roots=daily_basic_roots,
        stock_basic=stock_basic,
        market=market,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        lookback_days=lookback_days,
        min_abs_gap_change=min_abs_gap_change,
        min_signal_date_amount=min_signal_date_amount,
        min_state_dates=min_state_dates,
        min_median_cross_section=min_median_cross_section,
        min_cross_section=min_cross_section,
        high_reference_corr_threshold=high_reference_corr_threshold,
        high_reference_mean_abs_corr_threshold=high_reference_mean_abs_corr_threshold,
        moderate_reference_corr_threshold=moderate_reference_corr_threshold,
        moderate_reference_mean_abs_corr_threshold=moderate_reference_mean_abs_corr_threshold,
        high_exposure_corr_threshold=high_exposure_corr_threshold,
        high_exposure_mean_abs_corr_threshold=high_exposure_mean_abs_corr_threshold,
    )
    write_lpr_macro_regime_state_conditioned_reference_dedup(output_dir, result)
    return result


def summarize_lpr_macro_regime_state_conditioned_reference_dedup(
    smoke: dict[str, Any],
    factor_frame: pd.DataFrame,
    reference_frame: pd.DataFrame,
    exposure_frame: pd.DataFrame,
    state_frame: pd.DataFrame,
    *,
    processed_root: str | Path | None = None,
    smoke_path: str | Path | None = None,
    bars_roots: Sequence[str | Path] = (),
    daily_basic_roots: Sequence[str | Path] = (),
    stock_basic: str | Path | pd.DataFrame | None = None,
    market: str = "CN",
    analysis_start_date: str = "2024-07-01",
    analysis_end_date: str = "2025-12-31",
    lookback_days: int = 60,
    min_abs_gap_change: float = 0.01,
    min_signal_date_amount: float = 10_000_000,
    min_state_dates: int = 20,
    min_median_cross_section: int = 100,
    min_cross_section: int = 30,
    high_reference_corr_threshold: float = 0.85,
    high_reference_mean_abs_corr_threshold: float = 0.70,
    moderate_reference_corr_threshold: float = 0.70,
    moderate_reference_mean_abs_corr_threshold: float = 0.50,
    high_exposure_corr_threshold: float = 0.85,
    high_exposure_mean_abs_corr_threshold: float = 0.50,
) -> dict[str, Any]:
    global_blockers = _smoke_blockers(smoke)
    candidates = _candidate_inputs(smoke)
    if not candidates:
        global_blockers.append("no_factor_value_ready_lpr_representatives")
    aligned_factors = _analysis_window(
        _align_factor_values_to_lpr_states(factor_frame, state_frame),
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
    )
    aligned_references = _analysis_window(
        _align_factor_values_to_lpr_states(reference_frame, state_frame),
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
    )
    aligned_exposures = _analysis_window(
        _align_exposures_to_lpr_states(exposure_frame, state_frame),
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
    )
    candidate_results, reference_correlations, exposure_correlations = _candidate_results(
        candidates,
        aligned_factors,
        aligned_references,
        aligned_exposures,
        global_blockers=global_blockers,
        min_state_dates=min_state_dates,
        min_median_cross_section=min_median_cross_section,
        min_cross_section=min_cross_section,
        high_reference_corr_threshold=high_reference_corr_threshold,
        high_reference_mean_abs_corr_threshold=high_reference_mean_abs_corr_threshold,
        moderate_reference_corr_threshold=moderate_reference_corr_threshold,
        moderate_reference_mean_abs_corr_threshold=moderate_reference_mean_abs_corr_threshold,
        high_exposure_corr_threshold=high_exposure_corr_threshold,
        high_exposure_mean_abs_corr_threshold=high_exposure_mean_abs_corr_threshold,
    )
    pass_count = sum(1 for row in candidate_results if row["state_conditioned_reference_dedup_pass"])
    high_reference_count = sum(1 for row in candidate_results if row["reference_redundancy_class"] == "highly_redundant")
    high_exposure_count = sum(1 for row in candidate_results if row["exposure_class"] == "high_exposure")
    decision_blockers = _unique(global_blockers)
    if pass_count <= 0:
        decision_blockers.append("no_state_conditioned_reference_dedup_survivors")
    passes = bool(not global_blockers and pass_count > 0)
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "market": market,
        "processed_root": str(Path(processed_root)) if processed_root is not None else None,
        "smoke_path": str(Path(smoke_path)) if smoke_path is not None else None,
        "bars_roots": [str(Path(path)) for path in bars_roots],
        "daily_basic_roots": [str(Path(path)) for path in daily_basic_roots],
        "stock_basic": str(stock_basic) if isinstance(stock_basic, (str, Path)) else None,
        "summary": {
            "passes": passes,
            "representative_candidate_count": len(candidates),
            "factor_value_rows": int(len(factor_frame)),
            "state_conditioned_reference_dedup_pass_count": pass_count,
            "state_conditioned_reference_dedup_blocked_count": len(candidate_results) - pass_count,
            "high_reference_redundancy_candidate_count": high_reference_count,
            "high_exposure_candidate_count": high_exposure_count,
            "reference_correlation_rows": len(reference_correlations),
            "exposure_correlation_rows": len(exposure_correlations),
            "walk_forward_preflight_allowed_next_candidate_count": pass_count if passes else 0,
            "walk_forward_preflight_allowed_candidates": 0,
            "portfolio_grid_allowed_candidates": 0,
            "promotion_allowed_candidates": 0,
            "next_direction": (
                "state_conditioned_walk_forward_preflight_after_reference_dedup"
                if passes
                else "repair_or_rotate_lpr_state_conditioned_reference_dedup"
            ),
        },
        "data_window": {
            "analysis_start_date": analysis_start_date,
            "analysis_end_date": analysis_end_date,
            "first_factor_date": _min_date(aligned_factors, "date"),
            "last_factor_date": _max_date(aligned_factors, "date"),
        },
        "thresholds": {
            "min_signal_date_amount": float(min_signal_date_amount),
            "min_state_dates": int(min_state_dates),
            "min_median_cross_section": int(min_median_cross_section),
            "min_cross_section": int(min_cross_section),
            "lookback_days": int(lookback_days),
            "min_abs_gap_change": float(min_abs_gap_change),
            "high_reference_corr_threshold": float(high_reference_corr_threshold),
            "high_reference_mean_abs_corr_threshold": float(high_reference_mean_abs_corr_threshold),
            "moderate_reference_corr_threshold": float(moderate_reference_corr_threshold),
            "moderate_reference_mean_abs_corr_threshold": float(moderate_reference_mean_abs_corr_threshold),
            "high_exposure_corr_threshold": float(high_exposure_corr_threshold),
            "high_exposure_mean_abs_corr_threshold": float(high_exposure_mean_abs_corr_threshold),
        },
        "holdout_policy": {
            "final_holdout_start": FINAL_HOLDOUT_START,
            "final_holdout_use": "blocked_for_state_conditioned_reference_dedup",
        },
        "candidate_results": candidate_results,
        "reference_correlations": reference_correlations,
        "exposure_correlations": exposure_correlations,
        "decision": {
            "research_screen_allowed": passes,
            "walk_forward_preflight_allowed_next": passes,
            "walk_forward_preflight_allowed": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "blockers": _unique(decision_blockers),
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed": False,
            "requires_walk_forward_after_dedup": True,
            "requires_cost_capacity_gate": True,
            "requires_regime_coverage": True,
            "requires_final_holdout_read_once": True,
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_lpr_macro_regime_state_conditioned_reference_dedup_markdown(result)
    return result


def write_lpr_macro_regime_state_conditioned_reference_dedup(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(result)
    (output_path / "lpr_macro_regime_state_conditioned_reference_dedup.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "lpr_macro_regime_state_conditioned_reference_dedup.md").write_text(
        render_lpr_macro_regime_state_conditioned_reference_dedup_markdown(clean),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "lpr_macro_regime_state_conditioned_reference_dedup_candidates.csv",
        clean["candidate_results"],
        CANDIDATE_COLUMNS,
    )
    _write_csv(
        output_path / "lpr_macro_regime_state_conditioned_reference_correlations.csv",
        clean["reference_correlations"],
        REFERENCE_COLUMNS,
    )
    _write_csv(
        output_path / "lpr_macro_regime_state_conditioned_exposure_correlations.csv",
        clean["exposure_correlations"],
        EXPOSURE_COLUMNS,
    )


def render_lpr_macro_regime_state_conditioned_reference_dedup_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    decision = result.get("decision", {})
    lines = [
        "# LPR Macro Regime State-Conditioned Reference Dedup",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Representative candidates: {summary.get('representative_candidate_count', 0)}",
        f"- Dedup pass count: {summary.get('state_conditioned_reference_dedup_pass_count', 0)}",
        f"- Dedup blocked count: {summary.get('state_conditioned_reference_dedup_blocked_count', 0)}",
        f"- High reference candidates: {summary.get('high_reference_redundancy_candidate_count', 0)}",
        f"- High exposure candidates: {summary.get('high_exposure_candidate_count', 0)}",
        f"- Walk-forward preflight allowed next: {decision.get('walk_forward_preflight_allowed_next', False)}",
        f"- Walk-forward preflight run now: {decision.get('walk_forward_preflight_allowed', False)}",
        f"- Portfolio grid allowed: {decision.get('portfolio_grid_allowed', False)}",
        f"- Promotion allowed: {decision.get('promotion_allowed', False)}",
        f"- Next direction: `{summary.get('next_direction', '')}`",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Decision Blockers",
        "",
    ]
    blockers = _as_list(decision.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(
        [
            "",
            "## Candidate Gate",
            "",
            "| Factor | State | Dates | Median CS | Ref | Max Ref | Exposure | Max Exp | Pass | Next WF Preflight | Blockers | Requirements |",
            "|---|---|---:|---:|---|---:|---|---:|---|---|---|---|",
        ]
    )
    for row in result.get("candidate_results", []):
        lines.append(
            "| {factor} | {state} | {dates} | {cs:.1f} | {ref} | {max_ref:.3f} | {exp} | {max_exp:.3f} | {passed} | {wf_next} | {blockers} | {reqs} |".format(
                factor=row.get("factor_name", ""),
                state=row.get("state", ""),
                dates=row.get("state_dates", 0),
                cs=float(row.get("median_cross_section", 0.0) or 0.0),
                ref=row.get("reference_redundancy_class", ""),
                max_ref=float(row.get("max_reference_abs_correlation", 0.0) or 0.0),
                exp=row.get("exposure_class", ""),
                max_exp=float(row.get("max_exposure_abs_correlation", 0.0) or 0.0),
                passed="yes" if row.get("state_conditioned_reference_dedup_pass", False) else "no",
                wf_next="yes" if row.get("walk_forward_preflight_allowed_next", False) else "no",
                blockers=", ".join(_as_list(row.get("blockers"))) or "none",
                reqs=", ".join(_as_list(row.get("requirements"))) or "none",
            )
        )
    return "\n".join(lines) + "\n"


def _candidate_results(
    candidates: Sequence[dict[str, Any]],
    aligned_factors: pd.DataFrame,
    aligned_references: pd.DataFrame,
    aligned_exposures: pd.DataFrame,
    *,
    global_blockers: Sequence[str],
    min_state_dates: int,
    min_median_cross_section: int,
    min_cross_section: int,
    high_reference_corr_threshold: float,
    high_reference_mean_abs_corr_threshold: float,
    moderate_reference_corr_threshold: float,
    moderate_reference_mean_abs_corr_threshold: float,
    high_exposure_corr_threshold: float,
    high_exposure_mean_abs_corr_threshold: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    candidate_rows = []
    all_reference_rows = []
    all_exposure_rows = []
    for candidate in candidates:
        state = candidate["state"]
        lead_state = aligned_factors[
            (aligned_factors["factor_name"] == candidate["factor_name"]) & (aligned_factors[STATE_COLUMN] == state)
        ].copy()
        reference_state = aligned_references[aligned_references[STATE_COLUMN] == state].copy()
        exposure_state = aligned_exposures[aligned_exposures[STATE_COLUMN] == state].copy()
        reference_rows = [
            _with_lead_metadata(row, candidate)
            for row in _reference_correlations(
                lead_state,
                reference_state,
                lead_factor_name=candidate["factor_name"],
                min_cross_section=min_cross_section,
                high_corr_threshold=high_reference_corr_threshold,
                high_mean_abs_corr_threshold=high_reference_mean_abs_corr_threshold,
                moderate_corr_threshold=moderate_reference_corr_threshold,
                moderate_mean_abs_corr_threshold=moderate_reference_mean_abs_corr_threshold,
            )
        ]
        lead_with_exposures = _merge_lead_exposures(lead_state, exposure_state)
        exposure_rows = [
            _with_lead_metadata(row, candidate)
            for row in _technical_exposure_correlations(
                lead_with_exposures,
                exposure_names=DEFAULT_EXPOSURE_COLUMNS,
                min_cross_section=min_cross_section,
                high_exposure_corr_threshold=high_exposure_corr_threshold,
                high_exposure_mean_abs_corr_threshold=high_exposure_mean_abs_corr_threshold,
            )
        ]
        all_reference_rows.extend(reference_rows)
        all_exposure_rows.extend(exposure_rows)
        candidate_rows.append(
            _single_candidate_result(
                candidate,
                lead_state,
                reference_rows,
                exposure_rows,
                global_blockers=global_blockers,
                min_state_dates=min_state_dates,
                min_median_cross_section=min_median_cross_section,
            )
        )
    return candidate_rows, all_reference_rows, all_exposure_rows


def _single_candidate_result(
    candidate: dict[str, Any],
    lead_state: pd.DataFrame,
    reference_rows: Sequence[dict[str, Any]],
    exposure_rows: Sequence[dict[str, Any]],
    *,
    global_blockers: Sequence[str],
    min_state_dates: int,
    min_median_cross_section: int,
) -> dict[str, Any]:
    cross_sections = lead_state.groupby("date")["asset_id"].nunique() if not lead_state.empty else pd.Series(dtype=float)
    median_cross_section = float(cross_sections.median()) if not cross_sections.empty else 0.0
    reference_class = _worst_class(reference_rows, "redundancy_class", _REFERENCE_CLASS_ORDER, default="missing")
    exposure_class = _worst_class(exposure_rows, "exposure_class", _EXPOSURE_CLASS_ORDER, default="missing")
    top_reference = _top_correlation(reference_rows, "factor_name")
    top_exposure = _top_correlation(exposure_rows, "exposure_name")
    blockers = list(global_blockers)
    requirements = [
        "requires_walk_forward_preflight_before_portfolio_grid",
        "requires_cost_capacity_gate_after_walk_forward",
        "requires_final_holdout_sealed_until_final_validation",
    ]
    if lead_state["date"].nunique() < int(min_state_dates):
        blockers.append("state_factor_dates_below_threshold")
    if median_cross_section < float(min_median_cross_section):
        blockers.append("state_factor_median_cross_section_below_threshold")
    if len(lead_state) <= 0:
        blockers.append("state_conditioned_factor_value_rows_missing")
    if not reference_rows or reference_class == "insufficient_overlap":
        blockers.append("state_conditioned_reference_evidence_missing")
    if not exposure_rows or exposure_class == "insufficient_overlap":
        blockers.append("state_conditioned_exposure_evidence_missing")
    if reference_class == "highly_redundant":
        blockers.append("state_conditioned_high_reference_redundancy")
    elif reference_class == "moderately_redundant":
        requirements.append("state_conditioned_moderate_reference_redundancy_requires_walk_forward_challenge")
    if exposure_class == "high_exposure":
        blockers.append("state_conditioned_high_exposure_correlation")
    elif exposure_class == "moderate_exposure":
        requirements.append("state_conditioned_moderate_exposure_requires_walk_forward_challenge")
    passed = not blockers
    return {
        **candidate,
        "state_factor_rows": int(len(lead_state)),
        "state_dates": int(lead_state["date"].nunique()) if "date" in lead_state else 0,
        "median_cross_section": median_cross_section,
        "first_state_date": _min_date(lead_state, "date"),
        "last_state_date": _max_date(lead_state, "date"),
        "reference_redundancy_class": reference_class,
        "high_reference_count": sum(1 for row in reference_rows if row.get("redundancy_class") == "highly_redundant"),
        "moderate_reference_count": sum(1 for row in reference_rows if row.get("redundancy_class") == "moderately_redundant"),
        "max_reference_abs_correlation": float(top_reference.get("max_abs_correlation", 0.0) or 0.0),
        "max_reference_factor_name": top_reference.get("factor_name", ""),
        "exposure_class": exposure_class,
        "high_exposure_count": sum(1 for row in exposure_rows if row.get("exposure_class") == "high_exposure"),
        "moderate_exposure_count": sum(1 for row in exposure_rows if row.get("exposure_class") == "moderate_exposure"),
        "max_exposure_abs_correlation": float(top_exposure.get("max_abs_correlation", 0.0) or 0.0),
        "max_exposure_name": top_exposure.get("exposure_name", ""),
        "state_conditioned_reference_dedup_pass": bool(passed),
        "walk_forward_preflight_allowed_next": bool(passed),
        "walk_forward_preflight_allowed": False,
        "blockers": _unique(blockers),
        "requirements": _unique(requirements),
    }


def _smoke_blockers(smoke: dict[str, Any]) -> list[str]:
    decision = _dict(smoke.get("decision"))
    blockers = []
    if smoke.get("stage") != SMOKE_STAGE:
        blockers.append("factor_value_reconstruction_smoke_stage_mismatch")
    if _dict(smoke.get("summary")).get("passes") is not True:
        blockers.append("factor_value_reconstruction_smoke_not_passing")
    if decision.get("factor_value_reference_dedup_allowed_next") is not True:
        blockers.append("factor_value_reconstruction_smoke_not_allowed_for_reference_dedup")
    if decision.get("walk_forward_preflight_allowed") is not False:
        blockers.append("factor_value_reconstruction_smoke_walk_forward_boundary_violation")
    if decision.get("portfolio_grid_allowed") is not False or decision.get("promotion_allowed") is not False:
        blockers.append("factor_value_reconstruction_smoke_policy_boundary_violation")
    if smoke.get("live_boundary_allowed") is not False:
        blockers.append("factor_value_reconstruction_smoke_live_boundary_violation")
    return blockers


def _candidate_inputs(smoke: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in smoke.get("candidate_results", []):
        if not isinstance(row, dict) or row.get("factor_value_reference_dedup_input_ready") is not True:
            continue
        rows.append(
            {
                "source_id": str(row.get("source_id", "")),
                "factor_name": str(row.get("factor_name", "")),
                "base_factor_name": str(row.get("base_factor_name", "")),
                "horizon": int(row.get("horizon", 0)),
                "state": str(row.get("state", "")),
            }
        )
    return rows


def _reconstruction_preflight_from_smoke(smoke: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_results": [
            {
                **row,
                "cluster_representative": True,
                "factor_value_reference_dedup_allowed": True,
            }
            for row in _candidate_inputs(smoke)
        ]
    }


def _align_exposures_to_lpr_states(exposure_frame: pd.DataFrame, state_frame: pd.DataFrame) -> pd.DataFrame:
    if exposure_frame is None or exposure_frame.empty:
        columns = ["date", "asset_id", "market", "lpr_available_date", STATE_COLUMN]
        return pd.DataFrame(columns=columns)
    if state_frame is None or state_frame.empty or "available_date" not in state_frame or STATE_COLUMN not in state_frame:
        output = exposure_frame.copy()
        output["lpr_available_date"] = pd.NaT
        output[STATE_COLUMN] = pd.NA
        return output
    exposures = exposure_frame.copy()
    exposures["date"] = pd.to_datetime(exposures["date"], errors="coerce").astype("datetime64[ns]")
    exposures["asset_id"] = exposures["asset_id"].astype(str)
    exposures["market"] = exposures["market"].astype(str)
    states = state_frame[["available_date", STATE_COLUMN]].copy()
    states["available_date"] = pd.to_datetime(states["available_date"], errors="coerce").astype("datetime64[ns]")
    states[STATE_COLUMN] = states[STATE_COLUMN].astype(str)
    states = states.dropna(subset=["available_date", STATE_COLUMN]).drop_duplicates("available_date", keep="last")
    aligned = pd.merge_asof(
        exposures.dropna(subset=["date"]).sort_values("date").reset_index(drop=True),
        states.sort_values("available_date").reset_index(drop=True),
        left_on="date",
        right_on="available_date",
        direction="backward",
        allow_exact_matches=True,
    )
    return aligned.rename(columns={"available_date": "lpr_available_date"})


def _analysis_window(frame: pd.DataFrame, *, analysis_start_date: str, analysis_end_date: str) -> pd.DataFrame:
    if frame.empty or "date" not in frame:
        return frame.copy()
    output = frame[
        (frame["date"] >= pd.Timestamp(analysis_start_date))
        & (frame["date"] <= pd.Timestamp(analysis_end_date))
        & (frame["date"] < pd.Timestamp(FINAL_HOLDOUT_START))
    ].copy()
    return output.reset_index(drop=True)


def _with_lead_metadata(row: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": candidate["source_id"],
        "lead_factor_name": candidate["factor_name"],
        "base_factor_name": candidate["base_factor_name"],
        "state": candidate["state"],
        "horizon": int(candidate["horizon"]),
        **row,
    }


_REFERENCE_CLASS_ORDER = {
    "highly_redundant": 4,
    "moderately_redundant": 3,
    "unique": 2,
    "insufficient_overlap": 1,
    "missing": 0,
}
_EXPOSURE_CLASS_ORDER = {
    "high_exposure": 4,
    "moderate_exposure": 3,
    "low_exposure": 2,
    "insufficient_overlap": 1,
    "missing": 0,
}


def _worst_class(rows: Sequence[dict[str, Any]], key: str, order: dict[str, int], *, default: str) -> str:
    if not rows:
        return default
    values = [str(row.get(key, default)) for row in rows]
    return sorted(values, key=lambda value: (-order.get(value, 0), value))[0]


def _top_correlation(rows: Sequence[dict[str, Any]], name_key: str) -> dict[str, Any]:
    if not rows:
        return {name_key: "", "max_abs_correlation": 0.0}
    return sorted(
        rows,
        key=lambda row: (
            -float(row.get("max_abs_correlation", 0.0) or 0.0),
            -float(row.get("mean_abs_correlation", 0.0) or 0.0),
            str(row.get(name_key, "")),
        ),
    )[0]


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: Sequence[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            clean = dict(row)
            for field in ("blockers", "requirements"):
                if isinstance(clean.get(field), list):
                    clean[field] = "|".join(str(item) for item in clean[field])
            writer.writerow(clean)


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").min()
    return None if pd.isna(value) else value.date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").max()
    return None if pd.isna(value) else value.date().isoformat()


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if value in (None, ""):
        return []
    return [str(value)]


def _unique(values: Iterable[Any]) -> list[str]:
    output = []
    seen = set()
    for value in values:
        text = str(value)
        if text not in seen:
            output.append(text)
            seen.add(text)
    return output
