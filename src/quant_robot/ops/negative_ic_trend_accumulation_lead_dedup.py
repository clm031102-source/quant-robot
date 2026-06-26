from __future__ import annotations

from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_preregistration import (
    DEFAULT_CAPACITY_FILTERS,
    SAFETY,
)
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    compute_capacity_safe_price_volume_factors,
    load_capacity_safe_bars,
)
from quant_robot.ops.capacity_safe_trend_accumulation_prescreen import (
    compute_capacity_safe_trend_accumulation_factors,
)
from quant_robot.ops.negative_ic_trend_accumulation_prescreen import (
    compute_negative_ic_trend_accumulation_factors,
)


STAGE = "negative_ic_trend_accumulation_lead_dedup"
DEFAULT_LEAD_FACTOR_NAME = "overheat_avoidance_relative_strength_60"
DEFAULT_LEAD_HORIZON = 20
BRIDGE_NEXT_DIRECTION = "round109_overheat_relative_strength_cost_capacity_bridge"
ROTATE_NEXT_DIRECTION = "round109_family_rotation_after_round108_dedup_failure"
HARD_BLOCKING_REFERENCE_FAMILIES = ("capacity_safe_price_volume",)
SOURCE_LINEAGE_REFERENCE_FAMILIES = ("positive_trend_accumulation_source",)
CORRELATION_COLUMNS = [
    "reference_family",
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
    "hard_blocking_redundancy",
    "source_lineage_redundancy",
    "blockers",
]
OBSERVATION_COLUMNS = ["reference_family", "factor_name", "date", "spearman_correlation", "cross_section"]
CAPACITY_COLUMNS = [
    "date",
    "top_quantile_count",
    "median_amount",
    "median_adv20_amount",
    "min_amount",
    "min_adv20_amount",
    "amount_breach_count",
    "adv20_breach_count",
    "extreme_abs_return_095_count",
    "extreme_abs_return_020_count",
    "max_abs_return_1d",
]


def build_negative_ic_trend_accumulation_lead_dedup(
    *,
    bars_roots: Iterable[str | Path],
    prescreen_report: dict[str, Any] | str | Path,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    lead_horizon: int = DEFAULT_LEAD_HORIZON,
    sample_every_n_dates: int = 5,
    min_cross_section: int = 30,
    min_signal_date_amount: float = DEFAULT_CAPACITY_FILTERS["min_signal_date_amount"],
) -> dict[str, Any]:
    report = _load_prescreen_report(prescreen_report)
    bars = load_capacity_safe_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    factor_frame = compute_negative_ic_lead_reference_factor_frame(
        bars,
        sample_every_n_dates=sample_every_n_dates,
        min_signal_date_amount=min_signal_date_amount,
    )
    result = summarize_negative_ic_trend_accumulation_lead_dedup(
        factor_frame,
        bars=bars,
        lead_factor_name=lead_factor_name,
        lead_horizon=lead_horizon,
        prescreen_report=report,
        min_cross_section=min_cross_section,
        min_signal_date_amount=min_signal_date_amount,
    )
    result["data_window"] = _data_window(bars, factor_frame)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_clearance_only",
    }
    result["capacity_policy"] = {
        "min_signal_date_amount": min_signal_date_amount,
        "sample_every_n_dates": sample_every_n_dates,
        "extreme_abs_return_threshold": 0.095,
        "extreme_abs_return_rate_block_threshold": 0.05,
        "drawdown_tolerance_is_not_capacity_waiver": True,
    }
    result["markdown"] = render_negative_ic_trend_accumulation_lead_dedup_markdown(result)
    return result


def compute_negative_ic_lead_reference_factor_frame(
    bars: pd.DataFrame,
    *,
    sample_every_n_dates: int = 5,
    min_signal_date_amount: float = DEFAULT_CAPACITY_FILTERS["min_signal_date_amount"],
) -> pd.DataFrame:
    frames = [
        _family_frame(
            compute_negative_ic_trend_accumulation_factors(
                bars,
                min_signal_date_amount=min_signal_date_amount,
            ),
            "negative_ic_trend_accumulation_same_family",
            sample_every_n_dates,
        ),
        _family_frame(
            compute_capacity_safe_trend_accumulation_factors(
                bars,
                min_signal_date_amount=min_signal_date_amount,
            ),
            "positive_trend_accumulation_source",
            sample_every_n_dates,
        ),
        _family_frame(
            compute_capacity_safe_price_volume_factors(
                bars,
                min_signal_date_amount=min_signal_date_amount,
            ),
            "capacity_safe_price_volume",
            sample_every_n_dates,
        ),
    ]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame(
            columns=[
                "date",
                "asset_id",
                "market",
                "factor_name",
                "factor_value",
                "amount",
                "adv20_amount",
                "reference_family",
            ]
        )
    return pd.concat(frames, ignore_index=True).sort_values(
        ["reference_family", "factor_name", "date", "asset_id"]
    ).reset_index(drop=True)


