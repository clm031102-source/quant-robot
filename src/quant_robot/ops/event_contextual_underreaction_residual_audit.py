from __future__ import annotations

from datetime import date
import csv
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    load_capacity_safe_bars,
)
from quant_robot.ops.event_contextual_underreaction_prescreen import (
    compute_event_contextual_underreaction_factor_frame,
    default_event_contextual_underreaction_candidate_specs,
)
from quant_robot.ops.event_contextual_underreaction_reference_dedup import (
    DEFAULT_PRICE_VOLUME_REFERENCE_NAMES,
    compute_event_contextual_underreaction_reference_frame,
    _data_window,
)
from quant_robot.ops.event_factor_pit_ic_prescreen import _normalise_bars
from quant_robot.ops.event_factor_preregistration import SAFETY
from quant_robot.ops.market_residual_lead_exposure_dedup import (
    IC_OBSERVATION_COLUMNS,
    MONTHLY_IC_COLUMNS,
    YEARLY_IC_COLUMNS,
    _lead_ic_observations,
    _lead_ic_summary,
    _load_report,
    _normalise_factor_frame,
    _period_ic,
)
from quant_robot.ops.profitability_quality_preregistration import _sanitize
from quant_robot.research.labels import make_forward_returns


STAGE = "event_contextual_underreaction_residual_audit"
ROUND_CONTEXT = {
    "round": "round250",
    "source_audit": "docs/research/cn_stock_round249_event_contextual_underreaction_reference_dedup_2026-06-25.md",
    "purpose": "residualize_round248_leads_against_round249_high_redundancy_reference_clusters",
}
NEXT_RESIDUAL_WALK_FORWARD_PREFLIGHT_DIRECTION = (
    "round251_event_contextual_underreaction_residual_walk_forward_preflight"
)
NEXT_HIBERNATE_OR_ROTATE_DIRECTION = (
    "round251_hibernate_event_contextual_underreaction_after_residual_audit_failure"
)
RESIDUAL_DIAGNOSTIC_COLUMNS = [
    "lead_factor_name",
    "horizon",
    "residual_factor_name",
    "date",
    "cross_section",
    "reference_count",
    "reference_factor_names",
    "lead_std",
    "residual_std",
    "r_squared",
]
RESIDUAL_IC_OUTPUT_COLUMNS = ["lead_factor_name", *IC_OBSERVATION_COLUMNS]
RESIDUAL_PERIOD_OUTPUT_COLUMNS = ["lead_factor_name", "horizon", *YEARLY_IC_COLUMNS]
RESIDUAL_MONTHLY_OUTPUT_COLUMNS = ["lead_factor_name", "horizon", *MONTHLY_IC_COLUMNS]


def build_event_contextual_underreaction_residual_audit(
    *,
    event_frames: dict[str, pd.DataFrame],
    stock_basic: pd.DataFrame,
    bars_roots: Iterable[str | Path],
    reference_dedup_report: dict[str, Any] | str | Path,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    execution_lag: int = 1,
    pit_lag_trade_days: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_reference_correlation_observations: int = 5,
    min_residual_mean_ic: float = 0.02,
    min_residual_icir: float = 0.30,
    min_residual_t_stat: float = 2.0,
    min_positive_ic_rate: float = 0.55,
    min_residual_std: float = 1e-6,
    max_yearly_failure_count: int = 1,
    include_price_volume_references: bool = True,
    price_volume_reference_names: Sequence[str] = DEFAULT_PRICE_VOLUME_REFERENCE_NAMES,
) -> dict[str, Any]:
    report = _load_report(reference_dedup_report)
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
    horizons = tuple(sorted({int(row.get("horizon", 0)) for row in report.get("lead_results", [])}))
    if not horizons:
        horizons = (5, 20)
    labels = make_forward_returns(
        clean_bars[["date", "asset_id", "market", "adj_close"]],
        horizons=horizons,
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_event_contextual_underreaction_residual_audit(
        factor_frame,
        labels,
        reference_factor_frame=reference_frame,
        reference_dedup_report=report,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_reference_correlation_observations=min_reference_correlation_observations,
        min_residual_mean_ic=min_residual_mean_ic,
        min_residual_icir=min_residual_icir,
        min_residual_t_stat=min_residual_t_stat,
        min_positive_ic_rate=min_positive_ic_rate,
        min_residual_std=min_residual_std,
        max_yearly_failure_count=max_yearly_failure_count,
    )
    result["data_window"] = _data_window(clean_bars, factor_frame, reference_frame, labels, event_frames)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_residual_walk_forward_and_oos_clearance_only",
    }
    result["pit_policy"] = {
        "pit_lag_trade_days": int(pit_lag_trade_days),
        "same_day_event_trading_allowed": False,
        "execution_lag": int(execution_lag),
    }
    result["reference_policy"] = {
        "include_price_volume_references": bool(include_price_volume_references),
        "price_volume_reference_names": list(price_volume_reference_names),
        "reference_cluster_source": "round249_highly_redundant_reference_correlations",
    }
    result["markdown"] = render_event_contextual_underreaction_residual_audit_markdown(result)
    return result


