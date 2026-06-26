from __future__ import annotations

from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence
import warnings

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.cn_tradeability_limit_event_preregistration import (
    SAFETY,
    SOURCE_AUDIT as ROUND159_SOURCE_REPORT,
    default_cn_tradeability_limit_event_specs,
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


STAGE = "cn_tradeability_limit_event_proxy_prescreen"
NEXT_DIRECTION_WITH_PROXY_LEADS = "round161_true_limit_status_audit_before_limit_event_portfolio_preflight"
NEXT_DIRECTION_WITHOUT_PROXY_LEADS = "round161_rotate_after_tradeability_limit_event_proxy_prescreen_failure"
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
    "tradeability_blocked_signal_rate",
    "true_limit_status_audit_required",
    "proxy_research_lead",
    "promotion_allowed",
    "portfolio_grid_allowed",
    "blockers",
]


def build_cn_tradeability_limit_event_proxy_prescreen(
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
    max_tradeability_blocked_signal_rate: float = 0.35,
) -> dict[str, Any]:
    specs = _load_candidate_specs(preregistration_json, candidate_specs)
    stock_basic_frame = _stock_basic_frame(stock_basic)
    bars = load_public_reference_multi_family_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    features = build_cn_tradeability_limit_event_feature_frame(
        bars,
        stock_basic=stock_basic_frame,
        horizons=tuple(horizons),
        execution_lag=execution_lag,
    )
    result = summarize_cn_tradeability_limit_event_proxy_prescreen_from_features(
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
        max_tradeability_blocked_signal_rate=max_tradeability_blocked_signal_rate,
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
        "final_holdout_use": "read_once_after_true_limit_status_and_walk_forward_cost_capacity_clearance_only",
    }
    result["markdown"] = render_cn_tradeability_limit_event_proxy_prescreen_markdown(result)
    return result


def summarize_cn_tradeability_limit_event_proxy_prescreen_from_features(
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
    max_tradeability_blocked_signal_rate: float = 0.35,
    high_corr_threshold: float = 0.85,
    high_mean_abs_corr_threshold: float = 0.70,
    moderate_corr_threshold: float = 0.70,
    moderate_mean_abs_corr_threshold: float = 0.50,
    high_exposure_corr_threshold: float = 0.85,
    high_exposure_mean_abs_corr_threshold: float = 0.60,
) -> dict[str, Any]:
    requested_horizons = tuple(int(horizon) for horizon in horizons)
    factor_frame = build_cn_tradeability_limit_event_factor_frame(
        features,
        stock_basic,
        candidate_specs=candidate_specs,
        min_signal_date_amount=min_signal_date_amount,
    )
    reference_frame = build_cn_tradeability_limit_event_reference_frame(features)
    exposure_frame = build_cn_tradeability_limit_event_exposure_frame(features, stock_basic)
    labels = build_cn_tradeability_limit_event_labels(features, horizons=requested_horizons)
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
        blocked_rate = _tradeability_blocked_rate(lead)
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
                tradeability_blocked_signal_rate=blocked_rate,
                min_industries=min_industries,
                min_industry_neutral_mean_ic=min_industry_neutral_mean_ic,
                min_industry_neutral_icir=min_industry_neutral_icir,
                min_industry_neutral_positive_ic_rate=min_industry_neutral_positive_ic_rate,
                min_residual_mean_ic=min_residual_mean_ic,
                min_residual_icir=min_residual_icir,
                min_residual_positive_ic_rate=min_residual_positive_ic_rate,
                max_tradeability_blocked_signal_rate=max_tradeability_blocked_signal_rate,
            )
            proxy_research_lead = not blockers
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
                    "tradeability_blocked_signal_rate": blocked_rate,
                    "true_limit_status_audit_required": True,
                    "proxy_research_lead": proxy_research_lead,
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

    proxy_lead_count = sum(1 for row in results if row["proxy_research_lead"])
    next_direction = NEXT_DIRECTION_WITH_PROXY_LEADS if proxy_lead_count else NEXT_DIRECTION_WITHOUT_PROXY_LEADS
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
            "true_limit_status_audit_required_candidates": int(len(candidate_specs)),
            "proxy_research_lead_count": int(proxy_lead_count),
            "promotion_allowed_candidates": 0,
            "portfolio_grid_allowed_candidates": 0,
            "portfolio_preflight_candidates": 0,
            "next_direction": next_direction,
            "horizons": sorted(requested_horizons),
        },
        "source_context": {
            "source_preregistration": "docs/research/cn_stock_cn_tradeability_limit_event_preregistration_round159_2026-06-23.md",
            "source_audit": ROUND159_SOURCE_REPORT,
            "round159_all_8_candidates_counted": True,
            "true_limit_status_is_proxy_only": True,
            "portfolio_grid_blocked_at_this_stage": True,
        },
        "multiple_testing_policy": {
            "method": "all Round159 candidate x horizon tests counted before any promotion claim",
            "round159_candidate_count": len(candidate_specs),
            "test_count": len(results),
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed_before_true_limit_audit": False,
            "requires_true_limit_status_audit": True,
            "requires_official_suspension_or_tradeability_feed": True,
            "requires_cost_capacity_walk_forward_after_proxy_lead": True,
            "requires_regime_coverage": True,
            "requires_multiple_testing_accounting": True,
        },
        "results": sorted(results, key=lambda row: (not row["proxy_research_lead"], -abs(row["residual_mean_spearman_ic"]), row["factor_name"])),
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
    result["markdown"] = render_cn_tradeability_limit_event_proxy_prescreen_markdown(result)
    return result