def summarize_negative_ic_trend_accumulation_lead_dedup(
    factor_frame: pd.DataFrame,
    *,
    bars: pd.DataFrame | None = None,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    lead_horizon: int = DEFAULT_LEAD_HORIZON,
    prescreen_report: dict[str, Any] | None = None,
    min_cross_section: int = 30,
    min_signal_date_amount: float = DEFAULT_CAPACITY_FILTERS["min_signal_date_amount"],
    moderate_corr_threshold: float = 0.70,
    high_corr_threshold: float = 0.85,
    moderate_mean_abs_corr_threshold: float = 0.50,
    high_mean_abs_corr_threshold: float = 0.70,
    extreme_abs_return_threshold: float = 0.095,
    extreme_abs_return_rate_block_threshold: float = 0.05,
) -> dict[str, Any]:
    frame = _normalise_factor_frame(factor_frame)
    lead_evidence = _prescreen_lead_evidence(prescreen_report, lead_factor_name, lead_horizon)
    correlations, correlation_observations = _lead_correlations(
        frame,
        lead_factor_name=lead_factor_name,
        min_cross_section=min_cross_section,
        moderate_corr_threshold=moderate_corr_threshold,
        high_corr_threshold=high_corr_threshold,
        moderate_mean_abs_corr_threshold=moderate_mean_abs_corr_threshold,
        high_mean_abs_corr_threshold=high_mean_abs_corr_threshold,
    )
    capacity_audit, capacity_observations = _lead_capacity_audit(
        frame,
        bars=bars,
        lead_factor_name=lead_factor_name,
        min_cross_section=min_cross_section,
        min_signal_date_amount=min_signal_date_amount,
        extreme_abs_return_threshold=extreme_abs_return_threshold,
        extreme_abs_return_rate_block_threshold=extreme_abs_return_rate_block_threshold,
    )
    summary = _summary(frame, correlations, correlation_observations, lead_factor_name)
    blockers = _gate_blockers(frame, lead_evidence, correlations, capacity_audit, lead_factor_name)
    next_direction = ROTATE_NEXT_DIRECTION if blockers else BRIDGE_NEXT_DIRECTION
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "lead_factor_name": lead_factor_name,
        "lead_horizon": int(lead_horizon),
        "lead_evidence": lead_evidence,
        "summary": summary,
        "thresholds": {
            "moderate_corr_threshold": moderate_corr_threshold,
            "high_corr_threshold": high_corr_threshold,
            "moderate_mean_abs_corr_threshold": moderate_mean_abs_corr_threshold,
            "high_mean_abs_corr_threshold": high_mean_abs_corr_threshold,
            "min_cross_section": min_cross_section,
            "min_signal_date_amount": min_signal_date_amount,
            "extreme_abs_return_threshold": extreme_abs_return_threshold,
            "extreme_abs_return_rate_block_threshold": extreme_abs_return_rate_block_threshold,
        },
        "capacity_audit": capacity_audit,
        "gate": {
            "blockers": blockers,
            "required_before": [
                "negative_ic_trend_accumulation_lead_correlation_dedup_before_portfolio_grid",
                "overheat_relative_strength_capacity_extreme_trade_audit_before_portfolio",
            ],
            "allowed_next_directions": [BRIDGE_NEXT_DIRECTION, ROTATE_NEXT_DIRECTION],
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_backtest_allowed_before_dedup": False,
            "reason": "Round108 is a pre-portfolio lead audit only.",
        },
        "next_direction": next_direction,
        "correlations": correlations,
        "correlation_observations": correlation_observations,
        "capacity_observations": capacity_observations,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_negative_ic_trend_accumulation_lead_dedup_markdown(result)
    return result