def summarize_event_contextual_underreaction_residual_audit(
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    reference_factor_frame: pd.DataFrame | None = None,
    reference_dedup_report: dict[str, Any] | str | Path | None = None,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_reference_correlation_observations: int = 5,
    min_residual_mean_ic: float = 0.02,
    min_residual_icir: float = 0.30,
    min_residual_t_stat: float = 2.0,
    min_positive_ic_rate: float = 0.55,
    min_residual_std: float = 1e-6,
    max_yearly_failure_count: int = 1,
) -> dict[str, Any]:
    frame = _normalise_factor_frame(factor_frame)
    reference_frame = _normalise_factor_frame(reference_factor_frame if reference_factor_frame is not None else pd.DataFrame())
    report = _load_report(reference_dedup_report) if reference_dedup_report is not None else {}
    lead_results = [
        _summarize_one_lead(
            frame,
            labels,
            reference_frame,
            reference_row=reference_row,
            min_cross_section=min_cross_section,
            min_ic_observations=min_ic_observations,
            min_reference_correlation_observations=min_reference_correlation_observations,
            min_residual_mean_ic=min_residual_mean_ic,
            min_residual_icir=min_residual_icir,
            min_residual_t_stat=min_residual_t_stat,
            min_positive_ic_rate=min_positive_ic_rate,
            min_residual_std=min_residual_std,
            max_yearly_failure_count=max_yearly_failure_count,
        )
        for reference_row in _lead_requests(report, frame)
    ]
    residual_pass_count = sum(1 for row in lead_results if not row["gate"]["blockers"])
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "round_context": ROUND_CONTEXT,
        "summary": {
            "lead_count": int(len(lead_results)),
            "residual_pass_count": int(residual_pass_count),
            "blocked_lead_count": int(len(lead_results) - residual_pass_count),
            "promotion_allowed_candidates": 0,
            "portfolio_grid_allowed_candidates": 0,
        },
        "thresholds": {
            "min_cross_section": int(min_cross_section),
            "min_ic_observations": int(min_ic_observations),
            "min_reference_correlation_observations": int(min_reference_correlation_observations),
            "min_residual_mean_ic": float(min_residual_mean_ic),
            "min_residual_icir": float(min_residual_icir),
            "min_residual_t_stat": float(min_residual_t_stat),
            "min_positive_ic_rate": float(min_positive_ic_rate),
            "min_residual_std": float(min_residual_std),
            "max_yearly_failure_count": int(max_yearly_failure_count),
        },
        "lead_results": lead_results,
        "next_direction": (
            NEXT_RESIDUAL_WALK_FORWARD_PREFLIGHT_DIRECTION
            if residual_pass_count
            else NEXT_HIBERNATE_OR_ROTATE_DIRECTION
        ),
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed": False,
            "manual_live_allowed": False,
            "reason": "Round250 is an incremental residual audit only; promotion requires pre-registered walk-forward, cost, capacity, and regime validation.",
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_event_contextual_underreaction_residual_audit_markdown(result)
    return result


