from __future__ import annotations

from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_preregistration import (
    SAFETY,
    default_capacity_safe_price_volume_candidate_specs,
)
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    _data_window,
    _sanitize,
    compute_capacity_safe_price_volume_factors,
    load_capacity_safe_bars,
)
from quant_robot.ops.market_residual_risk_premia_preregistration import (
    default_market_residual_risk_premia_candidate_specs,
)
from quant_robot.ops.market_residual_risk_premia_prescreen import (
    compute_market_residual_risk_premia_factors,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "market_residual_lead_exposure_dedup"
DEFAULT_LEAD_FACTOR_NAME = "beta_adjusted_range_contraction_60"
DEFAULT_HORIZON = 20
NEXT_REVIEW_DIRECTION = "round113_round110_112_three_round_review_before_next_action"
POST_REVIEW_BRIDGE_DIRECTION = "round113_market_residual_cost_capacity_walk_forward_bridge_after_review"
POST_REVIEW_ROTATE_DIRECTION = "round113_family_rotation_after_market_residual_lead_audit"
DEFAULT_REFERENCE_FACTOR_NAMES = (
    "range_contraction_lowvol_reversal_20",
    "bollinger_reversal_lowvol_liquid_20",
    "donchian_pullback_lowvol_liquid_20",
    "pv_lowvol_reversal_blend_20",
)
REFERENCE_CORRELATION_COLUMNS = [
    "factor_name",
    "correlation_observations",
    "mean_correlation",
    "mean_abs_correlation",
    "median_abs_correlation",
    "max_abs_correlation",
    "positive_correlation_rate",
    "median_cross_section",
    "unique_dates",
    "unique_assets",
    "redundancy_class",
    "blockers",
]
EXPOSURE_CORRELATION_COLUMNS = [
    "exposure_name",
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
IC_OBSERVATION_COLUMNS = ["factor_name", "horizon", "date", "spearman_ic", "cross_section"]
YEARLY_IC_COLUMNS = ["year", "ic_observations", "mean_spearman_ic", "positive_ic_rate", "failure"]
MONTHLY_IC_COLUMNS = ["month", "ic_observations", "mean_spearman_ic", "positive_ic_rate", "failure"]


def build_market_residual_lead_exposure_dedup(
    *,
    bars_roots: Iterable[str | Path],
    prescreen_report: dict[str, Any] | str | Path,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    horizon: int = DEFAULT_HORIZON,
    execution_lag: int = 1,
    sample_every_n_dates: int = 5,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    reference_factor_names: Sequence[str] = DEFAULT_REFERENCE_FACTOR_NAMES,
) -> dict[str, Any]:
    report = _load_report(prescreen_report)
    bars = load_capacity_safe_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    lead_specs = _lead_specs(lead_factor_name)
    lead_frame = compute_market_residual_risk_premia_factors(
        bars,
        candidate_specs=lead_specs,
        min_signal_date_amount=min_signal_date_amount,
    )
    reference_specs = _reference_specs(reference_factor_names)
    reference_frame = compute_capacity_safe_price_volume_factors(
        bars,
        candidate_specs=reference_specs,
        min_signal_date_amount=min_signal_date_amount,
    )
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=(horizon,),
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_market_residual_lead_exposure_dedup(
        lead_frame,
        labels,
        reference_factor_frame=reference_frame,
        prescreen_report=report,
        lead_factor_name=lead_factor_name,
        horizon=horizon,
        sample_every_n_dates=sample_every_n_dates,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
    )
    window = _data_window(bars, lead_frame, labels)
    result["data_window"] = window | {
        "min_factor_date": window.get("min_signal_date"),
        "max_factor_date": window.get("max_signal_date"),
        "factor_rows": int(len(lead_frame)),
        "reference_factor_rows": int(len(reference_frame)),
        "label_rows": int(len(labels)),
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
    }
    result["sampling_policy"] = {
        "sample_every_n_dates": sample_every_n_dates,
        "sampling_used_for_correlations_only": True,
    }
    result["markdown"] = render_market_residual_lead_exposure_dedup_markdown(result)
    return result


def summarize_market_residual_lead_exposure_dedup(
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    reference_factor_frame: pd.DataFrame | None = None,
    prescreen_report: dict[str, Any] | None = None,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    horizon: int = DEFAULT_HORIZON,
    sample_every_n_dates: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    high_corr_threshold: float = 0.85,
    high_mean_abs_corr_threshold: float = 0.70,
    moderate_corr_threshold: float = 0.70,
    moderate_mean_abs_corr_threshold: float = 0.50,
    high_exposure_corr_threshold: float = 0.85,
    high_exposure_mean_abs_corr_threshold: float = 0.60,
) -> dict[str, Any]:
    frame = _normalise_factor_frame(factor_frame)
    reference_frame = _normalise_factor_frame(reference_factor_frame if reference_factor_frame is not None else pd.DataFrame())
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
    exposure_correlations = _exposure_correlations(
        sampled_lead,
        min_cross_section=min_cross_section,
        high_exposure_corr_threshold=high_exposure_corr_threshold,
        high_exposure_mean_abs_corr_threshold=high_exposure_mean_abs_corr_threshold,
    )
    prescreen_evidence = _prescreen_evidence(prescreen_report, lead_factor_name=lead_factor_name, horizon=horizon)
    lead_ic_summary = _lead_ic_summary(ic_observations, min_ic_observations=min_ic_observations)
    blockers = _gate_blockers(
        lead,
        prescreen_evidence=prescreen_evidence,
        lead_ic_summary=lead_ic_summary,
        yearly_ic=yearly_ic,
        reference_correlations=reference_correlations,
        exposure_correlations=exposure_correlations,
    )
    recommended_post_review_direction = POST_REVIEW_BRIDGE_DIRECTION if not blockers else POST_REVIEW_ROTATE_DIRECTION
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "lead_factor_name": lead_factor_name,
        "horizon": int(horizon),
        "lead_evidence": prescreen_evidence,
        "lead_ic_summary": lead_ic_summary,
        "summary": {
            "lead_rows": int(len(lead)),
            "reference_factor_count": int(reference_frame["factor_name"].nunique()) if not reference_frame.empty else 0,
            "reference_highly_redundant_count": int(
                sum(1 for row in reference_correlations if row["redundancy_class"] == "highly_redundant")
            ),
            "exposure_high_count": int(
                sum(1 for row in exposure_correlations if row["exposure_class"] == "high_exposure")
            ),
            "yearly_failure_count": int(sum(1 for row in yearly_ic if row["failure"])),
            "monthly_failure_count": int(sum(1 for row in monthly_ic if row["failure"])),
            "promotion_allowed_candidates": 0,
        },
        "thresholds": {
            "min_cross_section": min_cross_section,
            "min_ic_observations": min_ic_observations,
            "high_corr_threshold": high_corr_threshold,
            "high_mean_abs_corr_threshold": high_mean_abs_corr_threshold,
            "moderate_corr_threshold": moderate_corr_threshold,
            "moderate_mean_abs_corr_threshold": moderate_mean_abs_corr_threshold,
            "high_exposure_corr_threshold": high_exposure_corr_threshold,
            "high_exposure_mean_abs_corr_threshold": high_exposure_mean_abs_corr_threshold,
        },
        "gate": {
            "blockers": blockers,
            "required_before": [
                "market_residual_lead_exposure_dedup_after_round111",
                "beta_adjusted_range_contraction_2015_regime_failure_audit",
                "market_residual_lead_monthly_yearly_stability_audit",
                "no_round112_topn_before_exposure_correlation_dedup",
            ],
            "drawdown_policy": "Drawdown tolerance is a user preference and is not used here as a capacity, exposure, or stability waiver.",
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed": False,
            "reason": "Round112 is an exposure, stability, and redundancy audit only; cost, capacity, regime, and walk-forward gates remain required.",
        },
        "next_direction": NEXT_REVIEW_DIRECTION,
        "recommended_post_review_direction": recommended_post_review_direction,
        "reference_correlations": reference_correlations,
        "exposure_correlations": exposure_correlations,
        "yearly_ic": yearly_ic,
        "monthly_ic": monthly_ic,
        "ic_observations": ic_observations,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_market_residual_lead_exposure_dedup_markdown(result)
    return result


def write_market_residual_lead_exposure_dedup(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "market_residual_lead_exposure_dedup.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "market_residual_lead_exposure_dedup.md").write_text(
        render_market_residual_lead_exposure_dedup_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "market_residual_lead_reference_correlations.csv",
        result.get("reference_correlations", []),
        REFERENCE_CORRELATION_COLUMNS,
    )
    _write_csv(
        output_path / "market_residual_lead_exposure_correlations.csv",
        result.get("exposure_correlations", []),
        EXPOSURE_CORRELATION_COLUMNS,
    )
    _write_csv(output_path / "market_residual_lead_yearly_ic.csv", result.get("yearly_ic", []), YEARLY_IC_COLUMNS)
    _write_csv(output_path / "market_residual_lead_monthly_ic.csv", result.get("monthly_ic", []), MONTHLY_IC_COLUMNS)
    _write_csv(
        output_path / "market_residual_lead_ic_observations.csv",
        result.get("ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )


def render_market_residual_lead_exposure_dedup_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lead_ic = result.get("lead_ic_summary", {})
    gate = result.get("gate", {})
    lines = [
        "# Market Residual Lead Exposure Dedup",
        "",
        "## Summary",
        "",
        f"- Lead: `{result.get('lead_factor_name')}` horizon {result.get('horizon')}",
        f"- Lead rows: {summary.get('lead_rows', 0)}",
        f"- IC observations: {lead_ic.get('ic_observations', 0)}",
        f"- Mean IC: {lead_ic.get('mean_spearman_ic', 0.0):.4f}",
        f"- ICIR: {lead_ic.get('icir', 0.0):.3f}",
        f"- Positive IC rate: {lead_ic.get('positive_ic_rate', 0.0):.1%}",
        f"- Highly redundant references: {summary.get('reference_highly_redundant_count', 0)}",
        f"- High exposures: {summary.get('exposure_high_count', 0)}",
        f"- Yearly failures: {summary.get('yearly_failure_count', 0)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Portfolio grid allowed: {result.get('promotion_policy', {}).get('portfolio_grid_allowed', False)}",
        f"- Next direction: `{result.get('next_direction')}`",
        f"- Recommended post-review direction: `{result.get('recommended_post_review_direction')}`",
        "",
        "## Reference Correlations",
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
            "## Exposure Correlations",
            "",
            "| Exposure | Obs | Mean | Mean Abs | Max Abs | Class | Blockers |",
            "|---|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in result.get("exposure_correlations", []):
        lines.append(
            "| {name} | {obs} | {mean:.4f} | {mean_abs:.4f} | {max_abs:.4f} | {klass} | {blockers} |".format(
                name=row.get("exposure_name"),
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
            "## Yearly IC",
            "",
            "| Year | Obs | Mean IC | IC+ | Failure |",
            "|---:|---:|---:|---:|---|",
        ]
    )
    for row in result.get("yearly_ic", []):
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
            f"- Safety: {result.get('safety', '')}",
            "",
        ]
    )
    return "\n".join(lines)


def _lead_specs(lead_factor_name: str) -> list[Any]:
    return [spec for spec in default_market_residual_risk_premia_candidate_specs() if spec.factor_name == lead_factor_name]


def _reference_specs(reference_factor_names: Sequence[str]) -> list[Any]:
    allowed = set(reference_factor_names)
    return [spec for spec in default_capacity_safe_price_volume_candidate_specs() if spec.factor_name in allowed]


def _lead_ic_observations(
    lead_frame: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    lead_factor_name: str,
    horizon: int,
    min_cross_section: int,
) -> list[dict[str, Any]]:
    if lead_frame.empty or labels.empty:
        return []
    label_frame = labels[labels["horizon"] == horizon].copy() if "horizon" in labels else labels.copy()
    merged = lead_frame[["date", "asset_id", "market", "factor_value"]].merge(
        label_frame[["date", "asset_id", "market", "forward_return"]],
        on=["date", "asset_id", "market"],
        how="inner",
    )
    observations: list[dict[str, Any]] = []
    for signal_date, group in merged.groupby("date", sort=True):
        group = group.dropna(subset=["factor_value", "forward_return"])
        if len(group) < min_cross_section:
            continue
        ic = _spearman(group["factor_value"], group["forward_return"])
        if not _is_finite(ic):
            continue
        observations.append(
            {
                "factor_name": lead_factor_name,
                "horizon": int(horizon),
                "date": pd.Timestamp(signal_date).date().isoformat(),
                "spearman_ic": float(ic),
                "cross_section": int(len(group)),
            }
        )
    return observations


def _lead_ic_summary(ic_observations: list[dict[str, Any]], *, min_ic_observations: int) -> dict[str, Any]:
    if not ic_observations:
        return {
            "ic_observations": 0,
            "mean_spearman_ic": 0.0,
            "ic_std": 0.0,
            "icir": 0.0,
            "ic_t_stat": 0.0,
            "positive_ic_rate": 0.0,
            "median_cross_section": 0.0,
            "minimum_observation_gate_passed": False,
        }
    values = pd.Series([row["spearman_ic"] for row in ic_observations], dtype=float)
    std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    mean = float(values.mean())
    return {
        "ic_observations": int(len(values)),
        "mean_spearman_ic": mean,
        "ic_std": std,
        "icir": _safe_ratio(mean, std),
        "ic_t_stat": _t_stat(mean, std, len(values)),
        "positive_ic_rate": float((values > 0).mean()),
        "median_cross_section": float(pd.Series([row["cross_section"] for row in ic_observations]).median()),
        "minimum_observation_gate_passed": bool(len(values) >= min_ic_observations),
    }


def _period_ic(ic_observations: list[dict[str, Any]], *, period: str) -> list[dict[str, Any]]:
    if not ic_observations:
        return []
    frame = pd.DataFrame(ic_observations)
    frame["date"] = pd.to_datetime(frame["date"])
    if period == "year":
        frame["period"] = frame["date"].dt.year.astype(int)
        output_key = "year"
    elif period == "month":
        frame["period"] = frame["date"].dt.to_period("M").astype(str)
        output_key = "month"
    else:
        raise ValueError(f"Unsupported period: {period}")
    rows: list[dict[str, Any]] = []
    for period_value, group in frame.groupby("period", sort=True):
        mean_ic = float(group["spearman_ic"].mean())
        positive_rate = float((group["spearman_ic"] > 0).mean())
        rows.append(
            {
                output_key: period_value,
                "ic_observations": int(len(group)),
                "mean_spearman_ic": mean_ic,
                "positive_ic_rate": positive_rate,
                "failure": bool(mean_ic <= 0.0 or positive_rate < 0.50),
            }
        )
    return rows


def _reference_correlations(
    lead_frame: pd.DataFrame,
    reference_frame: pd.DataFrame,
    *,
    lead_factor_name: str,
    min_cross_section: int,
    high_corr_threshold: float,
    high_mean_abs_corr_threshold: float,
    moderate_corr_threshold: float,
    moderate_mean_abs_corr_threshold: float,
) -> list[dict[str, Any]]:
    if lead_frame.empty or reference_frame.empty:
        return []
    lead = lead_frame[lead_frame["factor_name"] == lead_factor_name][["date", "asset_id", "market", "factor_value"]]
    lead = lead.rename(columns={"factor_value": "lead_value"})
    rows = []
    for factor_name, group in reference_frame.groupby("factor_name", sort=True):
        merged = group[["date", "asset_id", "market", "factor_value"]].merge(
            lead,
            on=["date", "asset_id", "market"],
            how="inner",
        )
        row = _correlation_row(
            name_key="factor_name",
            name=str(factor_name),
            group=merged,
            value_column="factor_value",
            lead_column="lead_value",
            min_cross_section=min_cross_section,
            high_corr_threshold=high_corr_threshold,
            high_mean_abs_corr_threshold=high_mean_abs_corr_threshold,
            moderate_corr_threshold=moderate_corr_threshold,
            moderate_mean_abs_corr_threshold=moderate_mean_abs_corr_threshold,
            high_class="highly_redundant",
            moderate_class="moderately_redundant",
            unique_class="unique",
            high_blocker="high_reference_correlation_with_lead",
            moderate_blocker="moderate_reference_correlation_with_lead",
            insufficient_blocker="insufficient_reference_overlap_with_lead",
        )
        rows.append(row)
    return sorted(rows, key=lambda row: (-row["max_abs_correlation"], -row["mean_abs_correlation"], row["factor_name"]))


def _exposure_correlations(
    lead_frame: pd.DataFrame,
    *,
    min_cross_section: int,
    high_exposure_corr_threshold: float,
    high_exposure_mean_abs_corr_threshold: float,
) -> list[dict[str, Any]]:
    if lead_frame.empty:
        return []
    frame = lead_frame.copy()
    if "adv20_amount" in frame:
        frame["log_adv20_amount"] = np.log(pd.to_numeric(frame["adv20_amount"], errors="coerce").where(frame["adv20_amount"] > 0))
    exposure_columns = [
        "beta_120",
        "downside_beta_120",
        "market_corr_60",
        "residual_vol_60",
        "log_adv20_amount",
    ]
    rows = []
    for exposure_name in exposure_columns:
        if exposure_name not in frame:
            continue
        group = frame[["date", "asset_id", "market", "factor_value", exposure_name]].rename(
            columns={exposure_name: "exposure_value"}
        )
        row = _correlation_row(
            name_key="exposure_name",
            name=exposure_name,
            group=group,
            value_column="exposure_value",
            lead_column="factor_value",
            min_cross_section=min_cross_section,
            high_corr_threshold=high_exposure_corr_threshold,
            high_mean_abs_corr_threshold=high_exposure_mean_abs_corr_threshold,
            moderate_corr_threshold=0.70,
            moderate_mean_abs_corr_threshold=0.40,
            high_class="high_exposure",
            moderate_class="moderate_exposure",
            unique_class="low_exposure",
            high_blocker="high_lead_exposure_correlation",
            moderate_blocker="moderate_lead_exposure_correlation",
            insufficient_blocker="insufficient_exposure_overlap_with_lead",
        )
        rows.append(row)
    return sorted(rows, key=lambda row: (-row["max_abs_correlation"], -row["mean_abs_correlation"], row["exposure_name"]))


def _correlation_row(
    *,
    name_key: str,
    name: str,
    group: pd.DataFrame,
    value_column: str,
    lead_column: str,
    min_cross_section: int,
    high_corr_threshold: float,
    high_mean_abs_corr_threshold: float,
    moderate_corr_threshold: float,
    moderate_mean_abs_corr_threshold: float,
    high_class: str,
    moderate_class: str,
    unique_class: str,
    high_blocker: str,
    moderate_blocker: str,
    insufficient_blocker: str,
) -> dict[str, Any]:
    corr_values: list[float] = []
    cross_sections: list[int] = []
    dates: list[pd.Timestamp] = []
    for signal_date, date_frame in group.groupby("date", sort=True):
        date_frame = date_frame.dropna(subset=[value_column, lead_column])
        if len(date_frame) < min_cross_section:
            continue
        corr = _spearman(date_frame[value_column], date_frame[lead_column])
        if not _is_finite(corr):
            continue
        corr_values.append(float(corr))
        cross_sections.append(int(len(date_frame)))
        dates.append(pd.Timestamp(signal_date))
    if not corr_values:
        return {
            name_key: name,
            "correlation_observations": 0,
            "mean_correlation": 0.0,
            "mean_abs_correlation": 0.0,
            "median_abs_correlation": 0.0,
            "max_abs_correlation": 0.0,
            "positive_correlation_rate": 0.0,
            "median_cross_section": 0.0,
            "unique_dates": 0,
            "unique_assets": int(group["asset_id"].nunique()) if "asset_id" in group else 0,
            _class_key(name_key): "insufficient_overlap",
            "blockers": [insufficient_blocker],
        }
    series = pd.Series(corr_values, dtype=float)
    abs_series = series.abs()
    klass = _classify_correlation(
        max_abs_corr=float(abs_series.max()),
        mean_abs_corr=float(abs_series.mean()),
        high_corr_threshold=high_corr_threshold,
        high_mean_abs_corr_threshold=high_mean_abs_corr_threshold,
        moderate_corr_threshold=moderate_corr_threshold,
        moderate_mean_abs_corr_threshold=moderate_mean_abs_corr_threshold,
        high_class=high_class,
        moderate_class=moderate_class,
        unique_class=unique_class,
    )
    blockers = []
    if klass == high_class:
        blockers.append(high_blocker)
    elif klass == moderate_class:
        blockers.append(moderate_blocker)
    row = {
        name_key: name,
        "correlation_observations": int(len(series)),
        "mean_correlation": float(series.mean()),
        "mean_abs_correlation": float(abs_series.mean()),
        "median_abs_correlation": float(abs_series.median()),
        "max_abs_correlation": float(abs_series.max()),
        "positive_correlation_rate": float((series > 0).mean()),
        "median_cross_section": float(pd.Series(cross_sections).median()) if cross_sections else 0.0,
        "unique_dates": int(len(set(dates))),
        _class_key(name_key): klass,
        "blockers": blockers,
    }
    if name_key == "factor_name":
        row["unique_assets"] = int(group["asset_id"].nunique()) if "asset_id" in group else 0
    return row


def _class_key(name_key: str) -> str:
    return "redundancy_class" if name_key == "factor_name" else "exposure_class"


def _classify_correlation(
    *,
    max_abs_corr: float,
    mean_abs_corr: float,
    high_corr_threshold: float,
    high_mean_abs_corr_threshold: float,
    moderate_corr_threshold: float,
    moderate_mean_abs_corr_threshold: float,
    high_class: str,
    moderate_class: str,
    unique_class: str,
) -> str:
    if max_abs_corr >= high_corr_threshold or mean_abs_corr >= high_mean_abs_corr_threshold:
        return high_class
    if max_abs_corr >= moderate_corr_threshold or mean_abs_corr >= moderate_mean_abs_corr_threshold:
        return moderate_class
    return unique_class


def _gate_blockers(
    lead_frame: pd.DataFrame,
    *,
    prescreen_evidence: dict[str, Any],
    lead_ic_summary: dict[str, Any],
    yearly_ic: list[dict[str, Any]],
    reference_correlations: list[dict[str, Any]],
    exposure_correlations: list[dict[str, Any]],
) -> list[str]:
    blockers = []
    if lead_frame.empty:
        blockers.append("lead_factor_frame_empty")
    if not prescreen_evidence.get("prescreen_research_lead", False):
        blockers.append("prescreen_lead_not_confirmed")
    if not lead_ic_summary.get("minimum_observation_gate_passed", False):
        blockers.append("lead_ic_observations_below_threshold")
    if any(row["redundancy_class"] == "highly_redundant" for row in reference_correlations):
        blockers.append("lead_highly_redundant_with_reference_factor")
    if any(row["exposure_class"] == "high_exposure" for row in exposure_correlations):
        blockers.append("lead_high_exposure_to_market_or_liquidity_proxy")
    if any(row.get("year") == 2015 and row.get("failure") for row in yearly_ic):
        blockers.append("twenty_fifteen_regime_failure_unexplained")
    if any(row.get("failure") for row in yearly_ic):
        blockers.append("yearly_ic_instability")
    return blockers


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
            if row.get("factor_name") == lead_factor_name and int(row.get("horizon", horizon)) == int(horizon)
        ),
        None,
    )
    return {
        "prescreen_report_present": bool(prescreen_report),
        "prescreen_research_lead": bool(lead_row and lead_row.get("research_lead", False)),
        "prescreen_blockers": _normalise_blockers(lead_row.get("blockers") if lead_row else []),
        "prescreen_summary_research_lead_count": int((prescreen_report or {}).get("summary", {}).get("research_lead_count", 0)),
    }


def _normalise_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])
    normalised = frame.copy()
    normalised["date"] = pd.to_datetime(normalised["date"])
    normalised["asset_id"] = normalised["asset_id"].astype(str)
    normalised["market"] = normalised["market"].astype(str)
    normalised["factor_name"] = normalised["factor_name"].astype(str)
    normalised["factor_value"] = pd.to_numeric(normalised["factor_value"], errors="coerce")
    for column in ["amount", "adv20_amount", "beta_120", "downside_beta_120", "market_corr_60", "residual_vol_60"]:
        if column in normalised:
            normalised[column] = pd.to_numeric(normalised[column], errors="coerce")
    return normalised.sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def _sample_dates(frame: pd.DataFrame, *, sample_every_n_dates: int) -> pd.DataFrame:
    if frame.empty or sample_every_n_dates <= 1:
        return frame
    dates = pd.Index(sorted(frame["date"].dropna().unique()))
    keep_dates = set(dates[::sample_every_n_dates])
    return frame[frame["date"].isin(keep_dates)].reset_index(drop=True)