def write_negative_ic_trend_accumulation_lead_dedup(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "negative_ic_trend_accumulation_lead_dedup.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "negative_ic_trend_accumulation_lead_dedup.md").write_text(
        render_negative_ic_trend_accumulation_lead_dedup_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "negative_ic_trend_accumulation_lead_correlations.csv",
        result.get("correlations", []),
        CORRELATION_COLUMNS,
    )
    _write_csv(
        output_path / "negative_ic_trend_accumulation_lead_correlation_observations.csv",
        result.get("correlation_observations", []),
        OBSERVATION_COLUMNS,
    )
    _write_csv(
        output_path / "negative_ic_trend_accumulation_lead_capacity_observations.csv",
        result.get("capacity_observations", []),
        CAPACITY_COLUMNS,
    )


def render_negative_ic_trend_accumulation_lead_dedup_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    capacity = result.get("capacity_audit", {})
    gate = result.get("gate", {})
    lines = [
        "# Negative-IC Trend Accumulation Lead Dedup",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Lead: {result.get('lead_factor_name', DEFAULT_LEAD_FACTOR_NAME)}",
        f"- Lead horizon: {result.get('lead_horizon', DEFAULT_LEAD_HORIZON)}",
        f"- Prescreen lead confirmed: {result.get('lead_evidence', {}).get('prescreen_research_lead', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Compared candidates: {summary.get('compared_candidate_count', 0)}",
        f"- Hard-blocking redundant: {summary.get('hard_blocking_redundant_count', 0)}",
        f"- Source-lineage redundant: {summary.get('source_lineage_redundant_count', 0)}",
        f"- Top-quantile rows audited: {capacity.get('top_quantile_rows', 0)}",
        f"- Extreme abs-return >= 9.5% rate: {capacity.get('extreme_abs_return_095_rate', 0.0):.2%}",
        f"- Next direction: {result.get('next_direction', ROTATE_NEXT_DIRECTION)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Final holdout included: {result.get('holdout_policy', {}).get('final_holdout_included', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Correlations",
        "",
        "| Family | Factor | Obs | Mean | Mean Abs | Max Abs | Class | Hard Block | Source Lineage | Blockers |",
        "|---|---|---:|---:|---:|---:|---|---|---|---|",
    ]
    for row in result.get("correlations", [])[:30]:
        lines.append(
            "| {family} | {factor} | {obs} | {mean:.4f} | {mean_abs:.4f} | {max_abs:.4f} | {klass} | {hard} | {source} | {blockers} |".format(
                family=row.get("reference_family", ""),
                factor=row.get("factor_name", ""),
                obs=row.get("correlation_observations", 0),
                mean=row.get("mean_correlation", 0.0),
                mean_abs=row.get("mean_abs_correlation", 0.0),
                max_abs=row.get("max_abs_correlation", 0.0),
                klass=row.get("redundancy_class", "unknown"),
                hard="yes" if row.get("hard_blocking_redundancy") else "no",
                source="yes" if row.get("source_lineage_redundancy") else "no",
                blockers=", ".join(row.get("blockers", [])) if row.get("blockers") else "none",
            )
        )
    lines.extend(
        [
            "",
            "## Capacity Audit",
            "",
            f"- Top quantile dates: {capacity.get('top_quantile_dates', 0)}",
            f"- Top quantile rows: {capacity.get('top_quantile_rows', 0)}",
            f"- Median amount: {capacity.get('median_amount', 0.0):.2f}",
            f"- Median ADV20 amount: {capacity.get('median_adv20_amount', 0.0):.2f}",
            f"- Amount breach count: {capacity.get('amount_breach_count', 0)}",
            f"- ADV20 breach count: {capacity.get('adv20_breach_count', 0)}",
            f"- Extreme abs-return >= 9.5% count: {capacity.get('extreme_abs_return_095_count', 0)}",
            f"- Extreme abs-return >= 20% count: {capacity.get('extreme_abs_return_020_count', 0)}",
            "",
            "## Gate Interpretation",
            "",
            f"- Blockers: {', '.join(gate.get('blockers', [])) if gate.get('blockers') else 'none'}",
            "- This stage cannot promote a factor; it only decides whether the lead deserves a cost/capacity bridge.",
        ]
    )
    return "\n".join(lines) + "\n"


