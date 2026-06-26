from __future__ import annotations

from datetime import date
import csv
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_preregistration import (
    SAFETY,
    default_capacity_safe_price_volume_candidate_specs,
)
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    compute_capacity_safe_price_volume_factors,
    load_capacity_safe_bars,
)
from quant_robot.ops.event_contextual_underreaction_prescreen import (
    compute_event_contextual_underreaction_factor_frame,
    default_event_contextual_underreaction_candidate_specs,
    _daily_zscore,
    _signal_context_frame,
)
from quant_robot.ops.event_factor_pit_ic_prescreen import (
    _normalise_bars,
    compute_event_factor_frame,
)
from quant_robot.ops.event_factor_preregistration import default_event_factor_candidate_specs
from quant_robot.ops.market_residual_lead_exposure_dedup import (
    IC_OBSERVATION_COLUMNS,
    MONTHLY_IC_COLUMNS,
    REFERENCE_CORRELATION_COLUMNS,
    YEARLY_IC_COLUMNS,
    _filter_dates,
    _lead_ic_observations,
    _lead_ic_summary,
    _load_report,
    _normalise_factor_frame,
    _period_ic,
    _reference_correlations,
    _sample_dates,
)
from quant_robot.ops.profitability_quality_preregistration import _sanitize
from quant_robot.research.labels import make_forward_returns


STAGE = "event_contextual_underreaction_reference_dedup"
NEXT_WALK_FORWARD_PREFLIGHT_DIRECTION = "round250_event_contextual_underreaction_walk_forward_preflight"
NEXT_HIBERNATE_OR_ORTHOGONALIZE_DIRECTION = "round250_hibernate_or_orthogonalize_event_contextual_underreaction_after_dedup_failure"
DEFAULT_PRICE_VOLUME_REFERENCE_NAMES = (
    "pv_lowvol_reversal_blend_20",
    "range_contraction_lowvol_reversal_20",
    "bollinger_reversal_lowvol_liquid_20",
    "rsi_reversal_lowvol_liquid_14_20",
    "amount_stability_reversal_5_20",
    "donchian_pullback_lowvol_liquid_20",
)
RAW_EVENT_FACTOR_NAMES = (
    "event_repurchase_amount_to_mv_20",
    "event_holder_number_contraction_2q",
)
REFERENCE_OUTPUT_COLUMNS = ["lead_factor_name", "horizon", *REFERENCE_CORRELATION_COLUMNS]
PERIOD_OUTPUT_COLUMNS = ["lead_factor_name", "horizon", *YEARLY_IC_COLUMNS]
MONTHLY_OUTPUT_COLUMNS = ["lead_factor_name", "horizon", *MONTHLY_IC_COLUMNS]
IC_OUTPUT_COLUMNS = IC_OBSERVATION_COLUMNS