def build_cn_tradeability_limit_event_feature_frame(
    bars: pd.DataFrame,
    *,
    stock_basic: pd.DataFrame | None,
    horizons: tuple[int, ...],
    execution_lag: int,
) -> pd.DataFrame:
    frame = _normalise_limit_event_bars(bars)
    frame = _merge_tradeability_metadata(frame, stock_basic)
    pieces = []
    for _, group in frame.groupby("asset_id", sort=False):
        group = group.sort_values("date").copy()
        close = group["close_raw"]
        open_ = group["open_raw"]
        high = group["high_raw"]
        low = group["low_raw"]
        amount = group["amount"]
        volume = group["volume"]
        prev_close = close.shift(1)
        ret_1 = close / _nonzero(prev_close) - 1.0
        high_ret = high / _nonzero(prev_close) - 1.0
        low_ret = low / _nonzero(prev_close) - 1.0
        limit_pct = group["limit_pct_proxy"].astype(float)
        tol = 0.002
        near_tol = 0.015
        close_location = (close - low) / _nonzero(high - low)
        limit_up_touch = high_ret >= (limit_pct - tol)
        limit_down_touch = low_ret <= (-limit_pct + tol)
        limit_up_like = (ret_1 >= (limit_pct - tol)) & (high <= close * (1.0 + tol))
        limit_down_like = (ret_1 <= (-limit_pct + tol)) & (low >= close * (1.0 - tol))
        near_limit_up = high_ret >= (limit_pct - near_tol)
        near_limit_down = low_ret <= (-limit_pct + near_tol)
        failed_limit_up = limit_up_touch & (~limit_up_like)
        near_limit_up_failure = near_limit_up & (close_location < 0.65)
        limit_event_any = limit_up_like | limit_down_like | failed_limit_up | near_limit_down
        returns = close.pct_change()
        piece = group[
            [
                "date",
                "asset_id",
                "symbol",
                "market",
                "open_raw",
                "high_raw",
                "low_raw",
                "close_raw",
                "adj_close",
                "amount",
                "volume",
                "industry",
                "name",
                "stock_market",
                "board",
            ]
        ].copy()
        piece["prev_close_raw"] = prev_close
        piece["limit_pct_proxy"] = limit_pct
        piece["return_1d"] = ret_1
        piece["ret_5"] = close.pct_change(5)
        piece["ret_20_skip5"] = close.shift(5) / _nonzero(close.shift(25)) - 1.0
        piece["adv20_amount"] = amount.rolling(20, min_periods=5).mean()
        piece["amount_trend_20_60"] = amount.rolling(20, min_periods=5).mean() / _nonzero(amount.rolling(60, min_periods=20).mean()) - 1.0
        piece["realized_vol_20"] = returns.rolling(20, min_periods=5).std(ddof=0)
        piece["downside_vol_20"] = returns.clip(upper=0.0).rolling(20, min_periods=5).std(ddof=0)
        piece["turnover_spike_5"] = amount.rolling(5, min_periods=3).mean() / _nonzero(piece["adv20_amount"]) - 1.0
        piece["close_location_1"] = close_location
        piece["weak_close_location_1"] = 1.0 - close_location
        piece["limit_up_like_0"] = limit_up_like.astype(int)
        piece["limit_down_like_0"] = limit_down_like.astype(int)
        piece["limit_down_like_lag1"] = limit_down_like.shift(1).fillna(False).astype(int)
        piece["limit_down_relief_proxy"] = (piece["limit_down_like_lag1"] * (1 - piece["limit_down_like_0"])).astype(int)
        piece["near_limit_down_count_3"] = near_limit_down.astype(int).rolling(3, min_periods=1).sum()
        piece["failed_limit_up_proxy_1"] = failed_limit_up.astype(int)
        piece["near_limit_up_failure_proxy_1"] = near_limit_up_failure.astype(int)
        piece["close_unseal_proxy_1"] = (limit_up_touch & (ret_1 < (limit_pct - 0.010))).astype(int)
        piece["post_limit_cooling_days_5"] = (
            limit_event_any.shift(1).fillna(False).astype(int).rolling(5, min_periods=1).sum()
            * (1 - limit_event_any.astype(int))
        )
        piece["post_limit_down_recovery_5"] = (
            limit_down_like.shift(1).fillna(False).astype(int).rolling(5, min_periods=1).max()
            * close.pct_change(5).clip(lower=-0.5, upper=0.5)
        )
        piece["limit_down_pressure_5"] = near_limit_down.astype(int).rolling(5, min_periods=1).sum()
        piece["limit_up_pressure_5"] = near_limit_up.astype(int).rolling(5, min_periods=1).sum()
        piece["new_high_20"] = (close >= close.rolling(20, min_periods=5).max()).astype(int)
        piece["non_st_tradeable_quality_10"] = (
            (1 - group["st_flag"].astype(int))
            * (1 - group["suspended_proxy"].astype(int))
            * (1 - group["board_permission_blocked"].astype(int))
        ).rolling(10, min_periods=1).mean()
        piece["tradeability_blocked_proxy"] = (
            group["suspended_proxy"]
            | group["st_flag"]
            | group["new_listing_flag"]
            | group["delisted_or_inactive_flag"]
            | group["board_permission_blocked"]
            | limit_up_like
            | limit_down_like
        ).astype(int)
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
        "z_limit_down_relief_proxy": features["limit_down_relief_proxy"],
        "z_near_limit_down_count_3": features["near_limit_down_count_3"],
        "z_limit_up_like_0": features["limit_up_like_0"],
        "z_failed_limit_up_proxy_1": features["failed_limit_up_proxy_1"],
        "z_close_unseal_proxy_1": features["close_unseal_proxy_1"],
        "z_near_limit_up_failure_proxy_1": features["near_limit_up_failure_proxy_1"],
        "z_post_limit_cooling_days_5": features["post_limit_cooling_days_5"],
        "z_post_limit_down_recovery_5": features["post_limit_down_recovery_5"],
        "z_limit_pressure_asymmetry_5": features["limit_down_pressure_5"] - features["limit_up_pressure_5"],
        "z_new_high_20": features["new_high_20"],
        "z_neg_ret_5": -features["ret_5"],
        "z_ret_20_skip5": features["ret_20_skip5"],
        "z_turnover_spike_5": features["turnover_spike_5"],
        "z_weak_close_location_1": features["weak_close_location_1"],
        "z_non_st_tradeable_quality_10": features["non_st_tradeable_quality_10"],
        "z_log_adv20_amount": features["log_adv20_amount"],
        "z_neg_log_adv20_amount": -features["log_adv20_amount"],
        "z_neg_realized_vol_20": -features["realized_vol_20"],
        "z_neg_downside_vol_20": -features["downside_vol_20"],
    }
    for column, values in z_inputs.items():
        features[column] = _cs_zscore(features, values)
    return features.replace([float("inf"), float("-inf")], pd.NA)