def residualize_event_contextual_lead_frame(
    lead_frame: pd.DataFrame,
    reference_frame: pd.DataFrame,
    *,
    lead_factor_name: str,
    residual_factor_name: str,
    reference_factor_names: Sequence[str],
    min_cross_section: int = 30,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    lead = _normalise_factor_frame(lead_frame)
    refs = _normalise_factor_frame(reference_frame)
    selected = list(dict.fromkeys(str(name) for name in reference_factor_names))
    if lead.empty or not selected:
        return _empty_residual_frame(), []
    lead = lead[lead["factor_name"] == lead_factor_name].copy()
    refs = refs[refs["factor_name"].isin(selected)].copy()
    if lead.empty or refs.empty:
        return _empty_residual_frame(), []
    lead_base_columns = [
        column
        for column in ["date", "asset_id", "market", "amount", "adv20_amount"]
        if column in lead.columns
    ]
    lead_values = lead[lead_base_columns + ["factor_value"]].rename(columns={"factor_value": "lead_value"})
    ref_wide = refs.pivot_table(
        index=["date", "asset_id", "market"],
        columns="factor_name",
        values="factor_value",
        aggfunc="mean",
    ).reset_index()
    merged = lead_values.merge(ref_wide, on=["date", "asset_id", "market"], how="inner")
    rows: list[pd.DataFrame] = []
    diagnostics: list[dict[str, Any]] = []
    for signal_date, group in merged.groupby("date", sort=True):
        valid = group.dropna(subset=["lead_value", *selected]).copy()
        if len(valid) < min_cross_section:
            continue
        y = pd.to_numeric(valid["lead_value"], errors="coerce").to_numpy(dtype=float)
        x = valid[selected].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
        finite = np.isfinite(y) & np.isfinite(x).all(axis=1)
        if int(finite.sum()) < min_cross_section:
            continue
        valid = valid.loc[finite].copy()
        y = y[finite]
        x = x[finite]
        design = np.column_stack([np.ones(len(x)), x])
        beta, *_ = np.linalg.lstsq(design, y, rcond=None)
        fitted = design @ beta
        residual = y - fitted
        ss_total = float(np.square(y - y.mean()).sum())
        ss_residual = float(np.square(residual).sum())
        r_squared = 1.0 - ss_residual / ss_total if ss_total > 1e-12 else 0.0
        output = valid[lead_base_columns].copy()
        output["factor_name"] = residual_factor_name
        output["factor_value"] = residual
        rows.append(output)
        diagnostics.append(
            {
                "date": pd.Timestamp(signal_date).date().isoformat(),
                "cross_section": int(len(valid)),
                "lead_std": float(np.std(y, ddof=0)),
                "residual_std": float(np.std(residual, ddof=0)),
                "r_squared": float(r_squared),
                "reference_count": int(len(selected)),
                "reference_factor_names": list(selected),
            }
        )
    if not rows:
        return _empty_residual_frame(), diagnostics
    residual_frame = (
        pd.concat(rows, ignore_index=True)
        .dropna(subset=["date", "asset_id", "market", "factor_name", "factor_value"])
        .sort_values(["factor_name", "date", "asset_id"])
        .reset_index(drop=True)
    )
    return residual_frame, diagnostics


def write_event_contextual_underreaction_residual_audit(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "event_contextual_underreaction_residual_audit.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "event_contextual_underreaction_residual_audit.md").write_text(
        render_event_contextual_underreaction_residual_audit_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "event_contextual_underreaction_residual_ic_observations.csv",
        _flatten(result, "residual_ic_observations"),
        RESIDUAL_IC_OUTPUT_COLUMNS,
    )
    _write_csv(
        output_path / "event_contextual_underreaction_residual_yearly_ic.csv",
        _flatten(result, "residual_yearly_ic"),
        RESIDUAL_PERIOD_OUTPUT_COLUMNS,
    )
    _write_csv(
        output_path / "event_contextual_underreaction_residual_monthly_ic.csv",
        _flatten(result, "residual_monthly_ic"),
        RESIDUAL_MONTHLY_OUTPUT_COLUMNS,
    )
    _write_csv(
        output_path / "event_contextual_underreaction_residual_diagnostics.csv",
        _flatten(result, "residual_diagnostics"),
        RESIDUAL_DIAGNOSTIC_COLUMNS,
    )


def render_event_contextual_underreaction_residual_audit_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Event Contextual Underreaction Residual Audit Round250",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Leads tested: {summary.get('lead_count', 0)}",
        f"- Residual pass: {summary.get('residual_pass_count', 0)}",
        f"- Blocked leads: {summary.get('blocked_lead_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Next direction: `{result.get('next_direction')}`",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Lead Residual Gates",
        "",
        "| Lead | H | Refs | R2 | Resid IC | ICIR | t | IC+ | YearFail | Next | Blockers |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for lead in result.get("lead_results", []):
        ic = lead.get("residual_ic_summary", {})
        diag = lead.get("residual_diagnostics_summary", {})
        blockers = lead.get("gate", {}).get("blockers", [])
        lines.append(
            "| {lead} | {h} | {refs} | {r2:.4f} | {ic_mean:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {year_fail} | {next_dir} | {blockers} |".format(
                lead=lead.get("lead_factor_name", ""),
                h=int(lead.get("horizon", 0)),
                refs=len(lead.get("reference_factor_names", [])),
                r2=float(diag.get("median_r_squared", 0.0)),
                ic_mean=float(ic.get("mean_spearman_ic", 0.0)),
                icir=float(ic.get("icir", 0.0)),
                t=float(ic.get("ic_t_stat", 0.0)),
                pos=float(ic.get("positive_ic_rate", 0.0)),
                year_fail=int(lead.get("summary", {}).get("residual_yearly_failure_count", 0)),
                next_dir=lead.get("next_direction", ""),
                blockers=", ".join(blockers) if blockers else "none",
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This stage removes the raw event leg, context-only leg, and public price-volume reference cluster identified by Round249.",
            "- A residual pass only allows the next walk-forward preflight; it is not a paper-ready or live-ready signal.",
            "- Portfolio grids remain blocked until walk-forward, cost, capacity, and regime gates pass.",
            "",
        ]
    )
    return "\n".join(lines)


def _summarize_one_lead(
    frame: pd.DataFrame,
    labels: pd.DataFrame,
    reference_frame: pd.DataFrame,
    *,
    reference_row: dict[str, Any],
    min_cross_section: int,
    min_ic_observations: int,
    min_reference_correlation_observations: int,
    min_residual_mean_ic: float,
    min_residual_icir: float,
    min_residual_t_stat: float,
    min_positive_ic_rate: float,
    min_residual_std: float,
    max_yearly_failure_count: int,
) -> dict[str, Any]:
    lead_factor_name = str(reference_row.get("lead_factor_name", ""))
    horizon = int(float(reference_row.get("horizon", 20)))
    residual_factor_name = f"{lead_factor_name}_round249_reference_residual"
    requested_reference_names = _high_reference_names(
        reference_row,
        min_reference_correlation_observations=min_reference_correlation_observations,
    )
    available_reference_names = [
        name
        for name in requested_reference_names
        if not reference_frame.empty and name in set(reference_frame["factor_name"].unique())
    ]
    missing_reference_names = [name for name in requested_reference_names if name not in set(available_reference_names)]
    lead = frame[frame["factor_name"] == lead_factor_name].copy()
    residual_frame, diagnostics = residualize_event_contextual_lead_frame(
        lead,
        reference_frame,
        lead_factor_name=lead_factor_name,
        residual_factor_name=residual_factor_name,
        reference_factor_names=available_reference_names,
        min_cross_section=min_cross_section,
    )
    diagnostics = [
        {
            "lead_factor_name": lead_factor_name,
            "horizon": horizon,
            "residual_factor_name": residual_factor_name,
            **row,
        }
        for row in diagnostics
    ]
    residual_for_ic = _filter_low_variance_residual_dates(
        residual_frame,
        diagnostics,
        min_residual_std=min_residual_std,
    )
    residual_ic_observations = _lead_ic_observations(
        residual_for_ic,
        labels,
        lead_factor_name=residual_factor_name,
        horizon=horizon,
        min_cross_section=min_cross_section,
    )
    residual_ic_summary = _lead_ic_summary(
        residual_ic_observations,
        min_ic_observations=min_ic_observations,
    )
    residual_yearly_ic = _period_ic(residual_ic_observations, period="year")
    residual_monthly_ic = _period_ic(residual_ic_observations, period="month")
    diagnostics_summary = _residual_diagnostics_summary(diagnostics)
    blockers = _gate_blockers(
        lead,
        residual_frame=residual_frame,
        residual_ic_summary=residual_ic_summary,
        residual_yearly_ic=residual_yearly_ic,
        diagnostics_summary=diagnostics_summary,
        requested_reference_names=requested_reference_names,
        available_reference_names=available_reference_names,
        missing_reference_names=missing_reference_names,
        min_residual_mean_ic=min_residual_mean_ic,
        min_residual_icir=min_residual_icir,
        min_residual_t_stat=min_residual_t_stat,
        min_positive_ic_rate=min_positive_ic_rate,
        min_residual_std=min_residual_std,
        max_yearly_failure_count=max_yearly_failure_count,
    )
    return {
        "lead_factor_name": lead_factor_name,
        "horizon": horizon,
        "residual_factor_name": residual_factor_name,
        "reference_factor_names": available_reference_names,
        "requested_reference_factor_names": requested_reference_names,
        "missing_reference_factor_names": missing_reference_names,
        "summary": {
            "lead_rows": int(len(lead)),
            "residual_rows": int(len(residual_frame)),
            "residual_date_count": int(residual_frame["date"].nunique()) if not residual_frame.empty else 0,
            "residual_yearly_failure_count": int(sum(1 for row in residual_yearly_ic if row.get("failure"))),
            "residual_monthly_failure_count": int(sum(1 for row in residual_monthly_ic if row.get("failure"))),
            "promotion_allowed_candidates": 0,
        },
        "residual_diagnostics_summary": diagnostics_summary,
        "residual_ic_summary": residual_ic_summary,
        "gate": {
            "blockers": blockers,
            "required_before": [
                "round249_reference_dedup_report_read",
                "high_redundancy_reference_cluster_residualized",
                "independent_residual_ic_gate",
                "walk_forward_preflight_before_portfolio_grid",
            ],
            "drawdown_policy": "Drawdown tolerance cannot waive redundancy, residual IC, overfit, cost, capacity, or walk-forward gates.",
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed": False,
            "reason": "Residual audit is not portfolio validation.",
        },
        "next_direction": (
            NEXT_RESIDUAL_WALK_FORWARD_PREFLIGHT_DIRECTION
            if not blockers
            else NEXT_HIBERNATE_OR_ROTATE_DIRECTION
        ),
        "residual_yearly_ic": residual_yearly_ic,
        "residual_monthly_ic": residual_monthly_ic,
        "residual_ic_observations": residual_ic_observations,
        "residual_diagnostics": diagnostics,
    }


def _lead_requests(report: dict[str, Any], frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows = [dict(row) for row in report.get("lead_results", [])]
    if not rows and not frame.empty:
        rows = [{"lead_factor_name": str(name), "horizon": 20, "reference_correlations": []} for name in sorted(frame["factor_name"].unique())]
    seen = set()
    unique = []
    for row in rows:
        key = (str(row.get("lead_factor_name", "")), int(float(row.get("horizon", 20))))
        if key not in seen:
            unique.append(row)
            seen.add(key)
    return unique


def _high_reference_names(
    reference_row: dict[str, Any],
    *,
    min_reference_correlation_observations: int,
) -> list[str]:
    names = []
    for row in reference_row.get("reference_correlations", []):
        if row.get("redundancy_class") != "highly_redundant":
            continue
        if int(float(row.get("correlation_observations", 0))) < min_reference_correlation_observations:
            continue
        name = str(row.get("factor_name", "")).strip()
        if name:
            names.append(name)
    return list(dict.fromkeys(names))


def _gate_blockers(
    lead_frame: pd.DataFrame,
    *,
    residual_frame: pd.DataFrame,
    residual_ic_summary: dict[str, Any],
    residual_yearly_ic: list[dict[str, Any]],
    diagnostics_summary: dict[str, Any],
    requested_reference_names: Sequence[str],
    available_reference_names: Sequence[str],
    missing_reference_names: Sequence[str],
    min_residual_mean_ic: float,
    min_residual_icir: float,
    min_residual_t_stat: float,
    min_positive_ic_rate: float,
    min_residual_std: float,
    max_yearly_failure_count: int,
) -> list[str]:
    blockers: list[str] = []
    if lead_frame.empty:
        blockers.append("lead_factor_frame_empty")
    if not requested_reference_names:
        blockers.append("round249_high_reference_cluster_missing")
    if not available_reference_names:
        blockers.append("high_reference_factor_values_missing")
    elif missing_reference_names:
        blockers.append("some_high_reference_factor_values_missing")
    if residual_frame.empty:
        blockers.append("residual_factor_frame_empty")
    if diagnostics_summary.get("median_residual_std", 0.0) <= min_residual_std:
        blockers.append("residual_signal_variance_too_low")
    if not residual_ic_summary.get("minimum_observation_gate_passed", False):
        blockers.append("residual_ic_observations_below_threshold")
    if residual_ic_summary.get("mean_spearman_ic", 0.0) < min_residual_mean_ic:
        blockers.append("residual_mean_ic_below_threshold")
    if residual_ic_summary.get("icir", 0.0) < min_residual_icir:
        blockers.append("residual_icir_below_threshold")
    if residual_ic_summary.get("ic_t_stat", 0.0) < min_residual_t_stat:
        blockers.append("residual_t_stat_below_threshold")
    if residual_ic_summary.get("positive_ic_rate", 0.0) < min_positive_ic_rate:
        blockers.append("residual_positive_ic_rate_below_threshold")
    yearly_failure_count = sum(1 for row in residual_yearly_ic if row.get("failure"))
    if yearly_failure_count > max_yearly_failure_count:
        blockers.append("residual_yearly_ic_instability")
    return blockers


def _filter_low_variance_residual_dates(
    residual_frame: pd.DataFrame,
    diagnostics: Sequence[dict[str, Any]],
    *,
    min_residual_std: float,
) -> pd.DataFrame:
    if residual_frame.empty:
        return residual_frame
    keep_dates = {
        pd.Timestamp(row["date"])
        for row in diagnostics
        if float(row.get("residual_std", 0.0)) > min_residual_std
    }
    if not keep_dates:
        return residual_frame.iloc[0:0].copy()
    return residual_frame[pd.to_datetime(residual_frame["date"]).isin(keep_dates)].reset_index(drop=True)


def _residual_diagnostics_summary(diagnostics: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not diagnostics:
        return {
            "date_count": 0,
            "median_r_squared": 0.0,
            "mean_r_squared": 0.0,
            "median_residual_std": 0.0,
            "mean_residual_std": 0.0,
            "median_cross_section": 0.0,
        }
    frame = pd.DataFrame(diagnostics)
    return {
        "date_count": int(len(frame)),
        "median_r_squared": float(pd.to_numeric(frame["r_squared"], errors="coerce").median()),
        "mean_r_squared": float(pd.to_numeric(frame["r_squared"], errors="coerce").mean()),
        "median_residual_std": float(pd.to_numeric(frame["residual_std"], errors="coerce").median()),
        "mean_residual_std": float(pd.to_numeric(frame["residual_std"], errors="coerce").mean()),
        "median_cross_section": float(pd.to_numeric(frame["cross_section"], errors="coerce").median()),
    }


def _empty_residual_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])


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