def build_event_contextual_underreaction_reference_dedup(
    *,
    event_frames: dict[str, pd.DataFrame],
    stock_basic: pd.DataFrame,
    bars_roots: Iterable[str | Path],
    prescreen_report: dict[str, Any] | str | Path,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    execution_lag: int = 1,
    pit_lag_trade_days: int = 1,
    sample_every_n_dates: int = 5,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_reference_correlation_observations: int = 5,
    include_price_volume_references: bool = True,
    price_volume_reference_names: Sequence[str] = DEFAULT_PRICE_VOLUME_REFERENCE_NAMES,
) -> dict[str, Any]:
    report = _load_report(prescreen_report)
    bars = load_capacity_safe_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    clean_bars = _normalise_bars(bars)
    factor_frame = compute_event_contextual_underreaction_factor_frame(
        event_frames,
        clean_bars,
        stock_basic,
        candidate_specs=default_event_contextual_underreaction_candidate_specs(),
        pit_lag_trade_days=pit_lag_trade_days,
    )
    reference_frame = compute_event_contextual_underreaction_reference_frame(
        event_frames,
        clean_bars,
        stock_basic,
        include_price_volume_references=include_price_volume_references,
        price_volume_reference_names=price_volume_reference_names,
        pit_lag_trade_days=pit_lag_trade_days,
    )
    horizons = tuple(sorted({int(row.get("horizon", 0)) for row in report.get("results", []) if row.get("research_lead")}))
    if not horizons:
        horizons = (5, 20)
    labels = make_forward_returns(
        clean_bars[["date", "asset_id", "market", "adj_close"]],
        horizons=horizons,
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_event_contextual_underreaction_reference_dedup(
        factor_frame,
        labels,
        reference_factor_frame=reference_frame,
        prescreen_report=report,
        sample_every_n_dates=sample_every_n_dates,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_reference_correlation_observations=min_reference_correlation_observations,
    )
    result["data_window"] = _data_window(clean_bars, factor_frame, reference_frame, labels, event_frames)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_and_dedup_clearance_only",
    }
    result["pit_policy"] = {
        "pit_lag_trade_days": int(pit_lag_trade_days),
        "same_day_event_trading_allowed": False,
        "execution_lag": int(execution_lag),
    }
    result["sampling_policy"] = {
        "sample_every_n_dates": int(sample_every_n_dates),
        "sampling_used_for_reference_correlations_only": True,
        "ic_uses_all_dates": True,
    }
    result["reference_policy"] = {
        "include_raw_event_references": True,
        "include_event_context_component_references": True,
        "include_price_volume_references": bool(include_price_volume_references),
        "price_volume_reference_names": list(price_volume_reference_names),
    }
    result["markdown"] = render_event_contextual_underreaction_reference_dedup_markdown(result)
    return result


def compute_event_contextual_underreaction_reference_frame(
    event_frames: dict[str, pd.DataFrame],
    bars: pd.DataFrame,
    stock_basic: pd.DataFrame,
    *,
    include_price_volume_references: bool = True,
    price_volume_reference_names: Sequence[str] = DEFAULT_PRICE_VOLUME_REFERENCE_NAMES,
    pit_lag_trade_days: int = 1,
) -> pd.DataFrame:
    clean_bars = _normalise_bars(bars)
    base_specs = [spec for spec in default_event_factor_candidate_specs() if spec.factor_name in RAW_EVENT_FACTOR_NAMES]
    raw = compute_event_factor_frame(
        event_frames,
        clean_bars,
        stock_basic,
        candidate_specs=base_specs,
        pit_lag_trade_days=pit_lag_trade_days,
    )
    pieces: list[pd.DataFrame] = []
    if not raw.empty:
        raw_refs = raw.copy()
        raw_refs["factor_name"] = raw_refs["factor_name"].map(
            {
                "event_repurchase_amount_to_mv_20": "raw_event_repurchase_amount_to_mv_20",
                "event_holder_number_contraction_2q": "raw_event_holder_number_contraction_2q",
            }
        )
        pieces.append(_reference_columns(raw_refs))
        context = _signal_context_frame(clean_bars)
        raw_context = raw.merge(context, on=["date", "asset_id", "market"], how="left", validate="many_to_one")
        pieces.extend(_context_reference_pieces(raw_context))
    if include_price_volume_references:
        specs = _price_volume_reference_specs(price_volume_reference_names)
        if specs:
            price_refs = compute_capacity_safe_price_volume_factors(clean_bars, candidate_specs=specs)
            pieces.append(_reference_columns(price_refs))
    pieces = [piece for piece in pieces if piece is not None and not piece.empty]
    if not pieces:
        return _empty_factor_frame()
    return pd.concat(pieces, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def summarize_event_contextual_underreaction_reference_dedup(
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    reference_factor_frame: pd.DataFrame | None = None,
    prescreen_report: dict[str, Any] | None = None,
    sample_every_n_dates: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_reference_correlation_observations: int = 5,
    high_corr_threshold: float = 0.85,
    high_mean_abs_corr_threshold: float = 0.70,
    moderate_corr_threshold: float = 0.70,
    moderate_mean_abs_corr_threshold: float = 0.50,
) -> dict[str, Any]:
    frame = _normalise_factor_frame(factor_frame)
    reference_frame = _normalise_factor_frame(reference_factor_frame if reference_factor_frame is not None else pd.DataFrame())
    leads = _lead_requests(prescreen_report, frame)
    lead_results = []
    for lead_factor_name, horizon in leads:
        lead_results.append(
            _summarize_one_lead(
                frame,
                labels,
                reference_frame,
                prescreen_report=prescreen_report,
                lead_factor_name=lead_factor_name,
                horizon=int(horizon),
                sample_every_n_dates=sample_every_n_dates,
                min_cross_section=min_cross_section,
                min_ic_observations=min_ic_observations,
                min_reference_correlation_observations=min_reference_correlation_observations,
                high_corr_threshold=high_corr_threshold,
                high_mean_abs_corr_threshold=high_mean_abs_corr_threshold,
                moderate_corr_threshold=moderate_corr_threshold,
                moderate_mean_abs_corr_threshold=moderate_mean_abs_corr_threshold,
            )
        )
    dedup_pass_count = sum(1 for row in lead_results if not row["gate"]["blockers"])
    next_direction = NEXT_WALK_FORWARD_PREFLIGHT_DIRECTION if dedup_pass_count else NEXT_HIBERNATE_OR_ORTHOGONALIZE_DIRECTION
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": {
            "lead_count": int(len(lead_results)),
            "dedup_pass_count": int(dedup_pass_count),
            "blocked_lead_count": int(len(lead_results) - dedup_pass_count),
            "reference_factor_count": int(reference_frame["factor_name"].nunique()) if not reference_frame.empty else 0,
            "highly_redundant_lead_count": int(
                sum(1 for row in lead_results if "lead_highly_redundant_with_reference_factor" in row["gate"]["blockers"])
            ),
            "yearly_failure_lead_count": int(sum(1 for row in lead_results if "yearly_ic_instability" in row["gate"]["blockers"])),
            "promotion_allowed_candidates": 0,
        },
        "thresholds": {
            "min_cross_section": int(min_cross_section),
            "min_ic_observations": int(min_ic_observations),
            "min_reference_correlation_observations": int(min_reference_correlation_observations),
            "high_corr_threshold": float(high_corr_threshold),
            "high_mean_abs_corr_threshold": float(high_mean_abs_corr_threshold),
            "moderate_corr_threshold": float(moderate_corr_threshold),
            "moderate_mean_abs_corr_threshold": float(moderate_mean_abs_corr_threshold),
        },
        "lead_results": lead_results,
        "next_direction": next_direction,
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed": False,
            "reason": "Round249 is a reference-dedup and stability gate only; portfolio validation remains blocked.",
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_event_contextual_underreaction_reference_dedup_markdown(result)
    return result