def build_cn_tradeability_limit_event_factor_frame(
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
        frame = features.loc[
            capacity_mask,
            ["date", "asset_id", "market", "amount", "adv20_amount", "tradeability_blocked_proxy"],
        ].copy()
        frame["family"] = str(_field(spec, "family"))
        frame["source_evidence_status"] = str(_field(spec, "source_evidence_status"))
        frame["true_limit_status_audit_required"] = bool(_field(spec, "true_limit_status_audit_required"))
        frame["tradeability_controls_required"] = bool(_field(spec, "tradeability_controls_required"))
        frame["factor_name"] = name
        frame["factor_value"] = values.loc[capacity_mask]
        rows.append(frame.dropna(subset=["factor_value", "amount", "adv20_amount"]))
    if not rows:
        return _empty_factor_frame()
    result = pd.concat(rows, ignore_index=True)
    result = _merge_stock_basic_industry(result, stock_basic)
    return result.sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def build_cn_tradeability_limit_event_reference_frame(features: pd.DataFrame) -> pd.DataFrame:
    if features.empty:
        return _empty_factor_frame()
    base = features[["date", "asset_id", "market", "amount", "adv20_amount"]].copy()
    references = {
        "limit_down_pressure_reference_5": features["z_limit_pressure_asymmetry_5"] + features["z_neg_ret_5"],
        "limit_up_failure_reference_1_5": features["z_failed_limit_up_proxy_1"] + features["z_weak_close_location_1"],
        "post_limit_cooling_reference_5_20": features["z_post_limit_cooling_days_5"] + features["z_ret_20_skip5"],
        "lowvol_liquid_reversal_reference_20": features["z_neg_realized_vol_20"] + features["z_log_adv20_amount"],
    }
    rows = []
    for name, values in references.items():
        frame = base.copy()
        frame["factor_name"] = name
        frame["factor_value"] = pd.to_numeric(values, errors="coerce")
        rows.append(frame.dropna(subset=["factor_value"]))
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def build_cn_tradeability_limit_event_exposure_frame(
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
            "ret_20_skip5",
        ]
    ].copy()
    exposure = exposure.rename(columns={"ret_20_skip5": "return_20"})
    exposure = _merge_stock_basic_industry(exposure, stock_basic)
    return exposure.replace([float("inf"), float("-inf")], pd.NA).reset_index(drop=True)


