from __future__ import annotations

from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence
import warnings

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
    _period_ic,
    _reference_correlations,
    _sample_dates,
)
from quant_robot.ops.price_volume_shock_reversal_preregistration import (
    SAFETY,
    default_price_volume_shock_reversal_specs,
)
from quant_robot.ops.public_reference_multi_family_prescreen import (
    _nonzero,
    _safe_log,
    _sanitize,
    load_public_reference_multi_family_bars,
)
from quant_robot.ops.public_technical_failure_reversal_neutral_dedup import (
    DEFAULT_EXPOSURE_COLUMNS,
    DEFAULT_RESIDUAL_EXPOSURES,
    EXPOSURE_CORRELATION_COLUMNS,
    _industry_coverage,
    _load_stock_basic,
    _merge_lead_exposures,
    _merge_stock_basic_industry,
    _technical_exposure_correlations,
    industry_neutralize_technical_lead,
    residualize_technical_lead,
)


STAGE = "price_volume_shock_reversal_neutral_prescreen"
ROUND157_SOURCE_REPORT = "docs/research/cn_stock_price_volume_shock_reversal_preregistration_round157_2026-06-23.md"
NEXT_DIRECTION_WITH_LEADS = "round159_price_volume_shock_reversal_cost_capacity_preflight"
NEXT_DIRECTION_WITHOUT_LEADS = "round159_rotate_after_price_volume_shock_reversal_neutral_prescreen_failure"
RESULT_COLUMNS = [
    "factor_name",
    "family",
    "horizon",
    "raw_mean_spearman_ic",
    "raw_icir",
    "raw_ic_t_stat",
    "raw_positive_ic_rate",
    "industry_neutral_mean_spearman_ic",
    "industry_neutral_icir",
    "industry_neutral_positive_ic_rate",
    "residual_mean_spearman_ic",
    "residual_icir",
    "residual_ic_t_stat",
    "residual_positive_ic_rate",
    "residual_yearly_failure_count",
    "reference_highly_redundant_count",
    "style_exposure_high_count",
    "residual_research_lead",
    "promotion_allowed",
    "portfolio_grid_allowed",
    "blockers",
]


def build_price_volume_shock_reversal_neutral_prescreen(
    *,
    bars_roots: Iterable[str | Path],
    stock_basic: str | Path | pd.DataFrame | None,
    preregistration_json: str | Path | None = None,
    candidate_specs: Sequence[Any] | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = (5,),
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
    specs = _load_candidate_specs(preregistration_json, candidate_specs)
    bars = load_public_reference_multi_family_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    stock_basic_frame = _stock_basic_frame(stock_basic)
    features = build_price_volume_shock_reversal_feature_frame(
        bars,
        horizons=tuple(horizons),
        execution_lag=execution_lag,
    )
    result = summarize_price_volume_shock_reversal_neutral_prescreen_from_features(
        features,
        stock_basic=stock_basic_frame,
        candidate_specs=specs,
        horizons=tuple(horizons),
        sample_every_n_dates=sample_every_n_dates,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_signal_date_amount=min_signal_date_amount,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
        min_industry_neutral_mean_ic=min_industry_neutral_mean_ic,
        min_industry_neutral_icir=min_industry_neutral_icir,
        min_industry_neutral_positive_ic_rate=min_industry_neutral_positive_ic_rate,
        min_residual_mean_ic=min_residual_mean_ic,
        min_residual_icir=min_residual_icir,
        min_residual_positive_ic_rate=min_residual_positive_ic_rate,
    )
    result["bars_roots"] = [str(Path(root)) for root in bars_roots]
    result["stock_basic"] = str(stock_basic) if isinstance(stock_basic, (str, Path)) else None
    result["preregistration_json"] = str(Path(preregistration_json)) if preregistration_json else None
    result["data_window"] = _data_window(bars, features, result)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_neutral_prescreen_walk_forward_cost_capacity_clearance_only",
    }
    result["capacity_policy"] = {
        "min_signal_date_amount": min_signal_date_amount,
        "adv20_amount_filter_enabled": True,
        "portfolio_grid_blocked_before_round158_completion": True,
    }
    result["sampling_policy"] = {
        "sample_every_n_dates": sample_every_n_dates,
        "sampling_used_for_correlations_only": True,
        "raw_industry_residual_ic_use_all_dates": True,
    }
    result["markdown"] = render_price_volume_shock_reversal_neutral_prescreen_markdown(result)
    return result