def _family_frame(frame: pd.DataFrame, reference_family: str, sample_every_n_dates: int) -> pd.DataFrame:
    if frame.empty:
        return frame
    sampled = _sample_factor_dates(frame, sample_every_n_dates=sample_every_n_dates).copy()
    sampled["reference_family"] = reference_family
    return sampled


def _lead_correlations(
    frame: pd.DataFrame,
    *,
    lead_factor_name: str,
    min_cross_section: int,
    moderate_corr_threshold: float,
    high_corr_threshold: float,
    moderate_mean_abs_corr_threshold: float,
    high_mean_abs_corr_threshold: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if frame.empty or lead_factor_name not in set(frame.get("factor_name", [])):
        return [], []
    lead_frame = (
        frame[frame["factor_name"] == lead_factor_name][["date", "asset_id", "market", "factor_value"]]
        .rename(columns={"factor_value": "lead_value"})
        .copy()
    )
    rows: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    reference = frame[frame["factor_name"] != lead_factor_name]
    for (reference_family, factor_name), factor_group in reference.groupby(
        ["reference_family", "factor_name"], sort=True
    ):
        group = factor_group[["date", "asset_id", "market", "factor_value"]].merge(
            lead_frame,
            on=["date", "asset_id", "market"],
            how="inner",
        )
        corr_values: list[float] = []
        cross_sections: list[int] = []
        dates: list[pd.Timestamp] = []
        for signal_date, date_frame in group.groupby("date", sort=True):
            date_frame = date_frame.dropna(subset=["factor_value", "lead_value"])
            if len(date_frame) < min_cross_section:
                continue
            corr = _spearman(date_frame["factor_value"], date_frame["lead_value"])
            if not _is_finite(corr):
                continue
            corr_values.append(float(corr))
            cross_sections.append(int(len(date_frame)))
            dates.append(pd.Timestamp(signal_date))
            observations.append(
                {
                    "reference_family": str(reference_family),
                    "factor_name": str(factor_name),
                    "date": pd.Timestamp(signal_date).date().isoformat(),
                    "spearman_correlation": float(corr),
                    "cross_section": int(len(date_frame)),
                }
            )
        rows.append(
            _correlation_row(
                reference_family=str(reference_family),
                factor_name=str(factor_name),
                group=group,
                corr_values=corr_values,
                cross_sections=cross_sections,
                dates=dates,
                moderate_corr_threshold=moderate_corr_threshold,
                high_corr_threshold=high_corr_threshold,
                moderate_mean_abs_corr_threshold=moderate_mean_abs_corr_threshold,
                high_mean_abs_corr_threshold=high_mean_abs_corr_threshold,
            )
        )
    return sorted(rows, key=lambda row: (-row["max_abs_correlation"], -row["mean_abs_correlation"], row["factor_name"])), observations


def _correlation_row(
    *,
    reference_family: str,
    factor_name: str,
    group: pd.DataFrame,
    corr_values: list[float],
    cross_sections: list[int],
    dates: list[pd.Timestamp],
    moderate_corr_threshold: float,
    high_corr_threshold: float,
    moderate_mean_abs_corr_threshold: float,
    high_mean_abs_corr_threshold: float,
) -> dict[str, Any]:
    if not corr_values:
        return {
            "reference_family": reference_family,
            "factor_name": factor_name,
            "correlation_observations": 0,
            "mean_correlation": 0.0,
            "mean_abs_correlation": 0.0,
            "median_abs_correlation": 0.0,
            "max_abs_correlation": 0.0,
            "positive_correlation_rate": 0.0,
            "median_cross_section": 0.0,
            "unique_dates": 0,
            "unique_assets": int(group["asset_id"].nunique()) if "asset_id" in group else 0,
            "redundancy_class": "insufficient_overlap",
            "hard_blocking_redundancy": False,
            "source_lineage_redundancy": False,
            "blockers": ["insufficient_overlap_with_lead"],
        }
    series = pd.Series(corr_values, dtype=float)
    abs_series = series.abs()
    redundancy_class = _redundancy_class(
        max_abs_corr=float(abs_series.max()),
        mean_abs_corr=float(abs_series.mean()),
        moderate_corr_threshold=moderate_corr_threshold,
        high_corr_threshold=high_corr_threshold,
        moderate_mean_abs_corr_threshold=moderate_mean_abs_corr_threshold,
        high_mean_abs_corr_threshold=high_mean_abs_corr_threshold,
    )
    hard_block = reference_family in HARD_BLOCKING_REFERENCE_FAMILIES and redundancy_class == "highly_redundant"
    source_lineage = reference_family in SOURCE_LINEAGE_REFERENCE_FAMILIES and redundancy_class in {
        "highly_redundant",
        "moderately_redundant",
    }
    blockers = []
    if hard_block:
        blockers.append("hard_blocking_high_correlation_with_existing_reference")
    return {
        "reference_family": reference_family,
        "factor_name": factor_name,
        "correlation_observations": int(len(series)),
        "mean_correlation": float(series.mean()),
        "mean_abs_correlation": float(abs_series.mean()),
        "median_abs_correlation": float(abs_series.median()),
        "max_abs_correlation": float(abs_series.max()),
        "positive_correlation_rate": float((series > 0).mean()),
        "median_cross_section": float(pd.Series(cross_sections).median()) if cross_sections else 0.0,
        "unique_dates": int(len(set(dates))),
        "unique_assets": int(group["asset_id"].nunique()) if "asset_id" in group else 0,
        "redundancy_class": redundancy_class,
        "hard_blocking_redundancy": bool(hard_block),
        "source_lineage_redundancy": bool(source_lineage),
        "blockers": blockers,
    }


def _lead_capacity_audit(
    frame: pd.DataFrame,
    *,
    bars: pd.DataFrame | None,
    lead_factor_name: str,
    min_cross_section: int,
    min_signal_date_amount: float,
    extreme_abs_return_threshold: float,
    extreme_abs_return_rate_block_threshold: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    lead = frame[frame["factor_name"] == lead_factor_name].copy() if not frame.empty else pd.DataFrame()
    if lead.empty:
        return _empty_capacity_audit(extreme_abs_return_rate_block_threshold), []
    if bars is not None and not bars.empty:
        returns = _bar_returns(bars)
        lead = lead.merge(returns, on=["date", "asset_id", "market"], how="left")
    else:
        lead["return_1d"] = pd.NA
    observations: list[dict[str, Any]] = []
    top_rows: list[pd.DataFrame] = []
    for signal_date, date_frame in lead.groupby("date", sort=True):
        date_frame = date_frame.dropna(subset=["factor_value"])
        if len(date_frame) < min_cross_section:
            continue
        quantiles = _quantile_labels(date_frame["factor_value"])
        if quantiles is None:
            continue
        top = date_frame.loc[quantiles == 4].copy()
        if top.empty:
            continue
        top_rows.append(top)
        abs_return = pd.to_numeric(top.get("return_1d"), errors="coerce").abs()
        observations.append(
            {
                "date": pd.Timestamp(signal_date).date().isoformat(),
                "top_quantile_count": int(len(top)),
                "median_amount": _median(top.get("amount")),
                "median_adv20_amount": _median(top.get("adv20_amount")),
                "min_amount": _min_value(top.get("amount")),
                "min_adv20_amount": _min_value(top.get("adv20_amount")),
                "amount_breach_count": int((pd.to_numeric(top.get("amount"), errors="coerce") < min_signal_date_amount).sum()),
                "adv20_breach_count": int(
                    (pd.to_numeric(top.get("adv20_amount"), errors="coerce") < min_signal_date_amount).sum()
                ),
                "extreme_abs_return_095_count": int((abs_return >= extreme_abs_return_threshold).sum()),
                "extreme_abs_return_020_count": int((abs_return >= 0.20).sum()),
                "max_abs_return_1d": float(abs_return.max()) if abs_return.notna().any() else 0.0,
            }
        )
    if not top_rows:
        return _empty_capacity_audit(extreme_abs_return_rate_block_threshold), observations
    combined = pd.concat(top_rows, ignore_index=True)
    abs_return = pd.to_numeric(combined.get("return_1d"), errors="coerce").abs()
    return_audit_available = bool(abs_return.notna().any())
    extreme_095_count = int((abs_return >= extreme_abs_return_threshold).sum()) if return_audit_available else 0
    top_row_count = int(len(combined))
    extreme_rate = float(extreme_095_count / top_row_count) if top_row_count else 0.0
    amount_breach_count = int((pd.to_numeric(combined.get("amount"), errors="coerce") < min_signal_date_amount).sum())
    adv_breach_count = int((pd.to_numeric(combined.get("adv20_amount"), errors="coerce") < min_signal_date_amount).sum())
    blockers = []
    if amount_breach_count:
        blockers.append("top_quantile_signal_amount_breach")
    if adv_breach_count:
        blockers.append("top_quantile_adv20_amount_breach")
    if return_audit_available and extreme_rate > extreme_abs_return_rate_block_threshold:
        blockers.append("top_quantile_extreme_signal_date_return_rate_too_high")
    return (
        {
            "top_quantile_dates": int(len(observations)),
            "top_quantile_rows": top_row_count,
            "median_amount": _median(combined.get("amount")),
            "median_adv20_amount": _median(combined.get("adv20_amount")),
            "min_amount": _min_value(combined.get("amount")),
            "min_adv20_amount": _min_value(combined.get("adv20_amount")),
            "amount_breach_count": amount_breach_count,
            "adv20_breach_count": adv_breach_count,
            "return_audit_available": return_audit_available,
            "extreme_abs_return_095_count": extreme_095_count,
            "extreme_abs_return_095_rate": extreme_rate,
            "extreme_abs_return_020_count": int((abs_return >= 0.20).sum()) if return_audit_available else 0,
            "max_abs_return_1d": float(abs_return.max()) if return_audit_available else 0.0,
            "blockers": blockers,
        },
        observations,
    )


def _gate_blockers(
    frame: pd.DataFrame,
    lead_evidence: dict[str, Any],
    correlations: list[dict[str, Any]],
    capacity_audit: dict[str, Any],
    lead_factor_name: str,
) -> list[str]:
    blockers = []
    if frame.empty:
        blockers.append("factor_frame_empty")
    if lead_factor_name not in set(frame.get("factor_name", [])):
        blockers.append("lead_factor_missing")
    if not lead_evidence.get("prescreen_research_lead", False):
        blockers.append("prescreen_lead_not_confirmed")
    if any(row.get("hard_blocking_redundancy") for row in correlations):
        blockers.append("lead_highly_redundant_with_hard_blocking_reference")
    if capacity_audit.get("top_quantile_rows", 0) <= 0:
        blockers.append("lead_top_quantile_empty")
    blockers.extend(capacity_audit.get("blockers", []))
    return blockers


def _summary(
    frame: pd.DataFrame,
    correlations: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    lead_factor_name: str,
) -> dict[str, Any]:
    classes = [row.get("redundancy_class") for row in correlations]
    return {
        "candidate_count": int(frame[["reference_family", "factor_name"]].drop_duplicates().shape[0]) if not frame.empty else 0,
        "compared_candidate_count": int(len(correlations)),
        "correlation_observation_count": int(len(observations)),
        "highly_redundant_count": int(sum(1 for item in classes if item == "highly_redundant")),
        "moderately_redundant_count": int(sum(1 for item in classes if item == "moderately_redundant")),
        "unique_count": int(sum(1 for item in classes if item == "unique")),
        "hard_blocking_redundant_count": int(sum(1 for row in correlations if row.get("hard_blocking_redundancy"))),
        "source_lineage_redundant_count": int(sum(1 for row in correlations if row.get("source_lineage_redundancy"))),
        "lead_present": bool(not frame.empty and lead_factor_name in set(frame["factor_name"])),
    }


def _prescreen_lead_evidence(
    prescreen_report: dict[str, Any] | None,
    lead_factor_name: str,
    lead_horizon: int,
) -> dict[str, Any]:
    rows = prescreen_report.get("results", []) if isinstance(prescreen_report, dict) else []
    matches = [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("factor_name") == lead_factor_name
        and int(float(row.get("horizon", lead_horizon))) == int(lead_horizon)
    ]
    lead_row = matches[0] if matches else {}
    return {
        "prescreen_report_provided": isinstance(prescreen_report, dict),
        "lead_factor_name": lead_factor_name,
        "lead_horizon": int(lead_horizon),
        "prescreen_row_found": bool(matches),
        "prescreen_research_lead": bool(lead_row.get("research_lead", False)),
        "prescreen_blockers": _normalise_blockers(lead_row.get("blockers")),
    }


def _normalise_factor_frame(factor_frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "factor_name", "factor_value", "reference_family"]
    missing = [column for column in required if column not in factor_frame.columns]
    if missing:
        if factor_frame.empty:
            return pd.DataFrame(columns=required + ["amount", "adv20_amount"])
        raise ValueError(f"Factor frame is missing required columns: {', '.join(missing)}")
    frame = factor_frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str)
    frame["factor_name"] = frame["factor_name"].astype(str)
    frame["reference_family"] = frame["reference_family"].astype(str)
    frame["factor_value"] = pd.to_numeric(frame["factor_value"], errors="coerce")
    for column in ["amount", "adv20_amount"]:
        if column not in frame.columns:
            frame[column] = pd.NA
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["date", "asset_id", "market", "factor_name", "reference_family", "factor_value"])