def build_cn_tradeability_limit_event_labels(features: pd.DataFrame, *, horizons: tuple[int, ...]) -> pd.DataFrame:
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


def write_cn_tradeability_limit_event_proxy_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "cn_tradeability_limit_event_proxy_prescreen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "cn_tradeability_limit_event_proxy_prescreen.md").write_text(
        render_cn_tradeability_limit_event_proxy_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "cn_tradeability_limit_event_proxy_prescreen_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(output_path / "cn_tradeability_limit_event_reference_correlations.csv", result.get("reference_correlations", []), ["lead_factor_name", *REFERENCE_CORRELATION_COLUMNS])
    _write_csv(output_path / "cn_tradeability_limit_event_exposure_correlations.csv", result.get("exposure_correlations", []), ["lead_factor_name", *EXPOSURE_CORRELATION_COLUMNS])
    _write_csv(output_path / "cn_tradeability_limit_event_raw_yearly_ic.csv", result.get("raw_yearly_ic", []), ["factor_name", *YEARLY_IC_COLUMNS])
    _write_csv(output_path / "cn_tradeability_limit_event_industry_neutral_yearly_ic.csv", result.get("industry_neutral_yearly_ic", []), ["factor_name", *YEARLY_IC_COLUMNS])
    _write_csv(output_path / "cn_tradeability_limit_event_residual_yearly_ic.csv", result.get("residual_yearly_ic", []), ["factor_name", *YEARLY_IC_COLUMNS])
    _write_csv(output_path / "cn_tradeability_limit_event_raw_ic_observations.csv", result.get("raw_ic_observations", []), IC_OBSERVATION_COLUMNS)
    _write_csv(output_path / "cn_tradeability_limit_event_industry_neutral_ic_observations.csv", result.get("industry_neutral_ic_observations", []), IC_OBSERVATION_COLUMNS)
    _write_csv(output_path / "cn_tradeability_limit_event_residual_ic_observations.csv", result.get("residual_ic_observations", []), IC_OBSERVATION_COLUMNS)


