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
from quant_robot.ops.daily_basic_non_price_public_carry_preregistration import (
    SAFETY,
    DailyBasicNonPricePublicCarryCandidateSpec,
    default_daily_basic_non_price_public_carry_specs,
)
from quant_robot.ops.daily_basic_non_price_public_carry_prescreen import (
    _capacity_frame,
    _data_window,
    _feature_frame,
    _sanitize,
    attach_daily_basic_capacity_fields,
    compute_daily_basic_non_price_public_carry_factors,
    load_daily_basic_non_price_public_carry_inputs,
)
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


STAGE = "daily_basic_non_price_public_carry_lead_dedup"
DEFAULT_LEAD_FACTOR_NAME = "daily_basic_free_float_supply_quality_20"
DEFAULT_HORIZON = 20
NEXT_PORTFOLIO_PREFLIGHT_DIRECTION = "round134_daily_basic_free_float_supply_quality_portfolio_conversion_preflight"
NEXT_STABILITY_AUDIT_DIRECTION = "round134_daily_basic_free_float_supply_quality_residual_stability_audit"
ROTATE_AFTER_DEDUP_FAILURE_DIRECTION = "round134_daily_basic_non_price_carry_family_rotation_after_dedup_failure"
SOFT_STABILITY_BLOCKERS = {
    "twenty_fifteen_regime_failure_unexplained",
    "raw_yearly_ic_instability",
    "residual_yearly_ic_instability",
}
DEFAULT_RESIDUAL_EXPOSURES = (
    "log_circ_mv",
    "log_total_mv",
    "inv_pb",
    "dv_ttm",
    "log_adv20_amount",
)
THESIS_EXPOSURES = {
    "free_share_to_total_share",
    "float_share_to_total_share",
    "free_share_to_float_share",
}
IMPLEMENTATION_EXPOSURES = {
    "inv_pb",
    "dv_ttm",
    "inv_ps_ttm",
    "log_circ_mv",
    "log_total_mv",
    "volume_ratio_z_20",
    "log_adv20_amount",
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


def build_daily_basic_non_price_public_carry_lead_dedup(
    *,
    bars_roots: Iterable[str | Path],
    daily_basic_roots: Iterable[str | Path],
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
    specs = default_daily_basic_non_price_public_carry_specs()
    lead_specs = _select_specs(specs, [lead_factor_name])
    reference_specs = [spec for spec in specs if spec.factor_name != lead_factor_name]
    lead_frame = compute_daily_basic_non_price_public_carry_factors(daily_basic, candidate_specs=lead_specs)
    lead_frame = attach_daily_basic_capacity_fields(lead_frame, bars)
    reference_frame = compute_daily_basic_non_price_public_carry_factors(daily_basic, candidate_specs=reference_specs)
    reference_frame = attach_daily_basic_capacity_fields(reference_frame, bars)
    exposure_frame = build_daily_basic_lead_exposure_frame(daily_basic, bars)
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=(horizon,),
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_daily_basic_non_price_public_carry_lead_dedup(
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
    window = _data_window(bars, daily_basic, lead_frame, labels)
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
        "capacity_is_hard_gate_before_portfolio_conversion": True,
    }
    result["sampling_policy"] = {
        "sample_every_n_dates": sample_every_n_dates,
        "sampling_used_for_correlations_only": True,
        "raw_and_residual_ic_use_all_dates": True,
    }
    result["markdown"] = render_daily_basic_non_price_public_carry_lead_dedup_markdown(result)
    return result


def summarize_daily_basic_non_price_public_carry_lead_dedup(
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
    lead = _normalise_lead(factor_frame, lead_factor_name=lead_factor_name)
    reference = _normalise_reference(reference_factor_frame if reference_factor_frame is not None else pd.DataFrame())
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
    exposure_correlations = _daily_basic_exposure_correlations(
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
    raw_yearly_ic = _period_ic(raw_ic_observations, period="year")
    raw_monthly_ic = _period_ic(raw_ic_observations, period="month")
    raw_ic_summary = _lead_ic_summary(raw_ic_observations, min_ic_observations=min_ic_observations)
    residual_frame = residualize_daily_basic_lead(
        lead_with_exposures,
        exposure_names=residual_exposure_names,
        residual_factor_name=f"{lead_factor_name}_implementation_residual",
        min_cross_section=min_cross_section,
    )
    residual_ic_observations = _lead_ic_observations(
        residual_frame,
        labels,
        lead_factor_name=f"{lead_factor_name}_implementation_residual",
        horizon=horizon,
        min_cross_section=min_cross_section,
    )
    residual_yearly_ic = _period_ic(residual_ic_observations, period="year")
    residual_monthly_ic = _period_ic(residual_ic_observations, period="month")
    residual_ic_summary = _lead_ic_summary(residual_ic_observations, min_ic_observations=min_ic_observations)
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
        "lead_evidence": prescreen_evidence,
        "raw_ic_summary": raw_ic_summary,
        "residual_ic_summary": residual_ic_summary,
        "summary": {
            "lead_rows": int(len(lead)),
            "reference_factor_count": int(reference["factor_name"].nunique()) if not reference.empty else 0,
            "reference_highly_redundant_count": int(
                sum(1 for row in reference_correlations if row.get("redundancy_class") == "highly_redundant")
            ),
            "high_implementation_exposure_count": int(
                sum(
                    1
                    for row in exposure_correlations
                    if row.get("exposure_role") == "implementation" and row.get("exposure_class") == "high_exposure"
                )
            ),
            "high_thesis_exposure_count": int(
                sum(
                    1
                    for row in exposure_correlations
                    if row.get("exposure_role") == "thesis" and row.get("exposure_class") == "high_exposure"
                )
            ),
            "raw_yearly_failure_count": int(sum(1 for row in raw_yearly_ic if row.get("failure"))),
            "residual_yearly_failure_count": int(sum(1 for row in residual_yearly_ic if row.get("failure"))),
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
                "round133_daily_basic_free_float_supply_quality_dedup_after_round132_lead",
                "daily_basic_reference_correlation_gate_before_portfolio_conversion",
                "daily_basic_size_value_liquidity_residual_ic_gate",
                "drawdown_tolerance_does_not_waive_capacity_or_residual_gates",
            ],
            "drawdown_policy": (
                "User can tolerate roughly 30% drawdown, but drawdown tolerance does not waive capacity, "
                "tradeability, redundancy, implementation exposure, or residual IC gates."
            ),
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_conversion_candidate": portfolio_conversion_candidate,
            "portfolio_grid_allowed": portfolio_conversion_candidate,
            "reason": (
                "Round133 is a dedup and residual-alpha preflight only. Promotion still requires costed "
                "portfolio conversion, walk-forward, regime, capacity, and final holdout gates."
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
    result["markdown"] = render_daily_basic_non_price_public_carry_lead_dedup_markdown(result)
    return result


def build_daily_basic_lead_exposure_frame(daily_basic: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    features = _feature_frame(daily_basic)
    if features.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market"])
    exposure_columns = [
        "date",
        "asset_id",
        "market",
        "free_share_to_total_share",
        "float_share_to_total_share",
        "free_share_to_float_share",
        "inv_pb",
        "dv_ttm",
        "inv_ps_ttm",
        "log_circ_mv",
        "log_total_mv",
        "volume_ratio_z_20",
    ]
    existing = [column for column in exposure_columns if column in features.columns]
    exposure = features[existing].copy()
    capacity = _capacity_frame(bars)
    if not capacity.empty:
        capacity = capacity.copy()
        capacity["log_adv20_amount"] = np.log(pd.to_numeric(capacity["adv20_amount"], errors="coerce").where(capacity["adv20_amount"] > 0))
        exposure = exposure.merge(
            capacity[["date", "asset_id", "market", "adv20_amount", "log_adv20_amount"]],
            on=["date", "asset_id", "market"],
            how="left",
            validate="many_to_one",
        )
    return exposure.replace([float("inf"), float("-inf")], pd.NA)


def residualize_daily_basic_lead(
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


def write_daily_basic_non_price_public_carry_lead_dedup(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "daily_basic_non_price_public_carry_lead_dedup.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "daily_basic_non_price_public_carry_lead_dedup.md").write_text(
        render_daily_basic_non_price_public_carry_lead_dedup_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "daily_basic_lead_reference_correlations.csv",
        result.get("reference_correlations", []),
        REFERENCE_CORRELATION_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_lead_exposure_correlations.csv",
        result.get("exposure_correlations", []),
        EXPOSURE_CORRELATION_COLUMNS,
    )
    _write_csv(output_path / "daily_basic_lead_raw_yearly_ic.csv", result.get("raw_yearly_ic", []), YEARLY_IC_COLUMNS)
    _write_csv(output_path / "daily_basic_lead_raw_monthly_ic.csv", result.get("raw_monthly_ic", []), MONTHLY_IC_COLUMNS)
    _write_csv(
        output_path / "daily_basic_lead_raw_ic_observations.csv",
        result.get("raw_ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_lead_residual_yearly_ic.csv",
        result.get("residual_yearly_ic", []),
        YEARLY_IC_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_lead_residual_monthly_ic.csv",
        result.get("residual_monthly_ic", []),
        MONTHLY_IC_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_lead_residual_ic_observations.csv",
        result.get("residual_ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )


def render_daily_basic_non_price_public_carry_lead_dedup_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    raw_ic = result.get("raw_ic_summary", {})
    residual_ic = result.get("residual_ic_summary", {})
    gate = result.get("gate", {})
    lines = [
        "# Daily-Basic Non-Price Public Carry Lead Dedup",
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
        f"- Highly redundant references: {summary.get('reference_highly_redundant_count', 0)}",
        f"- High implementation exposures: {summary.get('high_implementation_exposure_count', 0)}",
        f"- High thesis exposures: {summary.get('high_thesis_exposure_count', 0)}",
        f"- Portfolio conversion candidate: {result.get('promotion_policy', {}).get('portfolio_conversion_candidate', False)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Next direction: `{result.get('next_direction')}`",
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
            "| Exposure | Role | Obs | Mean | Mean Abs | Max Abs | Class | Blockers |",
            "|---|---|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in result.get("exposure_correlations", []):
        lines.append(
            "| {name} | {role} | {obs} | {mean:.4f} | {mean_abs:.4f} | {max_abs:.4f} | {klass} | {blockers} |".format(
                name=row.get("exposure_name"),
                role=row.get("exposure_role", "implementation"),
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


def _daily_basic_exposure_correlations(
    lead_frame: pd.DataFrame,
    *,
    min_cross_section: int,
    high_exposure_corr_threshold: float,
    high_exposure_mean_abs_corr_threshold: float,
) -> list[dict[str, Any]]:
    if lead_frame.empty:
        return []
    exposure_names = [
        "free_share_to_total_share",
        "float_share_to_total_share",
        "free_share_to_float_share",
        "inv_pb",
        "dv_ttm",
        "inv_ps_ttm",
        "log_circ_mv",
        "log_total_mv",
        "volume_ratio_z_20",
        "log_adv20_amount",
    ]
    rows = []
    for exposure_name in exposure_names:
        if exposure_name not in lead_frame:
            continue
        role = "thesis" if exposure_name in THESIS_EXPOSURES else "implementation"
        row = _correlation_row(
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


def _correlation_row(
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
            "blockers": ["insufficient_exposure_overlap_with_lead"],
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
    if klass == "high_exposure" and role == "implementation":
        blockers.append("high_implementation_exposure_correlation")
    elif klass == "moderate_exposure" and role == "implementation":
        blockers.append("moderate_implementation_exposure_correlation")
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
        blockers.append("prescreen_lead_not_confirmed")
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
        blockers.append("lead_highly_redundant_with_daily_basic_reference")
    if any(
        row.get("exposure_role") == "implementation" and row.get("exposure_class") == "high_exposure"
        for row in exposure_correlations
    ):
        blockers.append("lead_high_implementation_exposure")
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
    hard_blockers = [blocker for blocker in blockers if blocker not in SOFT_STABILITY_BLOCKERS]
    residual_metrics_pass = (
        residual_ic_summary.get("minimum_observation_gate_passed", False)
        and residual_ic_summary.get("mean_spearman_ic", 0.0) >= min_residual_mean_ic
        and residual_ic_summary.get("icir", 0.0) >= min_residual_icir
        and residual_ic_summary.get("positive_ic_rate", 0.0) >= min_residual_positive_ic_rate
    )
    if not hard_blockers and residual_metrics_pass:
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


def _normalise_lead(frame: pd.DataFrame, *, lead_factor_name: str) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])
    normalised = frame.copy()
    normalised["date"] = pd.to_datetime(normalised["date"])
    normalised["asset_id"] = normalised["asset_id"].astype(str)
    normalised["market"] = normalised["market"].astype(str)
    normalised["factor_name"] = normalised["factor_name"].astype(str)
    normalised["factor_value"] = pd.to_numeric(normalised["factor_value"], errors="coerce")
    lead = normalised[normalised["factor_name"] == lead_factor_name].copy()
    for column in ["amount", "adv20_amount"]:
        if column in lead:
            lead[column] = pd.to_numeric(lead[column], errors="coerce")
    return lead.sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def _normalise_reference(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])
    normalised = frame.copy()
    normalised["date"] = pd.to_datetime(normalised["date"])
    normalised["asset_id"] = normalised["asset_id"].astype(str)
    normalised["market"] = normalised["market"].astype(str)
    normalised["factor_name"] = normalised["factor_name"].astype(str)
    normalised["factor_value"] = pd.to_numeric(normalised["factor_value"], errors="coerce")
    return normalised.sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def _normalise_exposure_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market"])
    normalised = frame.copy()
    normalised["date"] = pd.to_datetime(normalised["date"])
    normalised["asset_id"] = normalised["asset_id"].astype(str)
    normalised["market"] = normalised["market"].astype(str)
    for column in list(THESIS_EXPOSURES | IMPLEMENTATION_EXPOSURES):
        if column in normalised:
            normalised[column] = pd.to_numeric(normalised[column], errors="coerce")
    return normalised.drop_duplicates(["date", "asset_id", "market"], keep="last").reset_index(drop=True)


def _merge_lead_exposures(lead: pd.DataFrame, exposure_frame: pd.DataFrame) -> pd.DataFrame:
    if lead.empty or exposure_frame.empty:
        return lead.copy()
    exposure_columns = ["date", "asset_id", "market"] + [
        column for column in list(THESIS_EXPOSURES | IMPLEMENTATION_EXPOSURES) if column in exposure_frame.columns
    ]
    return lead.merge(
        exposure_frame[exposure_columns],
        on=["date", "asset_id", "market"],
        how="left",
        validate="many_to_one",
    )


def _select_specs(
    specs: Sequence[DailyBasicNonPricePublicCarryCandidateSpec],
    factor_names: Sequence[str],
) -> list[DailyBasicNonPricePublicCarryCandidateSpec]:
    allowed = set(factor_names)
    return [spec for spec in specs if spec.factor_name in allowed]


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


def _normalise_blockers(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item)]
    if value:
        return [item.strip() for item in str(value).split(",") if item.strip()]
    return []


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


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
