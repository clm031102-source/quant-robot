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
    _spearman,
)
from quant_robot.ops.public_reference_multi_family_prescreen import (
    _sanitize,
    load_public_reference_multi_family_bars,
)
from quant_robot.ops.public_technical_failure_reversal_preregistration import SAFETY
from quant_robot.ops.public_technical_failure_reversal_prescreen import (
    _candidate_value_series,
    _technical_feature_frame,
)


STAGE = "public_technical_failure_reversal_neutral_dedup"
DEFAULT_LEAD_FACTOR_NAME = "inverse_rsrs_slope_failure_liquid_18_60"
DEFAULT_HORIZON = 5
ROUND155_SOURCE_REPORT = "docs/research/cn_stock_public_technical_failure_reversal_prescreen_round155_2026-06-23.md"
NEXT_PORTFOLIO_PREFLIGHT_DIRECTION = "round157_public_technical_failure_reversal_walk_forward_cost_capacity_preflight"
NEXT_INCREMENTAL_RESIDUAL_DIRECTION = "round157_public_technical_failure_reversal_incremental_residual_research"
ROTATE_AFTER_NEUTRAL_DEDUP_FAILURE_DIRECTION = "round157_rotate_after_public_technical_failure_reversal_neutral_dedup_failure"
DEFAULT_RESIDUAL_EXPOSURES = (
    "log_adv20_amount",
    "log_amount",
    "realized_vol_20",
    "amount_trend_20_60",
)
DEFAULT_EXPOSURE_COLUMNS = (
    "log_adv20_amount",
    "log_amount",
    "realized_vol_20",
    "amount_trend_20_60",
    "return_20",
)
DEFAULT_REFERENCE_FACTOR_NAMES = (
    "rsrs_slope_acceleration_quality_18_60",
    "rsrs_slope_inverse_raw_18_60",
    "rsrs_residual_extreme_reversal_repair_18",
    "donchian_breakout_failure_reference_20",
    "price_efficiency_failure_reference_20",
    "volume_price_resonance_failure_reference_20_60",
    "kbar_momentum_failure_reference_20",
)
SOFT_STABILITY_BLOCKERS = {
    "raw_yearly_ic_instability",
    "industry_neutral_yearly_ic_instability",
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


def build_public_technical_failure_reversal_neutral_dedup(
    *,
    bars_roots: Iterable[str | Path],
    stock_basic_path: str | Path | None,
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
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
    min_industry_neutral_mean_ic: float = 0.02,
    min_industry_neutral_icir: float = 0.20,
    min_industry_neutral_positive_ic_rate: float = 0.55,
    min_residual_mean_ic: float = 0.02,
    min_residual_icir: float = 0.20,
    min_residual_positive_ic_rate: float = 0.55,
) -> dict[str, Any]:
    report = _load_report(prescreen_report)
    bars = load_public_reference_multi_family_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    stock_basic = _load_stock_basic(stock_basic_path) if stock_basic_path is not None else pd.DataFrame()
    features = _technical_feature_frame(bars, horizons=(int(horizon),), execution_lag=execution_lag)
    lead_frame = build_public_technical_failure_reversal_lead_frame(
        features,
        stock_basic,
        lead_factor_name=lead_factor_name,
        min_signal_date_amount=min_signal_date_amount,
    )
    reference_frame = build_public_technical_failure_reversal_reference_frame(features)
    exposure_frame = build_public_technical_failure_reversal_exposure_frame(features, stock_basic)
    labels = build_public_technical_failure_reversal_labels(features, horizon=horizon)
    result = summarize_public_technical_failure_reversal_neutral_dedup(
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
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
        min_industry_neutral_mean_ic=min_industry_neutral_mean_ic,
        min_industry_neutral_icir=min_industry_neutral_icir,
        min_industry_neutral_positive_ic_rate=min_industry_neutral_positive_ic_rate,
        min_residual_mean_ic=min_residual_mean_ic,
        min_residual_icir=min_residual_icir,
        min_residual_positive_ic_rate=min_residual_positive_ic_rate,
    )
    result["data_window"] = _data_window(bars, lead_frame, reference_frame, exposure_frame, labels)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_neutral_dedup_walk_forward_cost_capacity_clearance_only",
    }
    result["capacity_policy"] = {
        "min_signal_date_amount": min_signal_date_amount,
        "adv20_amount_filter_enabled": True,
        "portfolio_grid_blocked_before_round156_completion": True,
    }
    result["sampling_policy"] = {
        "sample_every_n_dates": sample_every_n_dates,
        "sampling_used_for_correlations_only": True,
        "raw_industry_residual_ic_use_all_dates": True,
    }
    result["markdown"] = render_public_technical_failure_reversal_neutral_dedup_markdown(result)
    return result