def render_cn_tradeability_limit_event_proxy_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# CN Tradeability Limit Event Proxy Prescreen Round160",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Industry-neutral rows: {summary.get('industry_neutral_rows', 0)}",
        f"- Residual rows: {summary.get('residual_rows', 0)}",
        f"- Proxy research leads: {summary.get('proxy_research_lead_count', 0)}",
        f"- Portfolio grid allowed candidates: {summary.get('portfolio_grid_allowed_candidates', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- True limit status audit required candidates: {summary.get('true_limit_status_audit_required_candidates', 0)}",
        f"- Next direction: {summary.get('next_direction', NEXT_DIRECTION_WITHOUT_PROXY_LEADS)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Results",
        "",
        "| Factor | H | Raw IC | Raw ICIR | Neutral IC | Residual IC | Residual ICIR | Blocked Rate | Lead | Blockers |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("results", []):
        lines.append(
            "| {factor} | {horizon} | {raw_ic:.4f} | {raw_icir:.3f} | {neutral_ic:.4f} | {resid_ic:.4f} | {resid_icir:.3f} | {blocked:.3f} | {lead} | {blockers} |".format(
                factor=row["factor_name"],
                horizon=row["horizon"],
                raw_ic=row["raw_mean_spearman_ic"],
                raw_icir=row["raw_icir"],
                neutral_ic=row["industry_neutral_mean_spearman_ic"],
                resid_ic=row["residual_mean_spearman_ic"],
                resid_icir=row["residual_icir"],
                blocked=row["tradeability_blocked_signal_rate"],
                lead="yes" if row["proxy_research_lead"] else "no",
                blockers=", ".join(row.get("blockers", [])) if row.get("blockers") else "none",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This is a proxy prescreen, not a portfolio or promotion stage.",
            "- Official true-limit and suspension/tradeability feeds are still required before portfolio conversion.",
            "- Final holdout data remains blocked for tuning.",
        ]
    )
    return "\n".join(lines) + "\n"