def _filter_dates(frame: pd.DataFrame, dates: Sequence[Any]) -> pd.DataFrame:
    if frame.empty:
        return frame
    keep_dates = set(pd.to_datetime(pd.Index(dates)))
    return frame[frame["date"].isin(keep_dates)].reset_index(drop=True)


def _load_report(value: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return json.loads(Path(value).read_text(encoding="utf-8"))


def _normalise_blockers(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [item.strip() for item in value.split(";") if item.strip()]
    return [str(value)]


def _spearman(left: pd.Series, right: pd.Series) -> float:
    aligned = pd.concat([left, right], axis=1).dropna()
    if len(aligned) < 2:
        return float("nan")
    left_rank = aligned.iloc[:, 0].rank(method="average")
    right_rank = aligned.iloc[:, 1].rank(method="average")
    if float(left_rank.std(ddof=0)) <= 1e-12 or float(right_rank.std(ddof=0)) <= 1e-12:
        return float("nan")
    return float(left_rank.corr(right_rank))


def _safe_ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) <= 1e-12:
        return 0.0
    return float(numerator / denominator)


def _t_stat(mean: float, std: float, observations: int) -> float:
    if observations <= 1 or abs(std) <= 1e-12:
        return 0.0
    return float(mean / (std / math.sqrt(observations)))


def _is_finite(value: Any) -> bool:
    try:
        return bool(math.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return ";".join(str(item) for item in value)
    if isinstance(value, (pd.Timestamp,)):
        return value.date().isoformat()
    return value