def _bar_returns(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        return pd.DataFrame(columns=["date", "asset_id", "market", "return_1d"])
    frame = bars[required].copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str)
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    frame = frame.dropna(subset=required).sort_values(["asset_id", "market", "date"])
    frame["return_1d"] = frame.groupby(["asset_id", "market"], sort=False)["adj_close"].pct_change()
    return frame[["date", "asset_id", "market", "return_1d"]]


def _sample_factor_dates(factor_frame: pd.DataFrame, *, sample_every_n_dates: int) -> pd.DataFrame:
    if factor_frame.empty or sample_every_n_dates <= 1:
        return factor_frame
    frame = factor_frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    dates = sorted(frame["date"].dropna().unique())
    sampled_dates = set(dates[::sample_every_n_dates])
    return frame[frame["date"].isin(sampled_dates)].reset_index(drop=True)


def _redundancy_class(
    *,
    max_abs_corr: float,
    mean_abs_corr: float,
    moderate_corr_threshold: float,
    high_corr_threshold: float,
    moderate_mean_abs_corr_threshold: float,
    high_mean_abs_corr_threshold: float,
) -> str:
    if max_abs_corr >= high_corr_threshold or mean_abs_corr >= high_mean_abs_corr_threshold:
        return "highly_redundant"
    if max_abs_corr >= moderate_corr_threshold or mean_abs_corr >= moderate_mean_abs_corr_threshold:
        return "moderately_redundant"
    return "unique"