def write_event_contextual_underreaction_reference_dedup(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "event_contextual_underreaction_reference_dedup.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "event_contextual_underreaction_reference_dedup.md").write_text(
        render_event_contextual_underreaction_reference_dedup_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "event_contextual_underreaction_reference_correlations.csv",
        _flatten(result, "reference_correlations"),
        REFERENCE_OUTPUT_COLUMNS,
    )
    _write_csv(
        output_path / "event_contextual_underreaction_reference_yearly_ic.csv",
        _flatten(result, "yearly_ic"),
        PERIOD_OUTPUT_COLUMNS,
    )
    _write_csv(
        output_path / "event_contextual_underreaction_reference_monthly_ic.csv",
        _flatten(result, "monthly_ic"),
        MONTHLY_OUTPUT_COLUMNS,
    )
    _write_csv(
        output_path / "event_contextual_underreaction_reference_ic_observations.csv",
        _flatten(result, "ic_observations"),
        IC_OUTPUT_COLUMNS,
    )


def render_event_contextual_underreaction_reference_dedup_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Event Contextual Underreaction Reference Dedup Round249",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Leads tested: {summary.get('lead_count', 0)}",
        f"- Dedup pass: {summary.get('dedup_pass_count', 0)}",
        f"- Blocked leads: {summary.get('blocked_lead_count', 0)}",
        f"- Reference factors: {summary.get('reference_factor_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Next direction: `{result.get('next_direction')}`",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Lead Gates",
        "",
        "| Lead | H | IC | ICIR | IC+ | HighRedun | YearFail | Next | Blockers |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for lead in result.get("lead_results", []):
        lead_ic = lead.get("lead_ic_summary", {})
        summary_row = lead.get("summary", {})
        blockers = lead.get("gate", {}).get("blockers", [])
        lines.append(
            "| {lead} | {h} | {ic:.4f} | {icir:.3f} | {pos:.1%} | {redun} | {year_fail} | {next_dir} | {blockers} |".format(
                lead=lead.get("lead_factor_name", ""),
                h=int(lead.get("horizon", 0)),
                ic=float(lead_ic.get("mean_spearman_ic", 0.0)),
                icir=float(lead_ic.get("icir", 0.0)),
                pos=float(lead_ic.get("positive_ic_rate", 0.0)),
                redun=int(summary_row.get("reference_highly_redundant_count", 0)),
                year_fail=int(summary_row.get("yearly_failure_count", 0)),
                next_dir=lead.get("next_direction", ""),
                blockers=", ".join(blockers) if blockers else "none",
            )
        )
    lines.extend(["", "## Top Reference Correlations", ""])
    for lead in result.get("lead_results", []):
        lines.append(f"### {lead.get('lead_factor_name')} h{lead.get('horizon')}")
        lines.append("")
        lines.append("| Reference | Obs | Mean Abs | Max Abs | Class |")
        lines.append("|---|---:|---:|---:|---|")
        for row in lead.get("reference_correlations", [])[:8]:
            lines.append(
                "| {name} | {obs} | {mean_abs:.4f} | {max_abs:.4f} | {klass} |".format(
                    name=row.get("factor_name", ""),
                    obs=int(row.get("correlation_observations", 0)),
                    mean_abs=float(row.get("mean_abs_correlation", 0.0)),
                    max_abs=float(row.get("max_abs_correlation", 0.0)),
                    klass=row.get("redundancy_class", ""),
                )
            )
        lines.append("")
    lines.extend(
        [
            "## Gate Interpretation",
            "",
            "- This stage tests whether Round248 leads are distinct from raw event signals, context-only legs, and public price-volume references.",
            "- Passing this gate still does not allow portfolio promotion; it only allows walk-forward preflight.",
        ]
    )
    return "\n".join(lines) + "\n"