def summarize_public_technical_failure_reversal_neutral_dedup(
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
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
    min_industry_neutral_mean_ic: float = 0.02,
    min_industry_neutral_icir: float = 0.20,
    min_industry_neutral_positive_ic_rate: float = 0.55,
    min_residual_mean_ic: float = 0.02,
    min_residual_icir: float = 0.20,
    min_residual_positive_ic_rate: float = 0.55,
    residual_exposure_names: Sequence[str] = DEFAULT_RESIDUAL_EXPOSURES,
    exposure_names: Sequence[str] = DEFAULT_EXPOSURE_COLUMNS,
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
    exposure_correlations = _technical_exposure_correlations(
        sampled_lead,
        exposure_names=exposure_names,
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
    industry_factor_name = f"{lead_factor_name}_industry_neutral"
    industry_neutral_frame = industry_neutralize_technical_lead(
        lead_with_exposures,
        industry_factor_name=industry_factor_name,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
    )
    industry_ic_observations = _lead_ic_observations(
        industry_neutral_frame,
        labels,
        lead_factor_name=industry_factor_name,
        horizon=horizon,
        min_cross_section=min_cross_section,
    )
    industry_ic_summary = _lead_ic_summary(industry_ic_observations, min_ic_observations=min_ic_observations)
    industry_yearly_ic = _period_ic(industry_ic_observations, period="year")
    industry_monthly_ic = _period_ic(industry_ic_observations, period="month")
    residual_factor_name = f"{lead_factor_name}_industry_size_liquidity_residual"
    residual_frame = residualize_technical_lead(
        industry_neutral_frame,
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
    industry_coverage = _industry_coverage(lead_with_exposures, min_assets_per_industry=min_assets_per_industry)
    blockers = _gate_blockers(
        lead,
        prescreen_evidence=prescreen_evidence,
        raw_ic_summary=raw_ic_summary,
        industry_neutral_ic_summary=industry_ic_summary,
        residual_ic_summary=residual_ic_summary,
        raw_yearly_ic=raw_yearly_ic,
        industry_neutral_yearly_ic=industry_yearly_ic,
        residual_yearly_ic=residual_yearly_ic,
        reference_correlations=reference_correlations,
        exposure_correlations=exposure_correlations,
        industry_coverage=industry_coverage,
        min_industries=min_industries,
        min_industry_neutral_mean_ic=min_industry_neutral_mean_ic,
        min_industry_neutral_icir=min_industry_neutral_icir,
        min_industry_neutral_positive_ic_rate=min_industry_neutral_positive_ic_rate,
        min_residual_mean_ic=min_residual_mean_ic,
        min_residual_icir=min_residual_icir,
        min_residual_positive_ic_rate=min_residual_positive_ic_rate,
    )
    portfolio_preflight_candidate = not blockers
    next_direction = _next_direction(
        blockers,
        industry_neutral_ic_summary=industry_ic_summary,
        residual_ic_summary=residual_ic_summary,
        min_industry_neutral_mean_ic=min_industry_neutral_mean_ic,
        min_industry_neutral_icir=min_industry_neutral_icir,
        min_industry_neutral_positive_ic_rate=min_industry_neutral_positive_ic_rate,
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
            "source_prescreen": ROUND155_SOURCE_REPORT,
            "round155_single_lead_requires_neutral_dedup_before_portfolio_grid": True,
            "portfolio_grid_blocked_at_this_stage": True,
        },
        "lead_evidence": prescreen_evidence,
        "raw_ic_summary": raw_ic_summary,
        "industry_neutral_ic_summary": industry_ic_summary,
        "residual_ic_summary": residual_ic_summary,
        "summary": {
            "lead_rows": int(len(lead)),
            "industry_neutral_rows": int(len(industry_neutral_frame)),
            "residual_rows": int(len(residual_frame)),
            "reference_factor_count": int(reference["factor_name"].nunique()) if not reference.empty else 0,
            "reference_highly_redundant_count": int(
                sum(row.get("redundancy_class") == "highly_redundant" for row in reference_correlations)
            ),
            "style_exposure_high_count": int(
                sum(row.get("exposure_class") == "high_exposure" for row in exposure_correlations)
            ),
            "raw_yearly_failure_count": int(sum(row.get("failure") for row in raw_yearly_ic)),
            "industry_neutral_yearly_failure_count": int(sum(row.get("failure") for row in industry_yearly_ic)),
            "residual_yearly_failure_count": int(sum(row.get("failure") for row in residual_yearly_ic)),
            "industry_coverage": industry_coverage,
            "promotion_allowed_candidates": 0,
            "portfolio_preflight_candidates": int(portfolio_preflight_candidate),
        },
        "thresholds": {
            "min_cross_section": min_cross_section,
            "min_ic_observations": min_ic_observations,
            "min_industries": min_industries,
            "min_assets_per_industry": min_assets_per_industry,
            "min_industry_neutral_mean_ic": min_industry_neutral_mean_ic,
            "min_industry_neutral_icir": min_industry_neutral_icir,
            "min_industry_neutral_positive_ic_rate": min_industry_neutral_positive_ic_rate,
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
            "exposure_names": list(exposure_names),
        },
        "gate": {
            "blockers": blockers,
            "required_before": [
                "round155_public_technical_failure_reversal_prescreen_read",
                "round155_single_rsrs_failure_reversal_research_lead_confirmed",
                "industry_neutral_ic_gate",
                "size_liquidity_volatility_residual_ic_gate",
                "public_technical_reference_correlation_gate",
                "no_public_technical_failure_reversal_portfolio_grid_before_round156",
            ],
            "drawdown_policy": (
                "User drawdown tolerance can affect later portfolio interpretation, but cannot waive "
                "industry, size, liquidity, volatility, reference redundancy, cost, capacity, or walk-forward gates."
            ),
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_preflight_candidate": portfolio_preflight_candidate,
            "portfolio_grid_allowed": False,
            "reason": (
                "Round156 is a neutralization and reference de-duplication audit. Even a surviving lead must next "
                "pass walk-forward, costs, capacity, regime, and final-holdout gates."
            ),
        },
        "next_direction": next_direction,
        "reference_correlations": reference_correlations,
        "exposure_correlations": exposure_correlations,
        "raw_yearly_ic": raw_yearly_ic,
        "raw_monthly_ic": raw_monthly_ic,
        "raw_ic_observations": raw_ic_observations,
        "industry_neutral_yearly_ic": industry_yearly_ic,
        "industry_neutral_monthly_ic": industry_monthly_ic,
        "industry_neutral_ic_observations": industry_ic_observations,
        "residual_yearly_ic": residual_yearly_ic,
        "residual_monthly_ic": residual_monthly_ic,
        "residual_ic_observations": residual_ic_observations,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_public_technical_failure_reversal_neutral_dedup_markdown(result)
    return result


def build_public_technical_failure_reversal_lead_frame(
    features: pd.DataFrame,
    stock_basic: pd.DataFrame | None,
    *,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    min_signal_date_amount: float = 10_000_000,
) -> pd.DataFrame:
    if features.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])
    values = _candidate_value_series(features).get(lead_factor_name)
    if values is None:
        return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])
    capacity_mask = (
        (features["amount"] >= min_signal_date_amount)
        & (features["adv20_amount"] >= min_signal_date_amount)
        & (features["return_1d"].abs() <= 0.50)
    )
    columns = ["date", "asset_id", "market", "amount", "adv20_amount"]
    lead = features.loc[capacity_mask, columns].copy()
    lead["factor_name"] = lead_factor_name
    lead["factor_value"] = values.loc[capacity_mask]
    lead = lead.dropna(subset=["factor_value", "amount", "adv20_amount"])
    lead = _merge_stock_basic_industry(lead, stock_basic)
    return lead.sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def build_public_technical_failure_reversal_reference_frame(features: pd.DataFrame) -> pd.DataFrame:
    if features.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])
    base = features[["date", "asset_id", "market", "amount", "adv20_amount"]].copy()
    references = {
        "rsrs_slope_acceleration_quality_18_60": (
            0.45 * features["z_rsrs_slope_18"]
            + 0.30 * features["z_rsrs_slope_delta_60"]
            + 0.15 * features["z_neg_realized_vol_20"]
            + 0.10 * features["z_log_adv20"]
        ),
        "rsrs_slope_inverse_raw_18_60": (
            -0.45 * features["z_rsrs_slope_18"] - 0.30 * features["z_rsrs_slope_delta_60"]
        ),
        "rsrs_residual_extreme_reversal_repair_18": (
            -0.55 * features["z_rsrs_residual_z_18"]
            + 0.25 * features["z_neg_realized_vol_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "donchian_breakout_failure_reference_20": (
            -0.45 * features["z_donchian_position_20"] - 0.30 * features["z_return_efficiency_20"]
        ),
        "price_efficiency_failure_reference_20": (
            -0.50 * features["z_return_efficiency_20"] - 0.25 * features["z_return_20"]
        ),
        "volume_price_resonance_failure_reference_20_60": (
            -0.40 * features["z_return_20"] - 0.30 * features["z_amount_trend_20_60"]
        ),
        "kbar_momentum_failure_reference_20": (
            -0.40 * features["z_kbar_close_position_20"] - 0.35 * features["z_skip5_momentum_20"]
        ),
    }
    rows = []
    for name, values in references.items():
        frame = base.copy()
        frame["factor_name"] = name
        frame["factor_value"] = pd.to_numeric(values, errors="coerce")
        rows.append(frame.dropna(subset=["factor_value"]))
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def build_public_technical_failure_reversal_exposure_frame(
    features: pd.DataFrame,
    stock_basic: pd.DataFrame | None,
) -> pd.DataFrame:
    if features.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market"])
    exposure = features[
        [
            "date",
            "asset_id",
            "market",
            "amount",
            "adv20_amount",
            "log_adv20",
            "realized_vol_20",
            "amount_trend_20_60",
            "return_20",
        ]
    ].rename(columns={"log_adv20": "log_adv20_amount"})
    exposure["log_amount"] = np.log(pd.to_numeric(exposure["amount"], errors="coerce").where(exposure["amount"] > 0))
    exposure = _merge_stock_basic_industry(exposure, stock_basic)
    return exposure.replace([float("inf"), float("-inf")], pd.NA).reset_index(drop=True)


def build_public_technical_failure_reversal_labels(features: pd.DataFrame, *, horizon: int) -> pd.DataFrame:
    column = f"forward_return_{int(horizon)}"
    if features.empty or column not in features:
        return pd.DataFrame(columns=["date", "asset_id", "market", "horizon", "forward_return"])
    labels = features[["date", "asset_id", "market", column]].rename(columns={column: "forward_return"}).copy()
    labels["horizon"] = int(horizon)
    return labels.dropna(subset=["forward_return"]).reset_index(drop=True)


def industry_neutralize_technical_lead(
    lead_frame: pd.DataFrame,
    *,
    industry_factor_name: str,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
) -> pd.DataFrame:
    if lead_frame.empty or "industry" not in lead_frame:
        return pd.DataFrame(columns=list(lead_frame.columns) if not lead_frame.empty else ["date", "asset_id", "market", "factor_name", "factor_value"])
    frame = lead_frame.copy()
    rows = []
    for _, group in frame.groupby("date", sort=True):
        group = group.copy()
        valid = group.dropna(subset=["factor_value", "industry"])
        industry_counts = valid.groupby("industry")["asset_id"].nunique()
        good_industries = industry_counts[industry_counts >= min_assets_per_industry].index
        valid = valid[valid["industry"].isin(good_industries)]
        output = group.copy()
        output["factor_name"] = industry_factor_name
        output["factor_value"] = np.nan
        if len(good_industries) < min_industries or valid.empty:
            rows.append(output)
            continue
        neutral = valid["factor_value"] - valid.groupby("industry")["factor_value"].transform("mean")
        output.loc[valid.index, "factor_value"] = neutral
        rows.append(output)
    result = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if result.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])
    return result.dropna(subset=["factor_value"]).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def residualize_technical_lead(
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
        output = group.copy()
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
        x = clean[list(exposure_names)].to_numpy(dtype=float)
        x = np.column_stack([np.ones(len(x)), x])
        y = clean["factor_value"].to_numpy(dtype=float)
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


def write_public_technical_failure_reversal_neutral_dedup(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "public_technical_failure_reversal_neutral_dedup.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "public_technical_failure_reversal_neutral_dedup.md").write_text(
        render_public_technical_failure_reversal_neutral_dedup_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "public_technical_failure_reversal_reference_correlations.csv",
        result.get("reference_correlations", []),
        REFERENCE_CORRELATION_COLUMNS,
    )
    _write_csv(
        output_path / "public_technical_failure_reversal_exposure_correlations.csv",
        result.get("exposure_correlations", []),
        EXPOSURE_CORRELATION_COLUMNS,
    )
    _write_csv(output_path / "public_technical_failure_reversal_raw_yearly_ic.csv", result.get("raw_yearly_ic", []), YEARLY_IC_COLUMNS)
    _write_csv(output_path / "public_technical_failure_reversal_raw_monthly_ic.csv", result.get("raw_monthly_ic", []), MONTHLY_IC_COLUMNS)
    _write_csv(
        output_path / "public_technical_failure_reversal_raw_ic_observations.csv",
        result.get("raw_ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )
    _write_csv(
        output_path / "public_technical_failure_reversal_industry_neutral_yearly_ic.csv",
        result.get("industry_neutral_yearly_ic", []),
        YEARLY_IC_COLUMNS,
    )
    _write_csv(
        output_path / "public_technical_failure_reversal_industry_neutral_ic_observations.csv",
        result.get("industry_neutral_ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )
    _write_csv(
        output_path / "public_technical_failure_reversal_residual_yearly_ic.csv",
        result.get("residual_yearly_ic", []),
        YEARLY_IC_COLUMNS,
    )
    _write_csv(
        output_path / "public_technical_failure_reversal_residual_ic_observations.csv",
        result.get("residual_ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )


def render_public_technical_failure_reversal_neutral_dedup_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    raw_ic = result.get("raw_ic_summary", {})
    industry_ic = result.get("industry_neutral_ic_summary", {})
    residual_ic = result.get("residual_ic_summary", {})
    gate = result.get("gate", {})
    lines = [
        "# Public Technical Failure-Reversal Neutral Dedup Round156",
        "",
        "## Summary",
        "",
        f"- Lead: `{result.get('lead_factor_name')}` horizon {result.get('horizon')}",
        f"- Lead rows: {summary.get('lead_rows', 0)}",
        f"- Raw mean IC: {raw_ic.get('mean_spearman_ic', 0.0):.4f}",
        f"- Raw ICIR: {raw_ic.get('icir', 0.0):.3f}",
        f"- Raw IC observations: {raw_ic.get('ic_observations', 0)}",
        f"- Industry-neutral mean IC: {industry_ic.get('mean_spearman_ic', 0.0):.4f}",
        f"- Industry-neutral ICIR: {industry_ic.get('icir', 0.0):.3f}",
        f"- Residual mean IC: {residual_ic.get('mean_spearman_ic', 0.0):.4f}",
        f"- Residual ICIR: {residual_ic.get('icir', 0.0):.3f}",
        f"- Highly redundant references: {summary.get('reference_highly_redundant_count', 0)}",
        f"- High style exposures: {summary.get('style_exposure_high_count', 0)}",
        f"- Portfolio preflight candidate: {result.get('promotion_policy', {}).get('portfolio_preflight_candidate', False)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Next direction: `{result.get('next_direction')}`",
        "",
        "## Public Technical Reference Correlations",
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
            "## Style Exposure Correlations",
            "",
            "| Exposure | Role | Obs | Mean | Mean Abs | Max Abs | Class | Blockers |",
            "|---|---|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in result.get("exposure_correlations", []):
        lines.append(
            "| {name} | {role} | {obs} | {mean:.4f} | {mean_abs:.4f} | {max_abs:.4f} | {klass} | {blockers} |".format(
                name=row.get("exposure_name"),
                role=row.get("exposure_role", "style_exposure"),
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


def _technical_exposure_correlations(
    lead_frame: pd.DataFrame,
    *,
    exposure_names: Sequence[str],
    min_cross_section: int,
    high_exposure_corr_threshold: float,
    high_exposure_mean_abs_corr_threshold: float,
) -> list[dict[str, Any]]:
    if lead_frame.empty:
        return []
    rows = []
    for exposure_name in sorted(dict.fromkeys(exposure_names)):
        if exposure_name not in lead_frame:
            continue
        group = lead_frame[["date", "asset_id", "market", "factor_value", exposure_name]].rename(
            columns={exposure_name: "exposure_value"}
        )
        rows.append(
            _exposure_correlation_row(
                group,
                name=exposure_name,
                role=_exposure_role(exposure_name),
                min_cross_section=min_cross_section,
                high_corr_threshold=high_exposure_corr_threshold,
                high_mean_abs_corr_threshold=high_exposure_mean_abs_corr_threshold,
            )
        )
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
            "blockers": ["insufficient_style_exposure_overlap_with_lead"],
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
        blockers.append("high_size_liquidity_or_volatility_exposure_correlation")
    elif klass == "moderate_exposure":
        blockers.append("moderate_size_liquidity_or_volatility_exposure_correlation")
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
    industry_neutral_ic_summary: dict[str, Any],
    residual_ic_summary: dict[str, Any],
    raw_yearly_ic: list[dict[str, Any]],
    industry_neutral_yearly_ic: list[dict[str, Any]],
    residual_yearly_ic: list[dict[str, Any]],
    reference_correlations: list[dict[str, Any]],
    exposure_correlations: list[dict[str, Any]],
    industry_coverage: dict[str, Any],
    min_industries: int,
    min_industry_neutral_mean_ic: float,
    min_industry_neutral_icir: float,
    min_industry_neutral_positive_ic_rate: float,
    min_residual_mean_ic: float,
    min_residual_icir: float,
    min_residual_positive_ic_rate: float,
) -> list[str]:
    blockers = []
    if lead_frame.empty:
        blockers.append("lead_factor_frame_empty")
    if not prescreen_evidence.get("prescreen_research_lead", False):
        blockers.append("round155_prescreen_lead_not_confirmed")
    if not raw_ic_summary.get("minimum_observation_gate_passed", False):
        blockers.append("raw_ic_observations_below_threshold")
    if not industry_coverage.get("industry_metadata_present", False):
        blockers.append("industry_metadata_missing")
    if int(industry_coverage.get("median_industries", 0)) < min_industries:
        blockers.append("industry_breadth_below_threshold")
    if not industry_neutral_ic_summary.get("minimum_observation_gate_passed", False):
        blockers.append("industry_neutral_ic_observations_below_threshold")
    if industry_neutral_ic_summary.get("mean_spearman_ic", 0.0) < min_industry_neutral_mean_ic:
        blockers.append("industry_neutral_mean_ic_below_threshold")
    if industry_neutral_ic_summary.get("icir", 0.0) < min_industry_neutral_icir:
        blockers.append("industry_neutral_icir_below_threshold")
    if industry_neutral_ic_summary.get("positive_ic_rate", 0.0) < min_industry_neutral_positive_ic_rate:
        blockers.append("industry_neutral_positive_ic_rate_below_threshold")
    if not residual_ic_summary.get("minimum_observation_gate_passed", False):
        blockers.append("residual_ic_observations_below_threshold")
    if residual_ic_summary.get("mean_spearman_ic", 0.0) < min_residual_mean_ic:
        blockers.append("residual_mean_ic_below_threshold")
    if residual_ic_summary.get("icir", 0.0) < min_residual_icir:
        blockers.append("residual_icir_below_threshold")
    if residual_ic_summary.get("positive_ic_rate", 0.0) < min_residual_positive_ic_rate:
        blockers.append("residual_positive_ic_rate_below_threshold")
    if any(row.get("redundancy_class") == "highly_redundant" for row in reference_correlations):
        blockers.append("lead_highly_redundant_with_public_technical_reference")
    if any(row.get("exposure_class") == "high_exposure" for row in exposure_correlations):
        blockers.append("lead_high_size_liquidity_or_volatility_exposure")
    yearly_rows = raw_yearly_ic + industry_neutral_yearly_ic + residual_yearly_ic
    if any(row.get("year") == 2015 and row.get("failure") for row in yearly_rows):
        blockers.append("twenty_fifteen_regime_failure_unexplained")
    if any(row.get("failure") for row in raw_yearly_ic):
        blockers.append("raw_yearly_ic_instability")
    if any(row.get("failure") for row in industry_neutral_yearly_ic):
        blockers.append("industry_neutral_yearly_ic_instability")
    if any(row.get("failure") for row in residual_yearly_ic):
        blockers.append("residual_yearly_ic_instability")
    return _dedupe(blockers)


def _next_direction(
    blockers: list[str],
    *,
    industry_neutral_ic_summary: dict[str, Any],
    residual_ic_summary: dict[str, Any],
    min_industry_neutral_mean_ic: float,
    min_industry_neutral_icir: float,
    min_industry_neutral_positive_ic_rate: float,
    min_residual_mean_ic: float,
    min_residual_icir: float,
    min_residual_positive_ic_rate: float,
) -> str:
    if not blockers:
        return NEXT_PORTFOLIO_PREFLIGHT_DIRECTION
    industry_pass = (
        industry_neutral_ic_summary.get("minimum_observation_gate_passed", False)
        and industry_neutral_ic_summary.get("mean_spearman_ic", 0.0) >= min_industry_neutral_mean_ic
        and industry_neutral_ic_summary.get("icir", 0.0) >= min_industry_neutral_icir
        and industry_neutral_ic_summary.get("positive_ic_rate", 0.0) >= min_industry_neutral_positive_ic_rate
    )
    residual_pass = (
        residual_ic_summary.get("minimum_observation_gate_passed", False)
        and residual_ic_summary.get("mean_spearman_ic", 0.0) >= min_residual_mean_ic
        and residual_ic_summary.get("icir", 0.0) >= min_residual_icir
        and residual_ic_summary.get("positive_ic_rate", 0.0) >= min_residual_positive_ic_rate
    )
    hard_blockers = [blocker for blocker in blockers if blocker not in SOFT_STABILITY_BLOCKERS]
    dedup_only_blockers = {
        "lead_highly_redundant_with_public_technical_reference",
        "lead_high_size_liquidity_or_volatility_exposure",
    }
    if industry_pass and residual_pass and hard_blockers and all(blocker in dedup_only_blockers for blocker in hard_blockers):
        return NEXT_INCREMENTAL_RESIDUAL_DIRECTION
    return ROTATE_AFTER_NEUTRAL_DEDUP_FAILURE_DIRECTION


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


def _normalise_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value"])
    normalised = frame.copy()
    normalised["date"] = pd.to_datetime(normalised["date"])
    normalised["asset_id"] = normalised["asset_id"].astype(str)
    normalised["market"] = normalised["market"].astype(str)
    normalised["factor_name"] = normalised["factor_name"].astype(str)
    normalised["factor_value"] = pd.to_numeric(normalised["factor_value"], errors="coerce")
    for column in ["amount", "adv20_amount", "log_adv20_amount", "log_amount", "realized_vol_20", "amount_trend_20_60", "return_20"]:
        if column in normalised:
            normalised[column] = pd.to_numeric(normalised[column], errors="coerce")
    if "industry" in normalised:
        normalised["industry"] = normalised["industry"].astype(str)
    return normalised.sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def _normalise_exposure_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market"])
    normalised = frame.copy()
    normalised["date"] = pd.to_datetime(normalised["date"])
    normalised["asset_id"] = normalised["asset_id"].astype(str)
    normalised["market"] = normalised["market"].astype(str)
    for column in ["amount", "adv20_amount", *DEFAULT_EXPOSURE_COLUMNS, *DEFAULT_RESIDUAL_EXPOSURES]:
        if column in normalised:
            normalised[column] = pd.to_numeric(normalised[column], errors="coerce")
    if "industry" in normalised:
        normalised["industry"] = normalised["industry"].astype(str)
    return normalised.drop_duplicates(["date", "asset_id", "market"], keep="last").reset_index(drop=True)


def _merge_lead_exposures(lead: pd.DataFrame, exposure_frame: pd.DataFrame) -> pd.DataFrame:
    if lead.empty:
        return lead.copy()
    output = lead.copy()
    if exposure_frame.empty:
        return output
    exposure_columns = ["date", "asset_id", "market"] + [
        column
        for column in ["industry", "amount", "adv20_amount", *DEFAULT_EXPOSURE_COLUMNS, *DEFAULT_RESIDUAL_EXPOSURES]
        if column in exposure_frame.columns and column not in output.columns
    ]
    if len(exposure_columns) <= 3:
        return output
    return output.merge(
        exposure_frame[exposure_columns],
        on=["date", "asset_id", "market"],
        how="left",
        validate="many_to_one",
    )


def _merge_stock_basic_industry(frame: pd.DataFrame, stock_basic: pd.DataFrame | None) -> pd.DataFrame:
    output = frame.copy()
    if stock_basic is None or stock_basic.empty or "asset_id" not in stock_basic or "industry" not in stock_basic:
        if "industry" not in output:
            output["industry"] = pd.NA
        return output
    basic = stock_basic[["asset_id", "industry"]].copy()
    basic["asset_id"] = basic["asset_id"].astype(str)
    basic["industry"] = basic["industry"].astype(str)
    basic = basic.drop_duplicates("asset_id", keep="last")
    if "industry" in output:
        output = output.drop(columns=["industry"])
    return output.merge(basic, on="asset_id", how="left", validate="many_to_one")


def _industry_coverage(frame: pd.DataFrame, *, min_assets_per_industry: int) -> dict[str, Any]:
    if frame.empty or "industry" not in frame:
        return {
            "industry_metadata_present": False,
            "median_industries": 0,
            "median_assets_per_industry": 0,
            "date_count": 0,
        }
    counts = []
    assets = []
    for _, group in frame.dropna(subset=["industry"]).groupby("date", sort=True):
        industry_counts = group.groupby("industry")["asset_id"].nunique()
        valid_counts = industry_counts[industry_counts >= min_assets_per_industry]
        counts.append(int(len(valid_counts)))
        if not valid_counts.empty:
            assets.append(float(valid_counts.median()))
    return {
        "industry_metadata_present": bool(counts and max(counts) > 0),
        "median_industries": int(pd.Series(counts).median()) if counts else 0,
        "median_assets_per_industry": float(pd.Series(assets).median()) if assets else 0.0,
        "date_count": int(len(counts)),
    }


def _load_stock_basic(path: str | Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame()
    target = Path(path)
    if target.is_dir():
        files = sorted([*target.rglob("*.parquet"), *target.rglob("*.csv")])
        files = [file for file in files if "stock_basic" in str(file).replace("\\", "/")]
        if not files:
            return pd.DataFrame()
        return pd.concat([_load_stock_basic(file) for file in files], ignore_index=True)
    if target.suffix.lower() == ".parquet":
        return pd.read_parquet(target)
    if target.suffix.lower() == ".csv":
        return pd.read_csv(target)
    return pd.DataFrame()


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


def _exposure_role(exposure_name: str) -> str:
    if "adv" in exposure_name or "amount" in exposure_name:
        return "size_liquidity_proxy"
    if "vol" in exposure_name:
        return "volatility_proxy"
    if "return" in exposure_name:
        return "momentum_proxy"
    return "style_proxy"


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()


def _is_finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


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
    if isinstance(value, (pd.Timestamp,)):
        return value.date().isoformat()
    return value