def _quantile_labels(values: pd.Series) -> pd.Series | None:
    try:
        return pd.qcut(values.rank(method="first"), 5, labels=False)
    except ValueError:
        return None


def _spearman(left: pd.Series, right: pd.Series) -> float:
    aligned = pd.concat([left, right], axis=1).dropna()
    if len(aligned) < 2:
        return float("nan")
    return float(aligned.iloc[:, 0].rank(method="average").corr(aligned.iloc[:, 1].rank(method="average")))


def _median(series: Any) -> float:
    values = pd.to_numeric(series, errors="coerce") if series is not None else pd.Series(dtype=float)
    return float(values.median()) if values.notna().any() else 0.0


def _min_value(series: Any) -> float:
    values = pd.to_numeric(series, errors="coerce") if series is not None else pd.Series(dtype=float)
    return float(values.min()) if values.notna().any() else 0.0


def _is_finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _empty_capacity_audit(extreme_abs_return_rate_block_threshold: float) -> dict[str, Any]:
    return {
        "top_quantile_dates": 0,
        "top_quantile_rows": 0,
        "median_amount": 0.0,
        "median_adv20_amount": 0.0,
        "min_amount": 0.0,
        "min_adv20_amount": 0.0,
        "amount_breach_count": 0,
        "adv20_breach_count": 0,
        "return_audit_available": False,
        "extreme_abs_return_095_count": 0,
        "extreme_abs_return_095_rate": 0.0,
        "extreme_abs_return_020_count": 0,
        "max_abs_return_1d": 0.0,
        "extreme_abs_return_rate_block_threshold": extreme_abs_return_rate_block_threshold,
        "blockers": ["lead_top_quantile_empty"],
    }


def _normalise_blockers(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item)]
    if value:
        return [item.strip() for item in str(value).split(",") if item.strip()]
    return []


def _load_prescreen_report(value: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return json.loads(Path(value).read_text(encoding="utf-8"))


def _data_window(bars: pd.DataFrame, factor_frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "min_signal_date": _min_date(factor_frame, "date"),
        "max_signal_date": _max_date(factor_frame, "date"),
        "bar_rows": int(len(bars)),
        "bar_assets": int(bars["asset_id"].nunique()) if not bars.empty else 0,
        "factor_rows": int(len(factor_frame)),
    }


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
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