def _summarize_one_lead(
    frame: pd.DataFrame,
    labels: pd.DataFrame,
    reference_frame: pd.DataFrame,
    *,
    prescreen_report: dict[str, Any] | None,
    lead_factor_name: str,
    horizon: int,
    sample_every_n_dates: int,
    min_cross_section: int,
    min_ic_observations: int,
    min_reference_correlation_observations: int,
    high_corr_threshold: float,
    high_mean_abs_corr_threshold: float,
    moderate_corr_threshold: float,
    moderate_mean_abs_corr_threshold: float,
) -> dict[str, Any]:
    lead = frame[frame["factor_name"] == lead_factor_name].copy()
    sampled_lead = _sample_dates(lead, sample_every_n_dates=sample_every_n_dates)
    sampled_reference = _filter_dates(reference_frame, sampled_lead["date"].unique()) if not sampled_lead.empty else reference_frame
    ic_observations = _lead_ic_observations(
        lead,
        labels,
        lead_factor_name=lead_factor_name,
        horizon=horizon,
        min_cross_section=min_cross_section,
    )
    lead_ic_summary = _lead_ic_summary(ic_observations, min_ic_observations=min_ic_observations)
    yearly_ic = _period_ic(ic_observations, period="year")
    monthly_ic = _period_ic(ic_observations, period="month")
    reference_correlations = _reference_correlations(
        sampled_lead,
        sampled_reference,
        lead_factor_name=lead_factor_name,
        min_cross_section=min_cross_section,
        high_corr_threshold=high_corr_threshold,
        high_mean_abs_corr_threshold=high_mean_abs_corr_threshold,
        moderate_corr_threshold=moderate_corr_threshold,
        moderate_mean_abs_corr_threshold=moderate_mean_abs_corr_threshold,
    )
    reference_correlations = _apply_reference_observation_floor(
        reference_correlations,
        min_reference_correlation_observations=min_reference_correlation_observations,
    )
    lead_evidence = _lead_evidence(prescreen_report, lead_factor_name=lead_factor_name, horizon=horizon)
    blockers = _gate_blockers(
        lead,
        lead_evidence=lead_evidence,
        lead_ic_summary=lead_ic_summary,
        yearly_ic=yearly_ic,
        reference_correlations=reference_correlations,
        lead_factor_name=lead_factor_name,
    )
    next_direction = NEXT_WALK_FORWARD_PREFLIGHT_DIRECTION if not blockers else NEXT_HIBERNATE_OR_ORTHOGONALIZE_DIRECTION
    return {
        "lead_factor_name": lead_factor_name,
        "horizon": int(horizon),
        "lead_evidence": lead_evidence,
        "lead_ic_summary": lead_ic_summary,
        "summary": {
            "lead_rows": int(len(lead)),
            "reference_factor_count": int(reference_frame["factor_name"].nunique()) if not reference_frame.empty else 0,
            "reference_highly_redundant_count": int(
                sum(1 for row in reference_correlations if row["redundancy_class"] == "highly_redundant")
            ),
            "reference_moderately_redundant_count": int(
                sum(1 for row in reference_correlations if row["redundancy_class"] == "moderately_redundant")
            ),
            "yearly_failure_count": int(sum(1 for row in yearly_ic if row["failure"])),
            "monthly_failure_count": int(sum(1 for row in monthly_ic if row["failure"])),
            "promotion_allowed_candidates": 0,
        },
        "gate": {
            "blockers": blockers,
            "required_before": [
                "round248_prescreen_report_read",
                "raw_event_reference_dedup",
                "event_context_component_dedup",
                "public_price_volume_reference_dedup",
                "walk_forward_preflight_before_portfolio_grid",
            ],
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed": False,
            "reason": "Reference dedup is not portfolio validation.",
        },
        "next_direction": next_direction,
        "reference_correlations": reference_correlations,
        "yearly_ic": yearly_ic,
        "monthly_ic": monthly_ic,
        "ic_observations": ic_observations,
    }


