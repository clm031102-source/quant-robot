from __future__ import annotations

from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    load_capacity_safe_bars,
)
from quant_robot.ops.daily_basic_non_price_public_carry_prescreen import (
    _capacity_frame,
    _feature_frame as _daily_basic_feature_frame,
    load_daily_basic_non_price_public_carry_inputs,
)
from quant_robot.ops.event_factor_pit_ic_prescreen import compute_event_factor_frame
from quant_robot.ops.event_factor_preregistration import SAFETY, default_event_factor_candidate_specs
from quant_robot.ops.market_residual_lead_exposure_dedup import (
    IC_OBSERVATION_COLUMNS,
    MONTHLY_IC_COLUMNS,
    REFERENCE_CORRELATION_COLUMNS,
    YEARLY_IC_COLUMNS,
    _filter_dates,
    _lead_ic_observations,
    _lead_ic_summary,
    _load_report,
    _period_ic,
    _reference_correlations,
    _sample_dates,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "event_factor_neutral_lead_dedup"
DEFAULT_LEAD_FACTOR_NAME = "event_dividend_cash_yield_announced_1y"
DEFAULT_HORIZON = 20
ROUND147_SOURCE_REPORT = "docs/research/cn_stock_event_factor_pit_ic_prescreen_round147_2026-06-22.md"
NEXT_PORTFOLIO_PREFLIGHT_DIRECTION = "round149_event_dividend_portfolio_conversion_preflight"
NEXT_INCREMENTAL_RESIDUAL_DIRECTION = "round149_event_dividend_incremental_residual_prescreen"
NEXT_STABILITY_AUDIT_DIRECTION = "round149_event_dividend_residual_stability_audit"
ROTATE_AFTER_DEDUP_FAILURE_DIRECTION = "round149_event_factor_family_rotation_after_dedup_failure"
DEFAULT_RESIDUAL_EXPOSURES = (
    "daily_basic_dv_ttm",
    "daily_basic_dv_ratio",
    "daily_basic_inv_pb",
    "daily_basic_inv_ps_ttm",
    "daily_basic_log_circ_mv",
    "daily_basic_log_total_mv",
    "log_adv20_amount",
)
PUBLIC_REFERENCE_EXPOSURES = {
    "daily_basic_dv_ttm",
    "daily_basic_dv_ratio",
    "daily_basic_inv_pb",
    "daily_basic_inv_pe_ttm",
    "daily_basic_inv_ps_ttm",
    "daily_basic_log_circ_mv",
    "daily_basic_log_total_mv",
    "daily_basic_volume_ratio_z_20",
    "log_adv20_amount",
}
SOFT_STABILITY_BLOCKERS = {
    "raw_yearly_ic_instability",
    "residual_yearly_ic_instability",
    "twenty_fifteen_regime_failure_unexplained",
}
EXPOSURE_CORRELATION_COLUMNS = [
    "exposure_name",
    "exposure_role",
    "correlation_observations",
    "mean_correlation",
    "mean_abs_correlation",
    "median_abs_correlation",
    "max_abs_correlation",
    "positive_correlation_rate",
    "median_cross_section",
    "unique_dates",
    "exposure_class",
    "blockers",
]


def build_event_factor_neutral_lead_dedup(
    *,
    event_frames: dict[str, pd.DataFrame],
    stock_basic: pd.DataFrame,
    bars_roots: Iterable[str | Path],
    daily_basic_roots: Iterable[str | Path],
    prescreen_report: dict[str, Any] | str | Path,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    horizon: int = DEFAULT_HORIZON,
    execution_lag: int = 1,
    pit_lag_trade_days: int = 1,
    sample_every_n_dates: int = 5,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
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
    lead_specs = _lead_specs(lead_factor_name)
    lead_frame = compute_event_factor_frame(
        event_frames,
        bars,
        stock_basic,
        candidate_specs=lead_specs,
        pit_lag_trade_days=pit_lag_trade_days,
    )
    lead_frame = _filter_analysis_window(
        lead_frame,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    exposure_frame = build_event_dividend_public_exposure_frame(daily_basic, bars)
    reference_frame = build_event_dividend_reference_factor_frame(exposure_frame)
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=(horizon,),
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_event_factor_neutral_lead_dedup(
        lead_frame,
        labels,
        reference_factor_frame=reference_frame,
        exposure_frame=exposure_frame,
        prescreen_report=report,
        lead_factor_name=lead_factor_name,
        horizon=horizon,
        sample_every_n_dates=sample_every_n_dates,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
    )
    result["data_window"] = _data_window(bars, lead_frame, reference_frame, exposure_frame, labels)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_and_residual_dedup_clearance_only",
    }
    result["pit_policy"] = {
        "pit_lag_trade_days": int(pit_lag_trade_days),
        "same_day_event_trading_allowed": False,
        "execution_lag": int(execution_lag),
    }
    result["sampling_policy"] = {
        "sample_every_n_dates": sample_every_n_dates,
        "sampling_used_for_correlations_only": True,
        "raw_and_residual_ic_use_all_dates": True,
    }
    result["markdown"] = render_event_factor_neutral_lead_dedup_markdown(result)
    return result


def summarize_event_factor_neutral_lead_dedup(
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    reference_factor_frame: pd.DataFrame | None = None,
    exposure_frame: pd.DataFrame | None = None,
    prescreen_report: dict[str, Any] | None = None,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    horizon: int = DEFAULT_HORIZON,
    sample_every_n_dates: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_residual_mean_ic: float = 0.02,
    min_residual_icir: float = 0.20,
    min_residual_positive_ic_rate: float = 0.55,
    residual_exposure_names: Sequence[str] = DEFAULT_RESIDUAL_EXPOSURES,
    high_corr_threshold: float = 0.85,
    high_mean_abs_corr_threshold: float = 0.70,
    moderate_corr_threshold: float = 0.70,
    moderate_mean_abs_corr_threshold: float = 0.50,
    high_exposure_corr_threshold: float = 0.85,
    high_exposure_mean_abs_corr_threshold: float = 0.60,
) -> dict[str, Any]:
    lead = _normalise_factor_frame(factor_frame)
    lead = lead[lead["factor_name"] == lead_factor_name].reset_index(drop=True)
    reference = _normalise_factor_frame(reference_factor_frame if reference_factor_frame is not None else pd.DataFrame())
    exposures = _normalise_exposure_frame(exposure_frame if exposure_frame is not None else pd.DataFrame())
    lead_with_exposures = _merge_lead_exposures(lead, exposures)
    sampled_lead = _sample_dates(lead_with_exposures, sample_every_n_dates=sample_every_n_dates)
    sampled_reference = _filter_dates(reference, sampled_lead["date"].unique()) if not sampled_lead.empty else reference
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
    exposure_correlations = _event_exposure_correlations(
        sampled_lead,
        min_cross_section=min_cross_section,
        high_exposure_corr_threshold=high_exposure_corr_threshold,
        high_exposure_mean_abs_corr_threshold=high_exposure_mean_abs_corr_threshold,
    )
    raw_ic_observations = _lead_ic_observations(
        lead,
        labels,
        lead_factor_name=lead_factor_name,
        horizon=horizon,
        min_cross_section=min_cross_section,
    )
    raw_ic_summary = _lead_ic_summary(raw_ic_observations, min_ic_observations=min_ic_observations)
    raw_yearly_ic = _period_ic(raw_ic_observations, period="year")
    raw_monthly_ic = _period_ic(raw_ic_observations, period="month")
    residual_factor_name = f"{lead_factor_name}_public_exposure_residual"
    residual_frame = residualize_event_lead(
        lead_with_exposures,
        exposure_names=residual_exposure_names,
        residual_factor_name=residual_factor_name,
        min_cross_section=min_cross_section,
    )
    residual_ic_observations = _lead_ic_observations(
        residual_frame,
        labels,
        lead_factor_name=residual_factor_name,
        horizon=horizon,
        min_cross_section=min_cross_section,
    )
    residual_ic_summary = _lead_ic_summary(residual_ic_observations, min_ic_observations=min_ic_observations)
    residual_yearly_ic = _period_ic(residual_ic_observations, period="year")
    residual_monthly_ic = _period_ic(residual_ic_observations, period="month")
    prescreen_evidence = _prescreen_evidence(prescreen_report, lead_factor_name=lead_factor_name, horizon=horizon)
    blockers = _gate_blockers(
        lead,
        prescreen_evidence=prescreen_evidence,
        raw_ic_summary=raw_ic_summary,
        residual_ic_summary=residual_ic_summary,
        raw_yearly_ic=raw_yearly_ic,
        residual_yearly_ic=residual_yearly_ic,
        reference_correlations=reference_correlations,
        exposure_correlations=exposure_correlations,
        min_residual_mean_ic=min_residual_mean_ic,
        min_residual_icir=min_residual_icir,
        min_residual_positive_ic_rate=min_residual_positive_ic_rate,
    )
    portfolio_conversion_candidate = not blockers
    next_direction = _next_direction(
        blockers,
        residual_ic_summary=residual_ic_summary,
        min_residual_mean_ic=min_residual_mean_ic,
        min_residual_icir=min_residual_icir,
        min_residual_positive_ic_rate=min_residual_positive_ic_rate,
    )
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "lead_factor_name": lead_factor_name,
        "horizon": int(horizon),
        "source_context": {
            "source_prescreen": ROUND147_SOURCE_REPORT,
            "round147_lead_requires_public_reference_and_residual_dedup_before_portfolio_grid": True,
        },
        "lead_evidence": prescreen_evidence,
        "raw_ic_summary": raw_ic_summary,
        "residual_ic_summary": residual_ic_summary,
        "summary": {
            "lead_rows": int(len(lead)),
            "reference_factor_count": int(reference["factor_name"].nunique()) if not reference.empty else 0,
            "reference_highly_redundant_count": int(
                sum(1 for row in reference_correlations if row.get("redundancy_class") == "highly_redundant")
            ),
            "public_exposure_high_count": int(
                sum(row.get("exposure_class") == "high_exposure" for row in exposure_correlations)
            ),
            "raw_yearly_failure_count": int(sum(row.get("failure") for row in raw_yearly_ic)),
            "residual_yearly_failure_count": int(sum(row.get("failure") for row in residual_yearly_ic)),
            "promotion_allowed_candidates": 0,
            "portfolio_conversion_candidates": int(portfolio_conversion_candidate),
        },
        "thresholds": {
            "min_cross_section": min_cross_section,
            "min_ic_observations": min_ic_observations,
            "min_residual_mean_ic": min_residual_mean_ic,
            "min_residual_icir": min_residual_icir,
            "min_residual_positive_ic_rate": min_residual_positive_ic_rate,
            "high_corr_threshold": high_corr_threshold,
            "high_mean_abs_corr_threshold": high_mean_abs_corr_threshold,
            "moderate_corr_threshold": moderate_corr_threshold,
            "moderate_mean_abs_corr_threshold": moderate_mean_abs_corr_threshold,
            "high_exposure_corr_threshold": high_exposure_corr_threshold,
            "high_exposure_mean_abs_corr_threshold": high_exposure_mean_abs_corr_threshold,
            "residual_exposure_names": list(residual_exposure_names),
        },
        "gate": {
            "blockers": blockers,
            "required_before": [
                "round147_event_pit_ic_prescreen_read",
                "round147_single_event_research_lead_confirmed",
                "event_dividend_public_reference_correlation_gate",
                "event_dividend_public_exposure_residual_ic_gate",
                "no_event_factor_portfolio_grid_before_dedup",
            ],
            "drawdown_policy": (
                "Drawdown tolerance can relax later portfolio MaxDD interpretation, but it cannot waive "
                "public-reference redundancy, residual IC, cost, capacity, PIT, or walk-forward gates."
            ),
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_conversion_candidate": portfolio_conversion_candidate,
            "portfolio_grid_allowed": portfolio_conversion_candidate,
            "reason": (
                "Round148 is a public-reference de-duplication and residual-alpha preflight. Promotion still "
                "requires costed portfolio conversion, walk-forward, regime, capacity, and final-holdout gates."
            ),
        },
        "next_direction": next_direction,
        "reference_correlations": reference_correlations,
        "exposure_correlations": exposure_correlations,
        "raw_yearly_ic": raw_yearly_ic,
        "raw_monthly_ic": raw_monthly_ic,
        "raw_ic_observations": raw_ic_observations,
        "residual_yearly_ic": residual_yearly_ic,
        "residual_monthly_ic": residual_monthly_ic,
        "residual_ic_observations": residual_ic_observations,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_event_factor_neutral_lead_dedup_markdown(result)
    return result


def build_event_dividend_public_exposure_frame(daily_basic: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    features = _daily_basic_feature_frame(daily_basic)
    if features.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market"])
    exposure = features[
        [
            "date",
            "asset_id",
            "market",
            "dv_ttm",
            "dv_ratio",
            "inv_pb",
            "inv_pe_ttm",
            "inv_ps_ttm",
            "log_circ_mv",
            "log_total_mv",
            "volume_ratio_z_20",
        ]
    ].rename(
        columns={
            "dv_ttm": "daily_basic_dv_ttm",
            "dv_ratio": "daily_basic_dv_ratio",
            "inv_pb": "daily_basic_inv_pb",
            "inv_pe_ttm": "daily_basic_inv_pe_ttm",
            "inv_ps_ttm": "daily_basic_inv_ps_ttm",
            "log_circ_mv": "daily_basic_log_circ_mv",
            "log_total_mv": "daily_basic_log_total_mv",
            "volume_ratio_z_20": "daily_basic_volume_ratio_z_20",
        }
    )
    capacity = _capacity_frame(bars)
    if not capacity.empty:
        capacity = capacity.copy()
        capacity["log_adv20_amount"] = np.log(
            pd.to_numeric(capacity["adv20_amount"], errors="coerce").where(capacity["adv20_amount"] > 0)
        )
        exposure = exposure.merge(
            capacity[["date", "asset_id", "market", "amount", "adv20_amount", "log_adv20_amount"]],
            on=["date", "asset_id", "market"],
            how="left",
            validate="many_to_one",
        )
    return exposure.replace([float("inf"), float("-inf")], pd.NA)


def build_event_dividend_reference_factor_frame(exposure_frame: pd.DataFrame) -> pd.DataFrame:
    exposures = _normalise_exposure_frame(exposure_frame)
    if exposures.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])
    rows = []
    base_columns = ["date", "asset_id", "market"]
    for exposure_name in sorted(PUBLIC_REFERENCE_EXPOSURES):
        if exposure_name not in exposures:
            continue
        frame = exposures[base_columns].copy()
        frame["factor_name"] = exposure_name
        frame["factor_value"] = pd.to_numeric(exposures[exposure_name], errors="coerce")
        if "amount" in exposures:
            frame["amount"] = exposures["amount"]
        if "adv20_amount" in exposures:
            frame["adv20_amount"] = exposures["adv20_amount"]
        rows.append(frame.dropna(subset=["factor_value"]))
    if not rows:
        return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def residualize_event_lead(
    lead_frame: pd.DataFrame,
    *,
    exposure_names: Sequence[str] = DEFAULT_RESIDUAL_EXPOSURES,
    residual_factor_name: str,
    min_cross_section: int = 30,
) -> pd.DataFrame:
    if lead_frame.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])
    frame = lead_frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    exposure_names = [name for name in exposure_names if name in frame.columns]
    rows = []
    for _, group in frame.groupby("date", sort=True):
        output = group[["date", "asset_id", "market"]].copy()
        output["factor_name"] = residual_factor_name
        output["factor_value"] = np.nan
        if not exposure_names:
            output["factor_value"] = pd.to_numeric(group["factor_value"], errors="coerce")
            rows.append(output)
            continue
        clean = group[["factor_value", *exposure_names]].apply(pd.to_numeric, errors="coerce").dropna()
        if len(clean) < max(3, min_cross_section):
            rows.append(output)
            continue
        y = clean["factor_value"].to_numpy(dtype=float)
        x = clean[list(exposure_names)].to_numpy(dtype=float)
        x = np.column_stack([np.ones(len(x)), x])
        try:
            beta = np.linalg.lstsq(x, y, rcond=None)[0]
        except np.linalg.LinAlgError:
            rows.append(output)
            continue
        residual = y - x @ beta
        if float(np.nanstd(residual)) <= 1e-12:
            rows.append(output)
            continue
        output.loc[clean.index, "factor_value"] = residual
        rows.append(output)
    result = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if result.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])
    return result.dropna(subset=["factor_value"]).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def write_event_factor_neutral_lead_dedup(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "event_factor_neutral_lead_dedup.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "event_factor_neutral_lead_dedup.md").write_text(
        render_event_factor_neutral_lead_dedup_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "event_factor_lead_reference_correlations.csv",
        result.get("reference_correlations", []),
        REFERENCE_CORRELATION_COLUMNS,
    )
    _write_csv(
        output_path / "event_factor_lead_exposure_correlations.csv",
        result.get("exposure_correlations", []),
        EXPOSURE_CORRELATION_COLUMNS,
    )
    _write_csv(output_path / "event_factor_lead_raw_yearly_ic.csv", result.get("raw_yearly_ic", []), YEARLY_IC_COLUMNS)
    _write_csv(output_path / "event_factor_lead_raw_monthly_ic.csv", result.get("raw_monthly_ic", []), MONTHLY_IC_COLUMNS)
    _write_csv(
        output_path / "event_factor_lead_raw_ic_observations.csv",
        result.get("raw_ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )
    _write_csv(
        output_path / "event_factor_lead_residual_yearly_ic.csv",
        result.get("residual_yearly_ic", []),
        YEARLY_IC_COLUMNS,
    )
    _write_csv(
        output_path / "event_factor_lead_residual_monthly_ic.csv",
        result.get("residual_monthly_ic", []),
        MONTHLY_IC_COLUMNS,
    )
    _write_csv(
        output_path / "event_factor_lead_residual_ic_observations.csv",
        result.get("residual_ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )


def render_event_factor_neutral_lead_dedup_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    raw_ic = result.get("raw_ic_summary", {})
    residual_ic = result.get("residual_ic_summary", {})
    gate = result.get("gate", {})
    lines = [
        "# Event Factor Neutral Lead Dedup Round148",
        "",
        "## Summary",
        "",
        f"- Lead: `{result.get('lead_factor_name')}` horizon {result.get('horizon')}",
        f"- Lead rows: {summary.get('lead_rows', 0)}",
        f"- Raw mean IC: {raw_ic.get('mean_spearman_ic', 0.0):.4f}",
        f"- Raw ICIR: {raw_ic.get('icir', 0.0):.3f}",
        f"- Raw IC observations: {raw_ic.get('ic_observations', 0)}",
        f"- Residual mean IC: {residual_ic.get('mean_spearman_ic', 0.0):.4f}",
        f"- Residual ICIR: {residual_ic.get('icir', 0.0):.3f}",
        f"- Residual IC observations: {residual_ic.get('ic_observations', 0)}",
        f"- Highly redundant public references: {summary.get('reference_highly_redundant_count', 0)}",
        f"- High public exposures: {summary.get('public_exposure_high_count', 0)}",
        f"- Portfolio conversion candidate: {result.get('promotion_policy', {}).get('portfolio_conversion_candidate', False)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Next direction: `{result.get('next_direction')}`",
        "",
        "## Public Reference Correlations",
        "",
        "| Factor | Obs | Mean | Mean Abs | Max Abs | Class | Blockers |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("reference_correlations", []):
        lines.append(
            "| {name} | {obs} | {mean:.4f} | {mean_abs:.4f} | {max_abs:.4f} | {klass} | {blockers} |".format(
                name=row.get("factor_name"),
                obs=row.get("correlation_observations", 0),
                mean=row.get("mean_correlation", 0.0),
                mean_abs=row.get("mean_abs_correlation", 0.0),
                max_abs=row.get("max_abs_correlation", 0.0),
                klass=row.get("redundancy_class", "unknown"),
                blockers=", ".join(row.get("blockers", [])) if row.get("blockers") else "none",
            )
        )
    lines.extend(
        [
            "",
            "## Public Exposure Correlations",
            "",
            "| Exposure | Role | Obs | Mean | Mean Abs | Max Abs | Class | Blockers |",
            "|---|---|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in result.get("exposure_correlations", []):
        lines.append(
            "| {name} | {role} | {obs} | {mean:.4f} | {mean_abs:.4f} | {max_abs:.4f} | {klass} | {blockers} |".format(
                name=row.get("exposure_name"),
                role=row.get("exposure_role", "public_reference"),
                obs=row.get("correlation_observations", 0),
                mean=row.get("mean_correlation", 0.0),
                mean_abs=row.get("mean_abs_correlation", 0.0),
                max_abs=row.get("max_abs_correlation", 0.0),
                klass=row.get("exposure_class", "unknown"),
                blockers=", ".join(row.get("blockers", [])) if row.get("blockers") else "none",
            )
        )
    lines.extend(
        [
            "",
            "## Residual Yearly IC",
            "",
            "| Year | Obs | Mean IC | IC+ | Failure |",
            "|---:|---:|---:|---:|---|",
        ]
    )
    for row in result.get("residual_yearly_ic", []):
        lines.append(
            f"| {row.get('year')} | {row.get('ic_observations', 0)} | {row.get('mean_spearman_ic', 0.0):.4f} | {row.get('positive_ic_rate', 0.0):.1%} | {row.get('failure', False)} |"
        )
    lines.extend(
        [
            "",
            "## Gate",
            "",
            f"- Blockers: {', '.join(gate.get('blockers', [])) if gate.get('blockers') else 'none'}",
            f"- Drawdown policy: {gate.get('drawdown_policy', '')}",
            f"- Safety: {result.get('safety', SAFETY)}",
            "",
        ]
    )
    return "\n".join(lines)


def _event_exposure_correlations(
    lead_frame: pd.DataFrame,
    *,
    min_cross_section: int,
    high_exposure_corr_threshold: float,
    high_exposure_mean_abs_corr_threshold: float,
) -> list[dict[str, Any]]:
    if lead_frame.empty:
        return []
    rows = []
    for exposure_name in sorted(PUBLIC_REFERENCE_EXPOSURES):
        if exposure_name not in lead_frame:
            continue
        role = "public_reference"
        row = _exposure_correlation_row(
            lead_frame[["date", "asset_id", "market", "factor_value", exposure_name]].rename(
                columns={exposure_name: "exposure_value"}
            ),
            name=exposure_name,
            role=role,
            min_cross_section=min_cross_section,
            high_corr_threshold=high_exposure_corr_threshold,
            high_mean_abs_corr_threshold=high_exposure_mean_abs_corr_threshold,
        )
        rows.append(row)
    return sorted(rows, key=lambda row: (-row["max_abs_correlation"], -row["mean_abs_correlation"], row["exposure_name"]))


def _exposure_correlation_row(
    group: pd.DataFrame,
    *,
    name: str,
    role: str,
    min_cross_section: int,
    high_corr_threshold: float,
    high_mean_abs_corr_threshold: float,
) -> dict[str, Any]:
    corr_values: list[float] = []
    cross_sections: list[int] = []
    dates: list[pd.Timestamp] = []
    for signal_date, date_frame in group.groupby("date", sort=True):
        date_frame = date_frame.dropna(subset=["factor_value", "exposure_value"])
        if len(date_frame) < min_cross_section:
            continue
        corr = _spearman(date_frame["factor_value"], date_frame["exposure_value"])
        if not _is_finite(corr):
            continue
        corr_values.append(float(corr))
        cross_sections.append(int(len(date_frame)))
        dates.append(pd.Timestamp(signal_date))
    if not corr_values:
        return {
            "exposure_name": name,
            "exposure_role": role,
            "correlation_observations": 0,
            "mean_correlation": 0.0,
            "mean_abs_correlation": 0.0,
            "median_abs_correlation": 0.0,
            "max_abs_correlation": 0.0,
            "positive_correlation_rate": 0.0,
            "median_cross_section": 0.0,
            "unique_dates": 0,
            "exposure_class": "insufficient_overlap",
            "blockers": ["insufficient_public_exposure_overlap_with_lead"],
        }
    series = pd.Series(corr_values, dtype=float)
    abs_series = series.abs()
    if float(abs_series.max()) >= high_corr_threshold or float(abs_series.mean()) >= high_mean_abs_corr_threshold:
        klass = "high_exposure"
    elif float(abs_series.max()) >= 0.70 or float(abs_series.mean()) >= 0.40:
        klass = "moderate_exposure"
    else:
        klass = "low_exposure"
    blockers = []
    if klass == "high_exposure":
        blockers.append("high_public_reference_exposure_correlation")
    elif klass == "moderate_exposure":
        blockers.append("moderate_public_reference_exposure_correlation")
    return {
        "exposure_name": name,
        "exposure_role": role,
        "correlation_observations": int(len(series)),
        "mean_correlation": float(series.mean()),
        "mean_abs_correlation": float(abs_series.mean()),
        "median_abs_correlation": float(abs_series.median()),
        "max_abs_correlation": float(abs_series.max()),
        "positive_correlation_rate": float((series > 0).mean()),
        "median_cross_section": float(pd.Series(cross_sections).median()) if cross_sections else 0.0,
        "unique_dates": int(len(set(dates))),
        "exposure_class": klass,
        "blockers": blockers,
    }


def _gate_blockers(
    lead_frame: pd.DataFrame,
    *,
    prescreen_evidence: dict[str, Any],
    raw_ic_summary: dict[str, Any],
    residual_ic_summary: dict[str, Any],
    raw_yearly_ic: list[dict[str, Any]],
    residual_yearly_ic: list[dict[str, Any]],
    reference_correlations: list[dict[str, Any]],
    exposure_correlations: list[dict[str, Any]],
    min_residual_mean_ic: float,
    min_residual_icir: float,
    min_residual_positive_ic_rate: float,
) -> list[str]:
    blockers = []
    if lead_frame.empty:
        blockers.append("lead_factor_frame_empty")
    if not prescreen_evidence.get("prescreen_research_lead", False):
        blockers.append("round147_prescreen_lead_not_confirmed")
    if not raw_ic_summary.get("minimum_observation_gate_passed", False):
        blockers.append("raw_ic_observations_below_threshold")
    if not residual_ic_summary.get("minimum_observation_gate_passed", False):
        blockers.append("residual_ic_observations_below_threshold")
    if residual_ic_summary.get("mean_spearman_ic", 0.0) < min_residual_mean_ic:
        blockers.append("residual_mean_ic_below_threshold")
    if residual_ic_summary.get("icir", 0.0) < min_residual_icir:
        blockers.append("residual_icir_below_threshold")
    if residual_ic_summary.get("positive_ic_rate", 0.0) < min_residual_positive_ic_rate:
        blockers.append("residual_positive_ic_rate_below_threshold")
    if any(row.get("redundancy_class") == "highly_redundant" for row in reference_correlations):
        blockers.append("lead_highly_redundant_with_public_reference_factor")
    if any(row.get("exposure_class") == "high_exposure" for row in exposure_correlations):
        blockers.append("lead_high_public_yield_or_value_exposure")
    if any(row.get("year") == 2015 and row.get("failure") for row in raw_yearly_ic + residual_yearly_ic):
        blockers.append("twenty_fifteen_regime_failure_unexplained")
    if any(row.get("failure") for row in raw_yearly_ic):
        blockers.append("raw_yearly_ic_instability")
    if any(row.get("failure") for row in residual_yearly_ic):
        blockers.append("residual_yearly_ic_instability")
    return _dedupe(blockers)


def _next_direction(
    blockers: list[str],
    *,
    residual_ic_summary: dict[str, Any],
    min_residual_mean_ic: float,
    min_residual_icir: float,
    min_residual_positive_ic_rate: float,
) -> str:
    if not blockers:
        return NEXT_PORTFOLIO_PREFLIGHT_DIRECTION
    residual_pass = (
        residual_ic_summary.get("minimum_observation_gate_passed", False)
        and residual_ic_summary.get("mean_spearman_ic", 0.0) >= min_residual_mean_ic
        and residual_ic_summary.get("icir", 0.0) >= min_residual_icir
        and residual_ic_summary.get("positive_ic_rate", 0.0) >= min_residual_positive_ic_rate
    )
    hard_blockers = [blocker for blocker in blockers if blocker not in SOFT_STABILITY_BLOCKERS]
    dedup_only_blockers = {
        "lead_highly_redundant_with_public_reference_factor",
        "lead_high_public_yield_or_value_exposure",
    }
    if residual_pass and hard_blockers and all(blocker in dedup_only_blockers for blocker in hard_blockers):
        return NEXT_INCREMENTAL_RESIDUAL_DIRECTION
    if residual_pass and not hard_blockers:
        return NEXT_STABILITY_AUDIT_DIRECTION
    return ROTATE_AFTER_DEDUP_FAILURE_DIRECTION


def _prescreen_evidence(
    prescreen_report: dict[str, Any] | None,
    *,
    lead_factor_name: str,
    horizon: int,
) -> dict[str, Any]:
    results = list((prescreen_report or {}).get("results", []))
    lead_row = next(
        (
            row
            for row in results
            if row.get("factor_name") == lead_factor_name and int(float(row.get("horizon", horizon))) == int(horizon)
        ),
        None,
    )
    return {
        "prescreen_report_present": bool(prescreen_report),
        "prescreen_research_lead": bool(lead_row and lead_row.get("research_lead", False)),
        "prescreen_blockers": _normalise_blockers(lead_row.get("blockers") if lead_row else []),
        "prescreen_summary_research_lead_count": int((prescreen_report or {}).get("summary", {}).get("research_lead_count", 0)),
    }


def _lead_specs(lead_factor_name: str) -> list[Any]:
    return [spec for spec in default_event_factor_candidate_specs() if spec.factor_name == lead_factor_name]


def _normalise_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])
    normalised = frame.copy()
    normalised["date"] = pd.to_datetime(normalised["date"])
    normalised["asset_id"] = normalised["asset_id"].astype(str)
    normalised["market"] = normalised["market"].astype(str)
    normalised["factor_name"] = normalised["factor_name"].astype(str)
    normalised["factor_value"] = pd.to_numeric(normalised["factor_value"], errors="coerce")
    for column in ["amount", "adv20_amount", *PUBLIC_REFERENCE_EXPOSURES]:
        if column in normalised:
            normalised[column] = pd.to_numeric(normalised[column], errors="coerce")
    return normalised.sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def _normalise_exposure_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market"])
    normalised = frame.copy()
    normalised["date"] = pd.to_datetime(normalised["date"])
    normalised["asset_id"] = normalised["asset_id"].astype(str)
    normalised["market"] = normalised["market"].astype(str)
    for column in [*PUBLIC_REFERENCE_EXPOSURES, "amount", "adv20_amount"]:
        if column in normalised:
            normalised[column] = pd.to_numeric(normalised[column], errors="coerce")
    return normalised.drop_duplicates(["date", "asset_id", "market"], keep="last").reset_index(drop=True)


def _merge_lead_exposures(lead: pd.DataFrame, exposure_frame: pd.DataFrame) -> pd.DataFrame:
    if lead.empty or exposure_frame.empty:
        return lead.copy()
    exposure_columns = ["date", "asset_id", "market"] + [
        column for column in sorted(PUBLIC_REFERENCE_EXPOSURES) if column in exposure_frame.columns
    ]
    return lead.merge(
        exposure_frame[exposure_columns],
        on=["date", "asset_id", "market"],
        how="left",
        validate="many_to_one",
    )


def _filter_analysis_window(
    frame: pd.DataFrame,
    *,
    analysis_start_date: str,
    analysis_end_date: str,
    include_final_holdout: bool,
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"])
    end = output["date"].max() if include_final_holdout else pd.Timestamp(analysis_end_date)
    return output[(output["date"] >= pd.Timestamp(analysis_start_date)) & (output["date"] <= end)].reset_index(drop=True)


def _data_window(
    bars: pd.DataFrame,
    lead_frame: pd.DataFrame,
    reference_frame: pd.DataFrame,
    exposure_frame: pd.DataFrame,
    labels: pd.DataFrame,
) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "bar_rows": int(len(bars)),
        "asset_count": int(bars["asset_id"].nunique()) if "asset_id" in bars else 0,
        "lead_factor_rows": int(len(lead_frame)),
        "reference_factor_rows": int(len(reference_frame)),
        "exposure_rows": int(len(exposure_frame)),
        "label_rows": int(len(labels)),
        "min_factor_date": _min_date(lead_frame, "date"),
        "max_factor_date": _max_date(lead_frame, "date"),
    }


def _normalise_blockers(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item)]
    return [item.strip() for item in str(value).replace(";", ",").split(",") if item.strip()]


def _spearman(left: pd.Series, right: pd.Series) -> float:
    aligned = pd.concat([left, right], axis=1).dropna()
    if len(aligned) < 2:
        return float("nan")
    return float(aligned.iloc[:, 0].rank(method="average").corr(aligned.iloc[:, 1].rank(method="average")))


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
    seen: set[str] = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