def summarize_price_volume_shock_reversal_neutral_prescreen_from_features(
    features: pd.DataFrame,
    *,
    stock_basic: pd.DataFrame | None,
    candidate_specs: Sequence[Any],
    horizons: tuple[int, ...],
    sample_every_n_dates: int = 1,
    min_cross_section: int,
    min_ic_observations: int,
    min_signal_date_amount: float,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
    min_industry_neutral_mean_ic: float = 0.02,
    min_industry_neutral_icir: float = 0.20,
    min_industry_neutral_positive_ic_rate: float = 0.55,
    min_residual_mean_ic: float = 0.02,
    min_residual_icir: float = 0.20,
    min_residual_positive_ic_rate: float = 0.55,
    high_corr_threshold: float = 0.85,
    high_mean_abs_corr_threshold: float = 0.70,
    moderate_corr_threshold: float = 0.70,
    moderate_mean_abs_corr_threshold: float = 0.50,
    high_exposure_corr_threshold: float = 0.85,
    high_exposure_mean_abs_corr_threshold: float = 0.60,
) -> dict[str, Any]:
    requested_horizons = tuple(int(horizon) for horizon in horizons)
    factor_frame = build_price_volume_shock_reversal_factor_frame(
        features,
        stock_basic,
        candidate_specs=candidate_specs,
        min_signal_date_amount=min_signal_date_amount,
    )
    reference_frame = build_price_volume_shock_reversal_reference_frame(features)
    exposure_frame = build_price_volume_shock_reversal_exposure_frame(features, stock_basic)
    labels = build_price_volume_shock_reversal_labels(features, horizons=requested_horizons)
    results: list[dict[str, Any]] = []
    raw_ic_rows: list[dict[str, Any]] = []
    industry_ic_rows: list[dict[str, Any]] = []
    residual_ic_rows: list[dict[str, Any]] = []
    reference_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []
    raw_yearly_rows: list[dict[str, Any]] = []
    industry_yearly_rows: list[dict[str, Any]] = []
    residual_yearly_rows: list[dict[str, Any]] = []
    factor_rows = 0
    industry_rows = 0
    residual_rows = 0

    for spec in candidate_specs:
        factor_name = str(_field(spec, "factor_name"))
        family = str(_field(spec, "family"))
        lead = factor_frame[factor_frame["factor_name"] == factor_name].reset_index(drop=True)
        factor_rows += len(lead)
        lead_with_exposures = _merge_lead_exposures(lead, exposure_frame)
        industry_factor_name = f"{factor_name}_industry_neutral"
        industry = industry_neutralize_technical_lead(
            lead_with_exposures,
            industry_factor_name=industry_factor_name,
            min_industries=min_industries,
            min_assets_per_industry=min_assets_per_industry,
        )
        industry_rows += len(industry)
        residual_factor_name = f"{factor_name}_industry_size_liquidity_vol_residual"
        residual = residualize_technical_lead(
            industry,
            exposure_names=DEFAULT_RESIDUAL_EXPOSURES,
            residual_factor_name=residual_factor_name,
            min_cross_section=min_cross_section,
        )
        residual_rows += len(residual)
        sampled_residual = _sample_dates(residual, sample_every_n_dates=sample_every_n_dates)
        sampled_reference = _filter_dates(reference_frame, sampled_residual["date"].unique()) if not sampled_residual.empty else reference_frame
        sampled_lead_exposure = _sample_dates(lead_with_exposures, sample_every_n_dates=sample_every_n_dates)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="invalid value encountered in divide", category=RuntimeWarning)
            refs = _reference_correlations(
                sampled_residual,
                sampled_reference,
                lead_factor_name=residual_factor_name,
                min_cross_section=min_cross_section,
                high_corr_threshold=high_corr_threshold,
                high_mean_abs_corr_threshold=high_mean_abs_corr_threshold,
                moderate_corr_threshold=moderate_corr_threshold,
                moderate_mean_abs_corr_threshold=moderate_mean_abs_corr_threshold,
            )
            exposures = _technical_exposure_correlations(
                sampled_lead_exposure,
                exposure_names=DEFAULT_EXPOSURE_COLUMNS,
                min_cross_section=min_cross_section,
                high_exposure_corr_threshold=high_exposure_corr_threshold,
                high_exposure_mean_abs_corr_threshold=high_exposure_mean_abs_corr_threshold,
            )
        for row in refs:
            reference_rows.append({"lead_factor_name": factor_name, **row})
        for row in exposures:
            exposure_rows.append({"lead_factor_name": factor_name, **row})
        for horizon in requested_horizons:
            raw_obs = _lead_ic_observations(
                lead,
                labels,
                lead_factor_name=factor_name,
                horizon=horizon,
                min_cross_section=min_cross_section,
            )
            industry_obs = _lead_ic_observations(
                industry,
                labels,
                lead_factor_name=industry_factor_name,
                horizon=horizon,
                min_cross_section=min_cross_section,
            )
            residual_obs = _lead_ic_observations(
                residual,
                labels,
                lead_factor_name=residual_factor_name,
                horizon=horizon,
                min_cross_section=min_cross_section,
            )
            raw_summary = _lead_ic_summary(raw_obs, min_ic_observations=min_ic_observations)
            industry_summary = _lead_ic_summary(industry_obs, min_ic_observations=min_ic_observations)
            residual_summary = _lead_ic_summary(residual_obs, min_ic_observations=min_ic_observations)
            raw_yearly = _period_ic(raw_obs, period="year")
            industry_yearly = _period_ic(industry_obs, period="year")
            residual_yearly = _period_ic(residual_obs, period="year")
            blockers = _row_blockers(
                raw_summary=raw_summary,
                industry_summary=industry_summary,
                residual_summary=residual_summary,
                residual_yearly=residual_yearly,
                reference_correlations=refs,
                exposure_correlations=exposures,
                industry_coverage=_industry_coverage(lead_with_exposures, min_assets_per_industry=min_assets_per_industry),
                min_industries=min_industries,
                min_industry_neutral_mean_ic=min_industry_neutral_mean_ic,
                min_industry_neutral_icir=min_industry_neutral_icir,
                min_industry_neutral_positive_ic_rate=min_industry_neutral_positive_ic_rate,
                min_residual_mean_ic=min_residual_mean_ic,
                min_residual_icir=min_residual_icir,
                min_residual_positive_ic_rate=min_residual_positive_ic_rate,
            )
            residual_research_lead = not blockers
            results.append(
                {
                    "factor_name": factor_name,
                    "family": family,
                    "horizon": int(horizon),
                    "raw_mean_spearman_ic": raw_summary["mean_spearman_ic"],
                    "raw_icir": raw_summary["icir"],
                    "raw_ic_t_stat": raw_summary["ic_t_stat"],
                    "raw_positive_ic_rate": raw_summary["positive_ic_rate"],
                    "industry_neutral_mean_spearman_ic": industry_summary["mean_spearman_ic"],
                    "industry_neutral_icir": industry_summary["icir"],
                    "industry_neutral_positive_ic_rate": industry_summary["positive_ic_rate"],
                    "residual_mean_spearman_ic": residual_summary["mean_spearman_ic"],
                    "residual_icir": residual_summary["icir"],
                    "residual_ic_t_stat": residual_summary["ic_t_stat"],
                    "residual_positive_ic_rate": residual_summary["positive_ic_rate"],
                    "residual_yearly_failure_count": int(sum(row.get("failure") for row in residual_yearly)),
                    "reference_highly_redundant_count": int(sum(row.get("redundancy_class") == "highly_redundant" for row in refs)),
                    "style_exposure_high_count": int(sum(row.get("exposure_class") == "high_exposure" for row in exposures)),
                    "residual_research_lead": residual_research_lead,
                    "promotion_allowed": False,
                    "portfolio_grid_allowed": False,
                    "blockers": blockers,
                }
            )
            raw_ic_rows.extend(raw_obs)
            industry_ic_rows.extend(industry_obs)
            residual_ic_rows.extend(residual_obs)
            raw_yearly_rows.extend([{"factor_name": factor_name, **row} for row in raw_yearly])
            industry_yearly_rows.extend([{"factor_name": factor_name, **row} for row in industry_yearly])
            residual_yearly_rows.extend([{"factor_name": factor_name, **row} for row in residual_yearly])

    residual_lead_count = sum(1 for row in results if row["residual_research_lead"])
    next_direction = NEXT_DIRECTION_WITH_LEADS if residual_lead_count else NEXT_DIRECTION_WITHOUT_LEADS
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": {
            "passes": True,
            "candidate_count": len(candidate_specs),
            "family_count": len({str(_field(spec, "family")) for spec in candidate_specs}),
            "test_count": len(results),
            "factor_rows": int(factor_rows),
            "industry_neutral_rows": int(industry_rows),
            "residual_rows": int(residual_rows),
            "label_rows": int(len(labels)),
            "reference_factor_count": int(reference_frame["factor_name"].nunique()) if not reference_frame.empty else 0,
            "residual_research_lead_count": int(residual_lead_count),
            "promotion_allowed_candidates": 0,
            "portfolio_grid_allowed_candidates": 0,
            "portfolio_preflight_candidates": int(residual_lead_count),
            "next_direction": next_direction,
            "horizons": sorted(requested_horizons),
        },
        "source_context": {
            "source_preregistration": ROUND157_SOURCE_REPORT,
            "round157_all_8_candidates_counted": True,
            "portfolio_grid_blocked_at_this_stage": True,
        },
        "multiple_testing_policy": {
            "method": "all Round157 candidate x horizon tests counted before any promotion claim",
            "round157_candidate_count": len(candidate_specs),
            "test_count": len(results),
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed_before_neutral_prescreen": False,
            "requires_next_gate": "cost_capacity_walk_forward_after_residual_reference_gate",
        },
        "results": sorted(results, key=lambda row: (not row["residual_research_lead"], -abs(row["residual_mean_spearman_ic"]), row["factor_name"])),
        "reference_correlations": reference_rows,
        "exposure_correlations": exposure_rows,
        "raw_yearly_ic": raw_yearly_rows,
        "industry_neutral_yearly_ic": industry_yearly_rows,
        "residual_yearly_ic": residual_yearly_rows,
        "raw_ic_observations": raw_ic_rows,
        "industry_neutral_ic_observations": industry_ic_rows,
        "residual_ic_observations": residual_ic_rows,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_price_volume_shock_reversal_neutral_prescreen_markdown(result)
    return result