def _candidate_value_series(features: pd.DataFrame) -> dict[str, pd.Series]:
    bad_limit_up_exhaustion = (
        0.45 * features["z_limit_up_like_0"]
        + 0.25 * features["z_close_unseal_proxy_1"]
        + 0.20 * features["z_turnover_spike_5"]
        + 0.10 * features["z_neg_log_adv20_amount"]
    )
    bad_failed_limit_up = (
        0.40 * features["z_failed_limit_up_proxy_1"]
        + 0.30 * features["z_weak_close_location_1"]
        + 0.20 * features["z_turnover_spike_5"]
        + 0.10 * features["z_log_adv20_amount"]
    )
    bad_new_high_failure = (
        0.35 * features["z_new_high_20"]
        + 0.35 * features["z_near_limit_up_failure_proxy_1"]
        + 0.20 * features["z_turnover_spike_5"]
        + 0.10 * features["z_log_adv20_amount"]
    )
    return {
        "limit_down_relief_reversal_liquid_1_5": (
            0.40 * features["z_limit_down_relief_proxy"] + 0.30 * features["z_neg_ret_5"] + 0.30 * features["z_log_adv20_amount"]
        ),
        "near_limit_down_rebound_quality_3_10": (
            0.35 * features["z_near_limit_down_count_3"]
            + 0.30 * features["z_non_st_tradeable_quality_10"]
            + 0.20 * features["z_log_adv20_amount"]
            + 0.15 * features["z_neg_realized_vol_20"]
        ),
        "limit_up_exhaustion_avoidance_1_5": -bad_limit_up_exhaustion,
        "failed_limit_up_reversal_1_5": -bad_failed_limit_up,
        "limit_event_cooling_momentum_5_20": (
            0.35 * features["z_post_limit_cooling_days_5"]
            + 0.30 * features["z_ret_20_skip5"]
            + 0.20 * features["z_log_adv20_amount"]
            + 0.15 * features["z_neg_realized_vol_20"]
        ),
        "post_limit_down_nonst_recovery_5_20": (
            0.35 * features["z_post_limit_down_recovery_5"]
            + 0.30 * features["z_non_st_tradeable_quality_10"]
            + 0.20 * features["z_log_adv20_amount"]
            + 0.15 * features["z_neg_downside_vol_20"]
        ),
        "limit_pressure_asymmetry_reversal_5_20": (
            0.45 * features["z_limit_pressure_asymmetry_5"] + 0.30 * features["z_neg_ret_5"] + 0.25 * features["z_log_adv20_amount"]
        ),
        "new_high_near_limit_failure_reversal_20": -bad_new_high_failure,
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
    tradeability_blocked_signal_rate: float,
    min_industries: int,
    min_industry_neutral_mean_ic: float,
    min_industry_neutral_icir: float,
    min_industry_neutral_positive_ic_rate: float,
    min_residual_mean_ic: float,
    min_residual_icir: float,
    min_residual_positive_ic_rate: float,
    max_tradeability_blocked_signal_rate: float,
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
    if tradeability_blocked_signal_rate > max_tradeability_blocked_signal_rate:
        blockers.append("tradeability_blocked_signal_rate_above_threshold")
    if any(row.get("redundancy_class") == "highly_redundant" for row in reference_correlations):
        blockers.append("candidate_highly_redundant_with_limit_event_reference")
    if any(row.get("exposure_class") == "high_exposure" for row in exposure_correlations):
        blockers.append("candidate_high_size_liquidity_or_volatility_exposure")
    if any(row.get("failure") for row in residual_yearly):
        blockers.append("residual_yearly_ic_instability")
    return _dedupe(blockers)


def _normalise_limit_event_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "high", "low", "adj_close", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing required columns: {', '.join(missing)}")
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str)
    if "symbol" not in frame:
        frame["symbol"] = frame["asset_id"]
    if "open" not in frame:
        frame["open"] = frame["adj_close"]
    if "close" not in frame:
        frame["close"] = frame["adj_close"]
    if "volume" not in frame:
        frame["volume"] = 0.0
    for column in ["open", "high", "low", "close", "adj_close", "volume", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["open_raw"] = frame["open"].fillna(frame["adj_close"])
    frame["high_raw"] = frame["high"]
    frame["low_raw"] = frame["low"]
    frame["close_raw"] = frame["close"].fillna(frame["adj_close"])
    frame = frame.dropna(subset=["date", "asset_id", "market", "high_raw", "low_raw", "close_raw", "adj_close", "amount"])
    return (
        frame[
            (frame["market"] == "CN")
            & (frame["close_raw"] > 0)
            & (frame["high_raw"] > 0)
            & (frame["low_raw"] > 0)
            & (frame["amount"] > 0)
        ]
        .drop_duplicates(["asset_id", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _merge_tradeability_metadata(frame: pd.DataFrame, stock_basic: pd.DataFrame | None) -> pd.DataFrame:
    enriched = frame.copy()
    if stock_basic is not None and not stock_basic.empty:
        basic = stock_basic.copy()
        keep = [
            column
            for column in ("asset_id", "symbol", "industry", "name", "stock_market", "list_date", "delist_date", "is_active")
            if column in basic.columns
        ]
        if keep and ("asset_id" in keep or "symbol" in keep):
            on = [column for column in ("asset_id", "symbol") if column in keep and column in enriched.columns]
            if on:
                basic = basic[keep].drop_duplicates(on, keep="last")
                enriched = enriched.merge(basic, on=on, how="left", suffixes=("", "_basic"))
    defaults = {
        "industry": "unknown",
        "name": "",
        "stock_market": "",
        "list_date": pd.NaT,
        "delist_date": pd.NaT,
        "is_active": True,
    }
    for column, default in defaults.items():
        if column not in enriched:
            enriched[column] = default
    enriched["list_date"] = pd.to_datetime(enriched["list_date"], errors="coerce")
    enriched["delist_date"] = pd.to_datetime(enriched["delist_date"], errors="coerce")
    enriched["is_active"] = enriched["is_active"].fillna(True).map(_boolish)
    enriched["name"] = enriched["name"].fillna("").astype(str)
    enriched["stock_market"] = enriched["stock_market"].fillna("").astype(str)
    enriched["industry"] = enriched["industry"].fillna("unknown").astype(str)
    enriched["board"] = [_board(row) for row in enriched.to_dict(orient="records")]
    enriched["st_flag"] = enriched["name"].str.upper().str.contains("ST", regex=False)
    enriched["new_listing_flag"] = (
        enriched["list_date"].notna() & ((enriched["date"] - enriched["list_date"]).dt.days < 120)
    )
    enriched["delisted_or_inactive_flag"] = (
        (~enriched["is_active"].astype(bool))
        | (enriched["delist_date"].notna() & (enriched["date"] >= enriched["delist_date"]))
    )
    enriched["board_permission_blocked"] = enriched["board"].isin({"BSE", "STAR", "CHINEXT"})
    enriched["suspended_proxy"] = (
        enriched[["open_raw", "high_raw", "low_raw", "close_raw"]].isna().any(axis=1)
        | (enriched[["open_raw", "high_raw", "low_raw", "close_raw"]] <= 0).any(axis=1)
        | enriched["volume"].isna()
        | enriched["amount"].isna()
        | (enriched["volume"] <= 0)
        | (enriched["amount"] <= 0)
    )
    enriched["limit_pct_proxy"] = [_limit_pct_proxy(row) for row in enriched.to_dict(orient="records")]
    return enriched


def _board(row: dict[str, Any]) -> str:
    symbol = str(row.get("symbol", ""))
    asset_id = str(row.get("asset_id", ""))
    stock_market = str(row.get("stock_market", "")).lower()
    code = symbol.split(".")[0] if symbol else asset_id.split("_")[-1]
    if "北交" in stock_market or code.startswith(("8", "4")):
        return "BSE"
    if "科创" in stock_market or code.startswith("688"):
        return "STAR"
    if "创业" in stock_market or code.startswith(("300", "301")):
        return "CHINEXT"
    return "MAIN"


def _limit_pct_proxy(row: dict[str, Any]) -> float:
    if bool(row.get("st_flag", False)):
        return 0.05
    board = str(row.get("board", "MAIN")).upper()
    if board in {"STAR", "CHINEXT"}:
        return 0.20
    if board == "BSE":
        return 0.30
    return 0.10


def _tradeability_blocked_rate(frame: pd.DataFrame) -> float:
    if frame.empty or "tradeability_blocked_proxy" not in frame:
        return 0.0
    values = pd.to_numeric(frame["tradeability_blocked_proxy"], errors="coerce").fillna(0.0)
    return float(values.mean()) if len(values) else 0.0


def _cs_zscore(frame: pd.DataFrame, series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    grouped = values.groupby(frame["date"])
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    zscore = (values - mean) / _nonzero(std)
    return zscore.fillna(0.0)


def _load_candidate_specs(preregistration_json: str | Path | None, candidate_specs: Sequence[Any] | None) -> list[Any]:
    if candidate_specs is not None:
        return list(candidate_specs)
    if preregistration_json is None:
        return default_cn_tradeability_limit_event_specs()
    packet = json.loads(Path(preregistration_json).read_text(encoding="utf-8"))
    candidates = [candidate for candidate in packet.get("candidates", []) or [] if isinstance(candidate, dict)]
    return candidates or default_cn_tradeability_limit_event_specs()


def _stock_basic_frame(value: str | Path | pd.DataFrame | None) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    return _load_stock_basic(value) if value is not None else pd.DataFrame()


def _field(spec: Any, name: str) -> Any:
    if isinstance(spec, dict):
        return spec.get(name)
    return getattr(spec, name)


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "asset_id",
            "market",
            "amount",
            "adv20_amount",
            "family",
            "factor_name",
            "factor_value",
            "tradeability_blocked_proxy",
        ]
    )


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


def _boolish(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in {"false", "0", "no", "n", ""}
    return bool(value)


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
