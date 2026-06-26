from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    _sanitize,
    _write_csv,
)
from quant_robot.ops.market_residual_lead_exposure_dedup import (
    IC_OBSERVATION_COLUMNS,
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
from quant_robot.ops.public_reference_multi_family_preregistration import SAFETY
from quant_robot.ops.public_reference_multi_family_prescreen import (
    _add_cross_sectional_features,
    _candidate_value_series,
    _feature_frame,
    _normalise_bars,
    load_public_reference_multi_family_bars,
)
from quant_robot.research.labels import make_forward_returns
from quant_robot.storage.factor_inputs import load_factor_inputs
from quant_robot.storage.moneyflow_inputs import load_moneyflow_inputs


STAGE = "alpha101_rank_pv_reversal_reference_dedup"
DEFAULT_LEAD_FACTOR_NAME = "alpha101_rank_pv_reversal_liquid_20"
DEFAULT_HORIZON = 20
ROUND128_SOURCE_REPORT = "docs/research/cn_stock_public_reference_multi_family_prescreen_round128_2026-06-22.md"
ROUND126_128_REVIEW = "docs/research/cn_stock_round126_128_three_round_review_2026-06-22.md"
NEXT_WALK_FORWARD_PREREGISTRATION_DIRECTION = (
    "round130_alpha101_rank_pv_reversal_walk_forward_cost_capacity_preregistration"
)
NEXT_HIBERNATE_OR_ORTHOGONALIZE_DIRECTION = (
    "round130_alpha101_rank_pv_reversal_hibernate_or_orthogonalize_after_dedup"
)
DEFAULT_REFERENCE_FACTOR_NAMES = (
    "pv_corr_reversal_capacity_safe_20",
    "pv_lowvol_reversal_blend_20",
    "bollinger_reversal_lowvol_liquid_20",
    "amount_stability_reversal_5_20",
    "alpha101_decay_reversal_amount_stability_10",
    "raw_neg_pv_corr_20",
    "raw_reversal_5",
    "raw_log_adv20",
    "raw_neg_realized_vol_20",
)
MONTHLY_IC_COLUMNS = ["month", "ic_observations", "mean_spearman_ic", "positive_ic_rate", "failure"]


def build_alpha101_rank_pv_reversal_reference_dedup(
    *,
    bars_roots: Iterable[str | Path],
    factor_input_root: str | Path,
    moneyflow_input_root: str | Path,
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
    bars = load_public_reference_multi_family_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    factor_inputs = load_factor_inputs(factor_input_root, "CN")
    moneyflow_inputs = load_moneyflow_inputs(moneyflow_input_root, "CN")
    result = build_alpha101_rank_pv_reversal_reference_dedup_from_frames(
        bars=bars,
        factor_inputs=factor_inputs,
        moneyflow_inputs=moneyflow_inputs,
        prescreen_report=report,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        lead_factor_name=lead_factor_name,
        horizon=horizon,
        execution_lag=execution_lag,
        sample_every_n_dates=sample_every_n_dates,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_signal_date_amount=min_signal_date_amount,
        reference_factor_names=reference_factor_names,
    )
    return result


def build_alpha101_rank_pv_reversal_reference_dedup_from_frames(
    *,
    bars: pd.DataFrame,
    factor_inputs: pd.DataFrame,
    moneyflow_inputs: pd.DataFrame,
    prescreen_report: dict[str, Any] | None,
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
    bars = _normalise_bars(bars)
    start = pd.Timestamp(analysis_start_date)
    end = pd.Timestamp(analysis_end_date)
    if include_final_holdout and not bars.empty:
        end = max(end, bars["date"].max())
    bars = bars[(bars["date"] >= start) & (bars["date"] <= end)].reset_index(drop=True)
    factor_frame, reference_frame, features = compute_alpha101_rank_pv_reversal_reference_frames(
        bars,
        factor_inputs=factor_inputs,
        moneyflow_inputs=moneyflow_inputs,
        lead_factor_name=lead_factor_name,
        reference_factor_names=reference_factor_names,
        min_signal_date_amount=min_signal_date_amount,
        reference_sample_every_n_dates=sample_every_n_dates,
    )
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=(horizon,),
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_alpha101_rank_pv_reversal_reference_dedup(
        factor_frame,
        labels,
        reference_factor_frame=reference_frame,
        prescreen_report=prescreen_report,
        lead_factor_name=lead_factor_name,
        horizon=horizon,
        sample_every_n_dates=sample_every_n_dates,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
    )
    result["data_window"] = _data_window(bars, features, factor_frame, reference_frame, labels)
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
        "ic_uses_all_dates": True,
    }
    result["markdown"] = render_alpha101_rank_pv_reversal_reference_dedup_markdown(result)
    return result


def compute_alpha101_rank_pv_reversal_reference_frames(
    bars: pd.DataFrame,
    *,
    factor_inputs: pd.DataFrame,
    moneyflow_inputs: pd.DataFrame,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    reference_factor_names: Sequence[str] = DEFAULT_REFERENCE_FACTOR_NAMES,
    min_signal_date_amount: float = 10_000_000,
    reference_sample_every_n_dates: int = 1,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    features = _feature_frame(bars, factor_inputs=factor_inputs, moneyflow_inputs=moneyflow_inputs)
    if features.empty:
        return _empty_factor_frame(), _empty_factor_frame(), features
    features = _add_cross_sectional_features(features)
    candidate_values = _candidate_value_series(features)
    if lead_factor_name not in candidate_values:
        raise ValueError(f"Unsupported lead factor: {lead_factor_name}")
    reference_values = _reference_value_series(features, candidate_values)
    allowed_references = {
        name: series
        for name, series in reference_values.items()
        if name in set(reference_factor_names) and name != lead_factor_name
    }
    lead = _series_to_factor_frame(
        features,
        {lead_factor_name: candidate_values[lead_factor_name]},
        min_signal_date_amount=min_signal_date_amount,
    )
    reference_features = _sample_feature_dates(features, sample_every_n_dates=reference_sample_every_n_dates)
    reference_values_for_sample = {name: series.loc[reference_features.index] for name, series in allowed_references.items()}
    references = _series_to_factor_frame(
        reference_features,
        reference_values_for_sample,
        min_signal_date_amount=min_signal_date_amount,
    )
    return lead, references, features


def _sample_feature_dates(features: pd.DataFrame, *, sample_every_n_dates: int) -> pd.DataFrame:
    if features.empty or sample_every_n_dates <= 1:
        return features
    dates = pd.Index(sorted(features["date"].dropna().unique()))
    keep_dates = set(dates[::sample_every_n_dates])
    return features[features["date"].isin(keep_dates)]


def summarize_alpha101_rank_pv_reversal_reference_dedup(
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
) -> dict[str, Any]:
    lead = _normalise_factor_frame(factor_frame)
    lead = lead[lead["factor_name"] == lead_factor_name].reset_index(drop=True)
    reference_frame = _normalise_factor_frame(reference_factor_frame if reference_factor_frame is not None else pd.DataFrame())
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
        high_corr_threshold=0.85,
        high_mean_abs_corr_threshold=0.70,
        moderate_corr_threshold=0.70,
        moderate_mean_abs_corr_threshold=0.50,
    )
    lead_evidence = _round128_lead_evidence(
        prescreen_report,
        lead_factor_name=lead_factor_name,
        horizon=horizon,
    )
    blockers = _gate_blockers(
        lead,
        lead_evidence=lead_evidence,
        lead_ic_summary=lead_ic_summary,
        yearly_ic=yearly_ic,
        reference_correlations=reference_correlations,
    )
    high_redundant_count = int(
        sum(1 for row in reference_correlations if row["redundancy_class"] == "highly_redundant")
    )
    moderate_redundant_count = int(
        sum(1 for row in reference_correlations if row["redundancy_class"] == "moderately_redundant")
    )
    next_direction = (
        NEXT_WALK_FORWARD_PREREGISTRATION_DIRECTION
        if not blockers
        else NEXT_HIBERNATE_OR_ORTHOGONALIZE_DIRECTION
    )
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "lead_factor_name": lead_factor_name,
        "horizon": int(horizon),
        "source_context": {
            "source_prescreen": ROUND128_SOURCE_REPORT,
            "source_audit": ROUND126_128_REVIEW,
            "round128_lead_requires_reference_dedup_before_portfolio_grid": True,
        },
        "lead_evidence": lead_evidence,
        "lead_ic_summary": lead_ic_summary,
        "summary": {
            "lead_rows": int(len(lead)),
            "reference_factor_count": int(reference_frame["factor_name"].nunique()) if not reference_frame.empty else 0,
            "reference_highly_redundant_count": high_redundant_count,
            "reference_moderately_redundant_count": moderate_redundant_count,
            "yearly_failure_count": int(sum(1 for row in yearly_ic if row["failure"])),
            "monthly_failure_count": int(sum(1 for row in monthly_ic if row["failure"])),
            "promotion_allowed_candidates": 0,
            "portfolio_grid_allowed_candidates": 0,
        },
        "thresholds": {
            "high_corr_threshold": 0.85,
            "high_mean_abs_corr_threshold": 0.70,
            "moderate_corr_threshold": 0.70,
            "moderate_mean_abs_corr_threshold": 0.50,
            "min_cross_section": min_cross_section,
            "min_ic_observations": min_ic_observations,
        },
        "gate": {
            "blockers": blockers,
            "required_before": [
                "round128_public_reference_multi_family_prescreen_read",
                "round128_three_horizons_are_one_unique_factor",
                "alpha101_rank_pv_reversal_reference_dedup_before_portfolio_grid",
                "cost_capacity_regime_walk_forward_required_before_promotion",
            ],
            "allowed_next_directions": [
                NEXT_WALK_FORWARD_PREREGISTRATION_DIRECTION,
                NEXT_HIBERNATE_OR_ORTHOGONALIZE_DIRECTION,
            ],
            "drawdown_policy": "Drawdown tolerance can relax MaxDD filters, but it cannot waive redundancy, cost, capacity, or walk-forward gates.",
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed": False,
            "reason": "Round129 is a lead de-duplication audit only; promotion requires separate cost, capacity, regime, and walk-forward validation.",
        },
        "next_direction": next_direction,
        "reference_correlations": reference_correlations,
        "yearly_ic": yearly_ic,
        "monthly_ic": monthly_ic,
        "ic_observations": ic_observations,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_alpha101_rank_pv_reversal_reference_dedup_markdown(result)
    return result


def write_alpha101_rank_pv_reversal_reference_dedup(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "alpha101_rank_pv_reversal_reference_dedup.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "alpha101_rank_pv_reversal_reference_dedup.md").write_text(
        render_alpha101_rank_pv_reversal_reference_dedup_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "alpha101_rank_pv_reversal_reference_correlations.csv",
        result.get("reference_correlations", []),
        REFERENCE_CORRELATION_COLUMNS,
    )
    _write_csv(output_path / "alpha101_rank_pv_reversal_yearly_ic.csv", result.get("yearly_ic", []), YEARLY_IC_COLUMNS)
    _write_csv(output_path / "alpha101_rank_pv_reversal_monthly_ic.csv", result.get("monthly_ic", []), MONTHLY_IC_COLUMNS)
    _write_csv(
        output_path / "alpha101_rank_pv_reversal_ic_observations.csv",
        result.get("ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )


def render_alpha101_rank_pv_reversal_reference_dedup_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lead_ic = result.get("lead_ic_summary", {})
    evidence = result.get("lead_evidence", {})
    gate = result.get("gate", {})
    lines = [
        "# Alpha101 Rank PV Reversal Reference Dedup",
        "",
        "## Summary",
        "",
        f"- Lead: `{result.get('lead_factor_name', DEFAULT_LEAD_FACTOR_NAME)}` horizon {result.get('horizon')}",
        f"- Round128 research lead rows: {evidence.get('round128_research_lead_rows', 0)}",
        f"- Round128 unique lead factors: {evidence.get('round128_unique_lead_factor_count', 0)}",
        f"- Lead rows: {summary.get('lead_rows', 0)}",
        f"- IC observations: {lead_ic.get('ic_observations', 0)}",
        f"- Mean IC: {lead_ic.get('mean_spearman_ic', 0.0):.4f}",
        f"- ICIR: {lead_ic.get('icir', 0.0):.3f}",
        f"- IC t-stat: {lead_ic.get('ic_t_stat', 0.0):.2f}",
        f"- Positive IC rate: {lead_ic.get('positive_ic_rate', 0.0):.1%}",
        f"- Highly redundant references: {summary.get('reference_highly_redundant_count', 0)}",
        f"- Moderately redundant references: {summary.get('reference_moderately_redundant_count', 0)}",
        f"- Yearly failures: {summary.get('yearly_failure_count', 0)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Portfolio grid allowed: {result.get('promotion_policy', {}).get('portfolio_grid_allowed', False)}",
        f"- Next direction: `{result.get('next_direction')}`",
        "",
        "## Reference Correlations",
        "",
        "| Factor | Obs | Mean | Mean Abs | Median Abs | Max Abs | Class | Blockers |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("reference_correlations", []):
        lines.append(
            "| {name} | {obs} | {mean:.4f} | {mean_abs:.4f} | {median_abs:.4f} | {max_abs:.4f} | {klass} | {blockers} |".format(
                name=row.get("factor_name"),
                obs=row.get("correlation_observations", 0),
                mean=row.get("mean_correlation", 0.0),
                mean_abs=row.get("mean_abs_correlation", 0.0),
                median_abs=row.get("median_abs_correlation", 0.0),
                max_abs=row.get("max_abs_correlation", 0.0),
                klass=row.get("redundancy_class", "unknown"),
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
            f"- Promotion reason: {result.get('promotion_policy', {}).get('reason', '')}",
            f"- Safety: {result.get('safety', '')}",
            "",
        ]
    )
    return "\n".join(lines)


def _reference_value_series(features: pd.DataFrame, candidate_values: dict[str, pd.Series]) -> dict[str, pd.Series]:
    return {
        "pv_corr_reversal_capacity_safe_20": -0.70 * features["z_pv_corr_20"] + 0.30 * features["z_log_adv20"],
        "pv_lowvol_reversal_blend_20": (
            0.45 * features["z_reversal_5"] - 0.35 * features["z_pv_corr_20"] + 0.20 * features["z_neg_realized_vol_20"]
        ),
        "bollinger_reversal_lowvol_liquid_20": (
            0.55 * features["z_bollinger_reversal_20"]
            + 0.25 * features["z_neg_realized_vol_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "amount_stability_reversal_5_20": (
            0.50 * features["z_reversal_5"]
            + 0.30 * features["z_neg_abs_amount_z_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "alpha101_decay_reversal_amount_stability_10": candidate_values["alpha101_decay_reversal_amount_stability_10"],
        "raw_neg_pv_corr_20": -features["z_pv_corr_20"],
        "raw_reversal_5": features["z_reversal_5"],
        "raw_log_adv20": features["z_log_adv20"],
        "raw_neg_realized_vol_20": features["z_neg_realized_vol_20"],
    }


def _series_to_factor_frame(
    features: pd.DataFrame,
    values_by_name: dict[str, pd.Series],
    *,
    min_signal_date_amount: float,
) -> pd.DataFrame:
    rows = []
    base_columns = ["date", "asset_id", "market", "amount", "adv20_amount"]
    base = features[base_columns].copy()
    capacity_mask = pd.to_numeric(base["adv20_amount"], errors="coerce") >= min_signal_date_amount
    for factor_name, values in values_by_name.items():
        frame = base.copy()
        frame["factor_name"] = factor_name
        frame["factor_value"] = pd.to_numeric(values, errors="coerce")
        frame = frame[capacity_mask].dropna(subset=["date", "asset_id", "market", "factor_value"])
        rows.append(frame)
    if not rows:
        return _empty_factor_frame()
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def _round128_lead_evidence(
    prescreen_report: dict[str, Any] | None,
    *,
    lead_factor_name: str,
    horizon: int,
) -> dict[str, Any]:
    results = list((prescreen_report or {}).get("results", []))
    lead_rows = [
        row
        for row in results
        if row.get("factor_name") == lead_factor_name and bool(row.get("research_lead", False))
    ]
    horizon_row = next((row for row in lead_rows if int(row.get("horizon", horizon)) == int(horizon)), None)
    unique_leads = sorted({str(row.get("factor_name")) for row in lead_rows})
    return {
        "prescreen_report_present": bool(prescreen_report),
        "prescreen_research_lead": bool(horizon_row),
        "round128_research_lead_rows": int(len(lead_rows)),
        "round128_unique_lead_factor_count": int(len(unique_leads)),
        "round128_unique_lead_factors": unique_leads,
        "round128_total_candidate_count": int((prescreen_report or {}).get("summary", {}).get("candidate_count", 0)),
        "round128_factor_horizon_test_count": int(
            (prescreen_report or {}).get("summary", {}).get(
                "test_count",
                (prescreen_report or {}).get("summary", {}).get("result_count", 0),
            )
        ),
        "round128_summary_research_lead_count": int((prescreen_report or {}).get("summary", {}).get("research_lead_count", 0)),
    }


def _gate_blockers(
    lead_frame: pd.DataFrame,
    *,
    lead_evidence: dict[str, Any],
    lead_ic_summary: dict[str, Any],
    yearly_ic: list[dict[str, Any]],
    reference_correlations: list[dict[str, Any]],
) -> list[str]:
    blockers = []
    if lead_frame.empty:
        blockers.append("lead_factor_frame_empty")
    if not lead_evidence.get("prescreen_research_lead", False):
        blockers.append("round128_prescreen_lead_not_confirmed")
    if lead_evidence.get("round128_unique_lead_factor_count") != 1:
        blockers.append("round128_unique_lead_factor_count_not_one")
    if lead_evidence.get("round128_research_lead_rows", 0) > 1:
        blockers.append("round128_multi_horizon_leads_not_independent")
    if not lead_ic_summary.get("minimum_observation_gate_passed", False):
        blockers.append("lead_ic_observations_below_threshold")
    if any(row["redundancy_class"] == "highly_redundant" for row in reference_correlations):
        blockers.append("lead_highly_redundant_with_reference_factor")
    if any(row.get("failure") for row in yearly_ic):
        blockers.append("yearly_ic_instability")
    return blockers


def _data_window(
    bars: pd.DataFrame,
    features: pd.DataFrame,
    factor_frame: pd.DataFrame,
    reference_frame: pd.DataFrame,
    labels: pd.DataFrame,
) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "bar_rows": int(len(bars)),
        "asset_count": int(bars["asset_id"].nunique()) if "asset_id" in bars else 0,
        "feature_rows": int(len(features)),
        "lead_factor_rows": int(len(factor_frame)),
        "reference_factor_rows": int(len(reference_frame)),
        "label_rows": int(len(labels)),
        "min_factor_date": _min_date(factor_frame, "date"),
        "max_factor_date": _max_date(factor_frame, "date"),
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
            "asset_id",
            "market",
            "factor_name",
            "factor_value",
            "amount",
            "adv20_amount",
        ]
    )