def _context_reference_pieces(raw_context: pd.DataFrame) -> list[pd.DataFrame]:
    outputs = []
    context_specs = [
        (
            "event_repurchase_amount_to_mv_20",
            "context_repurchase_pre_signal_underreaction_20",
            "pre_signal_return_20",
            True,
        ),
        (
            "event_repurchase_amount_to_mv_20",
            "context_repurchase_quiet_volume_20",
            "amount_trend_5_20",
            True,
        ),
        (
            "event_holder_number_contraction_2q",
            "context_holder_pre_signal_underreaction_20",
            "pre_signal_return_20",
            True,
        ),
        (
            "event_holder_number_contraction_2q",
            "context_holder_low_vol_20",
            "realized_vol_20",
            True,
        ),
    ]
    for source_factor, output_factor, column, invert in context_specs:
        source = raw_context[raw_context["factor_name"] == source_factor].copy()
        if source.empty or column not in source:
            continue
        values = pd.to_numeric(source[column], errors="coerce")
        if invert:
            values = -values
        source["factor_value"] = _daily_zscore(source, values)
        source["factor_name"] = output_factor
        outputs.append(_reference_columns(source))
    return outputs


def _apply_reference_observation_floor(
    rows: list[dict[str, Any]],
    *,
    min_reference_correlation_observations: int,
) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        item = dict(row)
        if int(item.get("correlation_observations", 0)) < int(min_reference_correlation_observations):
            item["redundancy_class"] = "insufficient_overlap"
            item["blockers"] = ["insufficient_reference_overlap_with_lead"]
        output.append(item)
    return output


def _lead_requests(prescreen_report: dict[str, Any] | None, frame: pd.DataFrame) -> list[tuple[str, int]]:
    rows = []
    if prescreen_report:
        for row in prescreen_report.get("results", []):
            if row.get("research_lead"):
                rows.append((str(row.get("factor_name")), int(float(row.get("horizon", 0)))))
    if not rows and not frame.empty:
        rows = [(str(name), 20) for name in sorted(frame["factor_name"].unique())]
    seen = set()
    unique = []
    for item in rows:
        if item not in seen:
            unique.append(item)
            seen.add(item)
    return unique


