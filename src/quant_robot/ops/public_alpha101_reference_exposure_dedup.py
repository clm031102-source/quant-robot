from __future__ import annotations

from datetime import date
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
    _data_window,
    _sanitize,
    compute_capacity_safe_price_volume_factors,
)
from quant_robot.ops.market_residual_lead_exposure_dedup import (
    EXPOSURE_CORRELATION_COLUMNS,
    IC_OBSERVATION_COLUMNS,
    MONTHLY_IC_COLUMNS,
    REFERENCE_CORRELATION_COLUMNS,
    YEARLY_IC_COLUMNS,
    _exposure_correlations,
    _filter_dates,
    _gate_blockers,
    _lead_ic_observations,
    _lead_ic_summary,
    _load_report,
    _period_ic,
    _prescreen_evidence,
    _reference_correlations,
    _sample_dates,
    _write_csv,
)
from quant_robot.ops.market_residual_risk_premia_preregistration import (
    default_market_residual_risk_premia_candidate_specs,
)
from quant_robot.ops.market_residual_risk_premia_prescreen import compute_market_residual_risk_premia_factors
from quant_robot.ops.public_alpha101_capacity_safe_preregistration import default_public_alpha101_candidate_specs
from quant_robot.ops.public_alpha101_capacity_safe_prescreen import (
    load_public_alpha101_bars,
    compute_public_alpha101_capacity_safe_factors,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "public_alpha101_reference_exposure_dedup"
DEFAULT_LEAD_FACTOR_NAME = "qlib_alpha158_return_std_position_blend_20"
DEFAULT_HORIZON = 5
NEXT_REVIEW_DIRECTION = "round117_round114_116_three_round_review_before_next_action"
POST_REVIEW_BRIDGE_DIRECTION = "round117_public_alpha101_cost_capacity_walk_forward_bridge_after_review"
POST_REVIEW_ROTATE_DIRECTION = "round117_family_rotation_after_public_alpha101_lead_audit"
DEFAULT_REFERENCE_FACTOR_NAMES = (
    "pv_lowvol_reversal_blend_20",
    "range_contraction_lowvol_reversal_20",
    "bollinger_reversal_lowvol_liquid_20",
    "rsi_reversal_lowvol_liquid_14_20",
    "amount_stability_reversal_5_20",
    "donchian_pullback_lowvol_liquid_20",
)


def build_public_alpha101_reference_exposure_dedup(
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
    bars = load_public_alpha101_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    lead_frame = compute_public_alpha101_capacity_safe_factors(
        bars,
        candidate_specs=_lead_specs(lead_factor_name),
        min_signal_date_amount=min_signal_date_amount,
    )
    reference_frame = compute_capacity_safe_price_volume_factors(
        bars,
        candidate_specs=_reference_specs(reference_factor_names),
        min_signal_date_amount=min_signal_date_amount,
    )
    exposure_frame = _exposure_frame_from_bars(bars, min_signal_date_amount=min_signal_date_amount)
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=(horizon,),
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_public_alpha101_reference_exposure_dedup(
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
    window = _data_window(bars, lead_frame, labels)
    result["data_window"] = window | {
        "min_factor_date": window.get("min_signal_date"),
        "max_factor_date": window.get("max_signal_date"),
        "factor_rows": int(len(lead_frame)),
        "reference_factor_rows": int(len(reference_frame)),
        "exposure_rows": int(len(exposure_frame)),
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
    result["markdown"] = render_public_alpha101_reference_exposure_dedup_markdown(result)
    return result


def summarize_public_alpha101_reference_exposure_dedup(
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
) -> dict[str, Any]:
    lead = _normalise_lead_with_exposures(factor_frame, exposure_frame, lead_factor_name=lead_factor_name)
    reference_frame = _normalise_reference(reference_factor_frame if reference_factor_frame is not None else pd.DataFrame())
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
        high_corr_threshold=0.85,
        high_mean_abs_corr_threshold=0.70,
        moderate_corr_threshold=0.70,
        moderate_mean_abs_corr_threshold=0.50,
    )
    exposure_correlations = _exposure_correlations(
        sampled_lead,
        min_cross_section=min_cross_section,
        high_exposure_corr_threshold=0.85,
        high_exposure_mean_abs_corr_threshold=0.60,
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
        "gate": {
            "blockers": blockers,
            "required_before": [
                "round116_public_alpha101_reference_exposure_dedup_after_round115_lead",
                "alpha101_capacity_turnover_redundancy_gate_before_portfolio_grid",
                "alpha101_inverse_direction_requires_new_preregistration",
            ],
            "drawdown_policy": "Drawdown tolerance is not a capacity, exposure, redundancy, or stability waiver.",
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed": False,
            "reason": "Round116 is a redundancy and exposure audit only; cost, capacity, regime, and walk-forward gates remain required.",
        },
        "next_direction": NEXT_REVIEW_DIRECTION,
        "recommended_post_review_direction": (
            POST_REVIEW_BRIDGE_DIRECTION if not blockers else POST_REVIEW_ROTATE_DIRECTION
        ),
        "reference_correlations": reference_correlations,
        "exposure_correlations": exposure_correlations,
        "yearly_ic": yearly_ic,
        "monthly_ic": monthly_ic,
        "ic_observations": ic_observations,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_public_alpha101_reference_exposure_dedup_markdown(result)
    return result


def write_public_alpha101_reference_exposure_dedup(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "public_alpha101_reference_exposure_dedup.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "public_alpha101_reference_exposure_dedup.md").write_text(
        render_public_alpha101_reference_exposure_dedup_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "public_alpha101_reference_correlations.csv",
        result.get("reference_correlations", []),
        REFERENCE_CORRELATION_COLUMNS,
    )
    _write_csv(
        output_path / "public_alpha101_exposure_correlations.csv",
        result.get("exposure_correlations", []),
        EXPOSURE_CORRELATION_COLUMNS,
    )
    _write_csv(output_path / "public_alpha101_yearly_ic.csv", result.get("yearly_ic", []), YEARLY_IC_COLUMNS)
    _write_csv(output_path / "public_alpha101_monthly_ic.csv", result.get("monthly_ic", []), MONTHLY_IC_COLUMNS)
    _write_csv(
        output_path / "public_alpha101_ic_observations.csv",
        result.get("ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )


def render_public_alpha101_reference_exposure_dedup_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lead_ic = result.get("lead_ic_summary", {})
    gate = result.get("gate", {})
    lines = [
        "# Public Alpha101 Reference Exposure Dedup",
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
        f"- Monthly failures: {summary.get('monthly_failure_count', 0)}",
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
    return [spec for spec in default_public_alpha101_candidate_specs() if spec.factor_name == lead_factor_name]


def _reference_specs(reference_factor_names: Sequence[str]) -> list[Any]:
    allowed = set(reference_factor_names)
    return [spec for spec in default_capacity_safe_price_volume_candidate_specs() if spec.factor_name in allowed]


def _exposure_frame_from_bars(bars: pd.DataFrame, *, min_signal_date_amount: float) -> pd.DataFrame:
    exposure_spec = [spec for spec in default_market_residual_risk_premia_candidate_specs() if spec.factor_name == "low_beta_120"]
    exposure_rows = compute_market_residual_risk_premia_factors(
        bars,
        candidate_specs=exposure_spec,
        min_signal_date_amount=min_signal_date_amount,
    )
    columns = [
        "date",
        "asset_id",
        "market",
        "beta_120",
        "downside_beta_120",
        "market_corr_60",
        "residual_vol_60",
        "adv20_amount",
    ]
    existing = [column for column in columns if column in exposure_rows.columns]
    return exposure_rows[existing].drop_duplicates(["date", "asset_id", "market"], keep="last")


def _normalise_lead_with_exposures(
    factor_frame: pd.DataFrame,
    exposure_frame: pd.DataFrame | None,
    *,
    lead_factor_name: str,
) -> pd.DataFrame:
    if factor_frame.empty:
        return factor_frame.copy()
    lead = factor_frame[factor_frame["factor_name"] == lead_factor_name].copy()
    if exposure_frame is not None and not exposure_frame.empty:
        exposure = exposure_frame.copy()
        exposure["date"] = pd.to_datetime(exposure["date"])
        exposure["asset_id"] = exposure["asset_id"].astype(str)
        exposure["market"] = exposure["market"].astype(str)
        merge_columns = [
            "date",
            "asset_id",
            "market",
            "beta_120",
            "downside_beta_120",
            "market_corr_60",
            "residual_vol_60",
        ]
        if "adv20_amount" in exposure and "adv20_amount" not in lead:
            merge_columns.append("adv20_amount")
        lead = lead.merge(
            exposure[[column for column in merge_columns if column in exposure.columns]],
            on=["date", "asset_id", "market"],
            how="left",
            validate="many_to_one",
        )
    return lead


def _normalise_reference(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])
    reference = frame.copy()
    reference["date"] = pd.to_datetime(reference["date"])
    reference["asset_id"] = reference["asset_id"].astype(str)
    reference["market"] = reference["market"].astype(str)
    reference["factor_name"] = reference["factor_name"].astype(str)
    reference["factor_value"] = pd.to_numeric(reference["factor_value"], errors="coerce")
    return reference