def build_price_volume_shock_reversal_feature_frame(
    bars: pd.DataFrame,
    *,
    horizons: tuple[int, ...],
    execution_lag: int,
) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str)
    if "volume" not in frame and "vol" in frame:
        frame["volume"] = frame["vol"]
    if "volume" not in frame:
        frame["volume"] = 0.0
    if "open" not in frame:
        frame["open"] = frame["adj_close"]
    if "close" not in frame:
        frame["close"] = frame["adj_close"]
    for column in ["open", "high", "low", "close", "adj_close", "volume", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = (
        frame[(frame["market"] == "CN") & (frame["adj_close"] > 0) & (frame["amount"] > 0)]
        .dropna(subset=["date", "asset_id", "market", "adj_close", "high", "low", "amount"])
        .drop_duplicates(["asset_id", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )
    pieces = []
    for _, group in frame.groupby("asset_id", sort=False):
        group = group.copy()
        close = group["adj_close"]
        open_ = group["open"]
        high = group["high"]
        low = group["low"]
        volume = group["volume"]
        amount = group["amount"]
        returns = close.pct_change()
        true_range = _true_range(high, low, close)
        amihud = returns.abs() / _nonzero(amount) * 100_000_000.0
        realized_vol_10 = returns.rolling(10, min_periods=5).std(ddof=0)
        realized_vol_20 = returns.rolling(20, min_periods=5).std(ddof=0)
        realized_vol_60 = returns.rolling(60, min_periods=20).std(ddof=0)
        piece = group[["date", "asset_id", "market", "open", "high", "low", "adj_close", "amount", "volume"]].copy()
        piece["return_1d"] = returns
        piece["return_5"] = close.pct_change(5)
        piece["return_10"] = close.pct_change(10)
        piece["return_20"] = close.pct_change(20)
        piece["adv20_amount"] = amount.rolling(20, min_periods=5).mean()
        piece["amount_trend_20_60"] = amount.rolling(20, min_periods=5).mean() / _nonzero(amount.rolling(60, min_periods=20).mean()) - 1.0
        piece["realized_vol_20"] = realized_vol_20
        piece["realized_vol_ratio_10_60"] = realized_vol_10 / _nonzero(realized_vol_60) - 1.0
        piece["amihud_20"] = amihud.rolling(20, min_periods=5).mean()
        piece["amihud_shock_20_60"] = piece["amihud_20"] / _nonzero(amihud.rolling(60, min_periods=20).mean()) - 1.0
        piece["liquidity_stress_persistence_20"] = piece["amihud_20"]
        piece["volume_ratio_5_20"] = volume.rolling(5, min_periods=3).mean() / _nonzero(volume.rolling(20, min_periods=5).mean()) - 1.0
        close_location = (close - low) / _nonzero(high - low)
        piece["close_location_20"] = close_location.rolling(20, min_periods=5).mean()
        piece["weak_close_location_20"] = 1.0 - piece["close_location_20"]
        piece["true_range_ratio_5_20"] = true_range.rolling(5, min_periods=3).mean() / _nonzero(true_range.rolling(20, min_periods=5).mean()) - 1.0
        piece["down_day_volume_share_10"] = volume.where(returns < 0.0, 0.0).rolling(10, min_periods=5).sum() / _nonzero(volume.rolling(10, min_periods=5).sum())
        piece["open_gap_1"] = open_ / _nonzero(close.shift(1)) - 1.0
        piece["abs_open_gap_1"] = piece["open_gap_1"].abs()
        piece["intraday_failure_reversal_5"] = (-(close / _nonzero(open_) - 1.0)).rolling(5, min_periods=3).mean()
        vwap_proxy = amount / _nonzero(volume)
        piece["close_over_vwap_proxy_5"] = (close / _nonzero(vwap_proxy) - 1.0).rolling(5, min_periods=3).mean()
        piece["shock_return_abs_5_20"] = returns.abs().rolling(5, min_periods=3).mean() / _nonzero(returns.abs().rolling(20, min_periods=5).mean()) - 1.0
        for horizon in horizons:
            entry = close.shift(-execution_lag)
            exit_ = close.shift(-(execution_lag + int(horizon)))
            piece[f"forward_return_{int(horizon)}"] = exit_ / entry - 1.0
        pieces.append(piece)
    if not pieces:
        return pd.DataFrame()
    features = pd.concat(pieces, ignore_index=True)
    features["log_adv20_amount"] = _safe_log(features["adv20_amount"])
    features["log_amount"] = _safe_log(features["amount"])
    z_inputs = {
        "z_amihud_shock_20_60": features["amihud_shock_20_60"],
        "z_neg_return_5": -features["return_5"],
        "z_log_adv20_amount": features["log_adv20_amount"],
        "z_volume_ratio_5_20": features["volume_ratio_5_20"],
        "z_weak_close_location_20": features["weak_close_location_20"],
        "z_true_range_ratio_5_20": features["true_range_ratio_5_20"],
        "z_down_day_volume_share_10": features["down_day_volume_share_10"],
        "z_neg_return_10": -features["return_10"],
        "z_neg_realized_vol_20": -features["realized_vol_20"],
        "z_abs_open_gap_1": features["abs_open_gap_1"],
        "z_intraday_failure_reversal_5": features["intraday_failure_reversal_5"],
        "z_close_over_vwap_proxy_5": features["close_over_vwap_proxy_5"],
        "z_neg_return_20": -features["return_20"],
        "z_neg_liquidity_stress_persistence_20": -features["liquidity_stress_persistence_20"],
        "z_shock_return_abs_5_20": features["shock_return_abs_5_20"],
        "z_neg_realized_vol_ratio_10_60": -features["realized_vol_ratio_10_60"],
    }
    for column, values in z_inputs.items():
        features[column] = _cs_zscore(features, values)
    return features.replace([float("inf"), float("-inf")], pd.NA)


def build_price_volume_shock_reversal_factor_frame(
    features: pd.DataFrame,
    stock_basic: pd.DataFrame | None,
    *,
    candidate_specs: Sequence[Any],
    min_signal_date_amount: float,
) -> pd.DataFrame:
    if features.empty:
        return _empty_factor_frame()
    values_by_name = _candidate_value_series(features)
    capacity_mask = (
        (features["amount"] >= min_signal_date_amount)
        & (features["adv20_amount"] >= min_signal_date_amount)
        & (features["return_1d"].abs() <= 0.50)
    )
    rows = []
    for spec in candidate_specs:
        name = str(_field(spec, "factor_name"))
        values = values_by_name.get(name)
        if values is None:
            continue
        frame = features.loc[capacity_mask, ["date", "asset_id", "market", "amount", "adv20_amount"]].copy()
        frame["family"] = str(_field(spec, "family"))
        frame["source_evidence_status"] = str(_field(spec, "source_evidence_status"))
        frame["factor_name"] = name
        frame["factor_value"] = values.loc[capacity_mask]
        rows.append(frame.dropna(subset=["factor_value", "amount", "adv20_amount"]))
    if not rows:
        return _empty_factor_frame()
    result = pd.concat(rows, ignore_index=True)
    result = _merge_stock_basic_industry(result, stock_basic)
    return result.sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def build_price_volume_shock_reversal_reference_frame(features: pd.DataFrame) -> pd.DataFrame:
    if features.empty:
        return _empty_factor_frame()
    base = features[["date", "asset_id", "market", "amount", "adv20_amount"]].copy()
    references = {
        "amihud_shock_reference_20_60": features["z_amihud_shock_20_60"] + features["z_neg_return_5"],
        "volume_climax_reference_20": features["z_volume_ratio_5_20"] + features["z_weak_close_location_20"],
        "range_expansion_reference_20": features["z_true_range_ratio_5_20"],
        "gap_range_failure_reference_5_20": features["z_abs_open_gap_1"] + features["z_intraday_failure_reversal_5"],
        "vwap_proxy_reclaim_reference_20": features["z_close_over_vwap_proxy_5"] + features["z_neg_return_20"],
        "lowvol_reversal_cluster_reference_20": features["z_neg_realized_vol_20"] + features["z_neg_return_20"],
    }
    rows = []
    for name, values in references.items():
        frame = base.copy()
        frame["factor_name"] = name
        frame["factor_value"] = pd.to_numeric(values, errors="coerce")
        rows.append(frame.dropna(subset=["factor_value"]))
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def build_price_volume_shock_reversal_exposure_frame(
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
            "log_adv20_amount",
            "log_amount",
            "realized_vol_20",
            "amount_trend_20_60",
            "return_20",
        ]
    ].copy()
    exposure = _merge_stock_basic_industry(exposure, stock_basic)
    return exposure.replace([float("inf"), float("-inf")], pd.NA).reset_index(drop=True)


def build_price_volume_shock_reversal_labels(features: pd.DataFrame, *, horizons: tuple[int, ...]) -> pd.DataFrame:
    rows = []
    for horizon in horizons:
        column = f"forward_return_{int(horizon)}"
        if features.empty or column not in features:
            continue
        labels = features[["date", "asset_id", "market", column]].rename(columns={column: "forward_return"}).copy()
        labels["horizon"] = int(horizon)
        rows.append(labels.dropna(subset=["forward_return"]))
    if not rows:
        return pd.DataFrame(columns=["date", "asset_id", "market", "horizon", "forward_return"])
    return pd.concat(rows, ignore_index=True).reset_index(drop=True)


def write_price_volume_shock_reversal_neutral_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "price_volume_shock_reversal_neutral_prescreen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "price_volume_shock_reversal_neutral_prescreen.md").write_text(
        render_price_volume_shock_reversal_neutral_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "price_volume_shock_reversal_neutral_prescreen_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(output_path / "price_volume_shock_reversal_reference_correlations.csv", result.get("reference_correlations", []), ["lead_factor_name", *REFERENCE_CORRELATION_COLUMNS])
    _write_csv(output_path / "price_volume_shock_reversal_exposure_correlations.csv", result.get("exposure_correlations", []), ["lead_factor_name", *EXPOSURE_CORRELATION_COLUMNS])
    _write_csv(output_path / "price_volume_shock_reversal_raw_yearly_ic.csv", result.get("raw_yearly_ic", []), ["factor_name", *YEARLY_IC_COLUMNS])
    _write_csv(output_path / "price_volume_shock_reversal_industry_neutral_yearly_ic.csv", result.get("industry_neutral_yearly_ic", []), ["factor_name", *YEARLY_IC_COLUMNS])
    _write_csv(output_path / "price_volume_shock_reversal_residual_yearly_ic.csv", result.get("residual_yearly_ic", []), ["factor_name", *YEARLY_IC_COLUMNS])
    _write_csv(output_path / "price_volume_shock_reversal_raw_ic_observations.csv", result.get("raw_ic_observations", []), IC_OBSERVATION_COLUMNS)
    _write_csv(output_path / "price_volume_shock_reversal_industry_neutral_ic_observations.csv", result.get("industry_neutral_ic_observations", []), IC_OBSERVATION_COLUMNS)
    _write_csv(output_path / "price_volume_shock_reversal_residual_ic_observations.csv", result.get("residual_ic_observations", []), IC_OBSERVATION_COLUMNS)


def render_price_volume_shock_reversal_neutral_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Price-Volume Shock Reversal Neutral Prescreen Round158",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Industry-neutral rows: {summary.get('industry_neutral_rows', 0)}",
        f"- Residual rows: {summary.get('residual_rows', 0)}",
        f"- Residual research leads: {summary.get('residual_research_lead_count', 0)}",
        f"- Portfolio grid allowed candidates: {summary.get('portfolio_grid_allowed_candidates', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Next direction: {summary.get('next_direction', NEXT_DIRECTION_WITHOUT_LEADS)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Results",
        "",
        "| Factor | H | Raw IC | Raw ICIR | Neutral IC | Residual IC | Residual ICIR | Ref High | Exposure High | Lead | Blockers |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("results", []):
        lines.append(
            "| {factor} | {horizon} | {raw_ic:.4f} | {raw_icir:.3f} | {neutral_ic:.4f} | {resid_ic:.4f} | {resid_icir:.3f} | {ref_high} | {exp_high} | {lead} | {blockers} |".format(
                factor=row["factor_name"],
                horizon=row["horizon"],
                raw_ic=row["raw_mean_spearman_ic"],
                raw_icir=row["raw_icir"],
                neutral_ic=row["industry_neutral_mean_spearman_ic"],
                resid_ic=row["residual_mean_spearman_ic"],
                resid_icir=row["residual_icir"],
                ref_high=row["reference_highly_redundant_count"],
                exp_high=row["style_exposure_high_count"],
                lead="yes" if row["residual_research_lead"] else "no",
                blockers=", ".join(row.get("blockers", [])) if row.get("blockers") else "none",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This is still not a promotion stage.",
            "- A residual lead only earns the right to a later cost/capacity walk-forward preflight.",
            "- If zero residual leads survive, the family must rotate instead of tuning more price-volume shock windows.",
        ]
    )
    return "\n".join(lines) + "\n"


def _candidate_value_series(features: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        "amihud_shock_reversal_liquid_20_60": (
            0.45 * features["z_amihud_shock_20_60"] + 0.30 * features["z_neg_return_5"] + 0.25 * features["z_log_adv20_amount"]
        ),
        "volume_climax_reversal_close_location_20": (
            0.40 * features["z_volume_ratio_5_20"] + 0.35 * features["z_weak_close_location_20"] + 0.25 * features["z_neg_return_5"]
        ),
        "range_expansion_exhaustion_reversal_20": (
            0.45 * features["z_true_range_ratio_5_20"] + 0.30 * features["z_neg_return_5"] + 0.25 * features["z_log_adv20_amount"]
        ),
        "downside_volume_absorption_reversal_10_60": (
            0.40 * features["z_down_day_volume_share_10"]
            + 0.30 * features["z_neg_return_10"]
            + 0.20 * features["z_neg_realized_vol_20"]
            + 0.10 * features["z_log_adv20_amount"]
        ),
        "gap_range_failure_reversal_5_20": (
            0.35 * features["z_abs_open_gap_1"] + 0.35 * features["z_intraday_failure_reversal_5"] + 0.30 * features["z_log_adv20_amount"]
        ),
        "vwap_proxy_reclaim_reversal_20": (
            0.35 * features["z_close_over_vwap_proxy_5"]
            + 0.30 * features["z_neg_return_20"]
            + 0.20 * features["z_volume_ratio_5_20"]
            + 0.15 * features["z_log_adv20_amount"]
        ),
        "low_liquidity_stress_normalization_20_60": (
            0.45 * features["z_amihud_shock_20_60"]
            + 0.35 * features["z_neg_liquidity_stress_persistence_20"]
            + 0.20 * features["z_log_adv20_amount"]
        ),
        "volatility_compression_after_shock_reversal_20_60": (
            0.35 * features["z_shock_return_abs_5_20"]
            + 0.35 * features["z_neg_realized_vol_ratio_10_60"]
            + 0.30 * features["z_log_adv20_amount"]
        ),
    }


def _row_blockers(
    *,
    raw_summary: dict[str, Any],
    industry_summary: dict[str, Any],
    residual_summary: dict[str, Any],
    residual_yearly: list[dict[str, Any]],
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
    if not raw_summary.get("minimum_observation_gate_passed", False):
        blockers.append("raw_ic_observations_below_threshold")
    if not industry_coverage.get("industry_metadata_present", False):
        blockers.append("industry_metadata_missing")
    if int(industry_coverage.get("median_industries", 0)) < min_industries:
        blockers.append("industry_breadth_below_threshold")
    if not industry_summary.get("minimum_observation_gate_passed", False):
        blockers.append("industry_neutral_ic_observations_below_threshold")
    if industry_summary.get("mean_spearman_ic", 0.0) < min_industry_neutral_mean_ic:
        blockers.append("industry_neutral_mean_ic_below_threshold")
    if industry_summary.get("icir", 0.0) < min_industry_neutral_icir:
        blockers.append("industry_neutral_icir_below_threshold")
    if industry_summary.get("positive_ic_rate", 0.0) < min_industry_neutral_positive_ic_rate:
        blockers.append("industry_neutral_positive_ic_rate_below_threshold")
    if not residual_summary.get("minimum_observation_gate_passed", False):
        blockers.append("residual_ic_observations_below_threshold")
    if residual_summary.get("mean_spearman_ic", 0.0) < min_residual_mean_ic:
        blockers.append("residual_mean_ic_below_threshold")
    if residual_summary.get("icir", 0.0) < min_residual_icir:
        blockers.append("residual_icir_below_threshold")
    if residual_summary.get("positive_ic_rate", 0.0) < min_residual_positive_ic_rate:
        blockers.append("residual_positive_ic_rate_below_threshold")
    if any(row.get("redundancy_class") == "highly_redundant" for row in reference_correlations):
        blockers.append("candidate_highly_redundant_with_public_price_volume_reference")
    if any(row.get("exposure_class") == "high_exposure" for row in exposure_correlations):
        blockers.append("candidate_high_size_liquidity_or_volatility_exposure")
    if any(row.get("failure") for row in residual_yearly):
        blockers.append("residual_yearly_ic_instability")
    return _dedupe(blockers)


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    previous_close = close.shift(1)
    return pd.concat([high - low, (high - previous_close).abs(), (low - previous_close).abs()], axis=1).max(axis=1)


def _cs_zscore(frame: pd.DataFrame, series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    grouped = values.groupby(frame["date"])
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return (values - mean) / _nonzero(std)


def _load_candidate_specs(preregistration_json: str | Path | None, candidate_specs: Sequence[Any] | None) -> list[Any]:
    if candidate_specs is not None:
        return list(candidate_specs)
    if preregistration_json is None:
        return default_price_volume_shock_reversal_specs()
    packet = json.loads(Path(preregistration_json).read_text(encoding="utf-8"))
    candidates = [candidate for candidate in packet.get("candidates", []) or [] if isinstance(candidate, dict)]
    return candidates or default_price_volume_shock_reversal_specs()


def _stock_basic_frame(value: str | Path | pd.DataFrame | None) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    return _load_stock_basic(value) if value is not None else pd.DataFrame()


def _field(spec: Any, name: str) -> Any:
    if isinstance(spec, dict):
        return spec.get(name)
    return getattr(spec, name)


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "asset_id", "market", "amount", "adv20_amount", "family", "factor_name", "factor_value"])


def _data_window(bars: pd.DataFrame, features: pd.DataFrame, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "bar_rows": int(len(bars)),
        "asset_count": int(bars["asset_id"].nunique()) if "asset_id" in bars else 0,
        "feature_rows": int(len(features)),
        "factor_rows": int(result.get("summary", {}).get("factor_rows", 0)),
        "label_rows": int(result.get("summary", {}).get("label_rows", 0)),
    }


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()


def _dedupe(values: list[str]) -> list[str]:
    output = []
    for value in values:
        if value not in output:
            output.append(value)
    return output


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