def _lead_evidence(prescreen_report: dict[str, Any] | None, *, lead_factor_name: str, horizon: int) -> dict[str, Any]:
    rows = prescreen_report.get("results", []) if isinstance(prescreen_report, dict) else []
    match = next(
        (
            row
            for row in rows
            if row.get("factor_name") == lead_factor_name
            and int(float(row.get("horizon", horizon))) == int(horizon)
        ),
        {},
    )
    return {
        "prescreen_report_present": isinstance(prescreen_report, dict),
        "prescreen_row_found": bool(match),
        "prescreen_research_lead": bool(match.get("research_lead", False)),
        "prescreen_candidate_count": int((prescreen_report or {}).get("summary", {}).get("candidate_count", 0)),
        "prescreen_test_count": int((prescreen_report or {}).get("summary", {}).get("test_count", 0)),
    }


def _gate_blockers(
    lead_frame: pd.DataFrame,
    *,
    lead_evidence: dict[str, Any],
    lead_ic_summary: dict[str, Any],
    yearly_ic: list[dict[str, Any]],
    reference_correlations: list[dict[str, Any]],
    lead_factor_name: str,
) -> list[str]:
    blockers = []
    if lead_frame.empty:
        blockers.append("lead_factor_frame_empty")
    if not lead_evidence.get("prescreen_research_lead", False):
        blockers.append("round248_prescreen_lead_not_confirmed")
    if not lead_ic_summary.get("minimum_observation_gate_passed", False):
        blockers.append("lead_ic_observations_below_threshold")
    if any(row.get("redundancy_class") == "highly_redundant" for row in reference_correlations):
        blockers.append("lead_highly_redundant_with_reference_factor")
    if any(row.get("failure") for row in yearly_ic):
        blockers.append("yearly_ic_instability")
    years = [int(row.get("year")) for row in yearly_ic if str(row.get("year", "")).isdigit()]
    if "repurchase" in lead_factor_name and years and min(years) > 2015:
        blockers.append("repurchase_coverage_gap_before_2018_or_start_year")
    return blockers


def _price_volume_reference_specs(names: Sequence[str]) -> list[Any]:
    allowed = set(names)
    return [spec for spec in default_capacity_safe_price_volume_candidate_specs() if spec.factor_name in allowed]


def _reference_columns(frame: pd.DataFrame) -> pd.DataFrame:
    columns = ["date", "asset_id", "market", "factor_name", "factor_value", "amount", "adv20_amount"]
    output = frame.copy()
    for column in columns:
        if column not in output:
            output[column] = pd.NA
    return output[columns].dropna(subset=["date", "asset_id", "market", "factor_name", "factor_value"]).reset_index(drop=True)


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value", "amount", "adv20_amount"])


def _data_window(
    bars: pd.DataFrame,
    factor_frame: pd.DataFrame,
    reference_frame: pd.DataFrame,
    labels: pd.DataFrame,
    event_frames: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "bar_rows": int(len(bars)),
        "bar_assets": int(bars["asset_id"].nunique()) if not bars.empty else 0,
        "lead_factor_rows": int(len(factor_frame)),
        "reference_factor_rows": int(len(reference_frame)),
        "reference_factor_count": int(reference_frame["factor_name"].nunique()) if not reference_frame.empty else 0,
        "label_rows": int(len(labels)),
        "event_rows_by_endpoint": {endpoint: int(len(frame)) for endpoint, frame in event_frames.items()},
    }


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").min()
    return None if pd.isna(value) else pd.Timestamp(value).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").max()
    return None if pd.isna(value) else pd.Timestamp(value).date().isoformat()


def _flatten(result: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = []
    for lead in result.get("lead_results", []):
        for row in lead.get(key, []):
            rows.append({"lead_factor_name": lead.get("lead_factor_name"), "horizon": lead.get("horizon"), **row})
    return rows


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
