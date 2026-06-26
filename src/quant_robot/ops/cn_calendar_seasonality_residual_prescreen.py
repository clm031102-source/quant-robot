from __future__ import annotations

import csv
import json
import math
import warnings
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.cn_calendar_seasonality_preregistration import (
    SAFETY,
    default_cn_calendar_seasonality_specs,
)
from quant_robot.ops.market_residual_lead_exposure_dedup import (
    IC_OBSERVATION_COLUMNS,
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


STAGE = "cn_calendar_seasonality_residual_prescreen"
ROUND163_SOURCE_REPORT = "docs/research/cn_stock_cn_calendar_seasonality_preregistration_round163_2026-06-23.md"
NEXT_DIRECTION_WITH_LEADS = "round165_cn_calendar_seasonality_cost_capacity_preflight"
NEXT_DIRECTION_WITHOUT_LEADS = "round165_rotate_after_calendar_seasonality_residual_prescreen_failure"
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
    "calendar_coverage_ok",
    "stress_2015_observations",
    "stress_2015_mean_spearman_ic",
    "stress_2015_failure",
    "residual_research_lead",
    "promotion_allowed",
    "portfolio_grid_allowed",
    "blockers",
]
CALENDAR_COVERAGE_COLUMNS = [
    "factor_name",
    "active_date_count",
    "year_count",
    "min_yearly_active_dates",
    "calendar_coverage_ok",
]


def build_cn_calendar_seasonality_residual_prescreen(
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
    min_calendar_dates: int = 20,
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
    features = build_cn_calendar_seasonality_feature_frame(
        bars,
        horizons=tuple(horizons),
        execution_lag=execution_lag,
    )
    result = summarize_cn_calendar_seasonality_residual_prescreen_from_features(
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
        min_calendar_dates=min_calendar_dates,
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
        "final_holdout_use": "read_once_after_residual_prescreen_walk_forward_cost_capacity_clearance_only",
    }
    result["capacity_policy"] = {
        "min_signal_date_amount": min_signal_date_amount,
        "adv20_amount_filter_enabled": True,
        "portfolio_grid_blocked_before_round164_completion": True,
    }
    result["calendar_policy"] = {
        "calendar_states_are_price_return_independent": True,
        "holiday_windows_use_known_trading_calendar_gaps": True,
        "future_return_lookup_for_calendar_state": False,
    }
    result["sampling_policy"] = {
        "sample_every_n_dates": sample_every_n_dates,
        "sampling_used_for_correlations_only": True,
        "raw_industry_residual_ic_use_all_dates": True,
    }
    result["markdown"] = render_cn_calendar_seasonality_residual_prescreen_markdown(result)
    return result


def summarize_cn_calendar_seasonality_residual_prescreen_from_features(
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
    min_calendar_dates: int = 20,
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
    factor_frame = build_cn_calendar_seasonality_factor_frame(
        features,
        candidate_specs=candidate_specs,
        min_signal_date_amount=min_signal_date_amount,
    )
    reference_frame = build_cn_calendar_seasonality_reference_frame(features)
    exposure_frame = build_cn_calendar_seasonality_exposure_frame(features, stock_basic)
    labels = build_cn_calendar_seasonality_labels(features, horizons=requested_horizons)
    results: list[dict[str, Any]] = []
    raw_ic_rows: list[dict[str, Any]] = []
    industry_ic_rows: list[dict[str, Any]] = []
    residual_ic_rows: list[dict[str, Any]] = []
    reference_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []
    raw_yearly_rows: list[dict[str, Any]] = []
    industry_yearly_rows: list[dict[str, Any]] = []
    residual_yearly_rows: list[dict[str, Any]] = []
    calendar_rows: list[dict[str, Any]] = []
    factor_rows = 0
    industry_rows = 0
    residual_rows = 0

    for spec in candidate_specs:
        factor_name = str(_field(spec, "factor_name"))
        family = str(_field(spec, "family"))
        lead = factor_frame[factor_frame["factor_name"] == factor_name].reset_index(drop=True)
        factor_rows += len(lead)
        calendar_coverage = _calendar_coverage(lead, min_calendar_dates=min_calendar_dates)
        calendar_rows.append({"factor_name": factor_name, **calendar_coverage})
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
            stress_2015 = _stress_2015_summary(residual_obs)
            blockers = _row_blockers(
                raw_summary=raw_summary,
                industry_summary=industry_summary,
                residual_summary=residual_summary,
                residual_yearly=residual_yearly,
                reference_correlations=refs,
                exposure_correlations=exposures,
                industry_coverage=_industry_coverage(lead_with_exposures, min_assets_per_industry=min_assets_per_industry),
                calendar_coverage=calendar_coverage,
                stress_2015=stress_2015,
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
                    "calendar_coverage_ok": bool(calendar_coverage["calendar_coverage_ok"]),
                    "stress_2015_observations": int(stress_2015["observations"]),
                    "stress_2015_mean_spearman_ic": stress_2015["mean_spearman_ic"],
                    "stress_2015_failure": bool(stress_2015["failure"]),
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
            "source_preregistration": ROUND163_SOURCE_REPORT,
            "round163_all_8_candidates_counted": True,
            "portfolio_grid_blocked_at_this_stage": True,
            "calendar_state_source": "known_cn_trading_calendar_only",
        },
        "multiple_testing_policy": {
            "method": "all Round163 candidate x horizon tests counted before any promotion claim",
            "round163_candidate_count": len(candidate_specs),
            "test_count": len(results),
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed_before_residual_prescreen": False,
            "requires_next_gate": "cost_capacity_walk_forward_after_calendar_residual_reference_gate",
            "requires_2015_stress_audit": True,
            "requires_calendar_bucket_coverage": True,
        },
        "results": sorted(results, key=lambda row: (not row["residual_research_lead"], -abs(row["residual_mean_spearman_ic"]), row["factor_name"])),
        "calendar_coverage": calendar_rows,
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
    result["markdown"] = render_cn_calendar_seasonality_residual_prescreen_markdown(result)
    return result


def build_cn_calendar_seasonality_feature_frame(
    bars: pd.DataFrame,
    *,
    horizons: tuple[int, ...],
    execution_lag: int,
) -> pd.DataFrame:
    frame = _normalise_bars(bars)
    if frame.empty:
        return pd.DataFrame()
    calendar = _calendar_state_frame(frame["date"].drop_duplicates())
    market_returns = frame.groupby("date", sort=True)["adj_close"].mean().pct_change().rename("market_return_1d")
    pieces = []
    for _, group in frame.groupby("asset_id", sort=False):
        group = group.sort_values("date").copy().reset_index(drop=True)
        close = group["adj_close"]
        open_ = group["open"]
        amount = group["amount"]
        returns = close.pct_change()
        piece = group[["date", "asset_id", "market", "open", "high", "low", "adj_close", "amount", "volume"]].copy()
        piece["return_1d"] = returns
        piece["return_3"] = close.pct_change(3)
        piece["return_5"] = close.pct_change(5)
        piece["return_10"] = close.pct_change(10)
        piece["return_20"] = close.pct_change(20)
        piece["ret_20_skip_5"] = close.shift(5) / _nonzero(close.shift(25)) - 1.0
        piece["gap_ret_1"] = open_ / _nonzero(close.shift(1)) - 1.0
        piece["adv20_amount"] = amount.rolling(20, min_periods=5).mean()
        piece["amount_trend_20_60"] = amount.rolling(20, min_periods=5).mean() / _nonzero(amount.rolling(60, min_periods=20).mean()) - 1.0
        piece["turnover_spike_5"] = amount.rolling(5, min_periods=3).mean() / _nonzero(amount.rolling(20, min_periods=5).mean()) - 1.0
        piece["turnover_spike_10"] = amount.rolling(10, min_periods=5).mean() / _nonzero(amount.rolling(20, min_periods=5).mean()) - 1.0
        piece["realized_vol_20"] = returns.rolling(20, min_periods=5).std(ddof=0)
        for horizon in horizons:
            entry = close.shift(-execution_lag)
            exit_ = close.shift(-(execution_lag + int(horizon)))
            piece[f"forward_return_{int(horizon)}"] = exit_ / entry - 1.0
        pieces.append(piece)
    features = pd.concat(pieces, ignore_index=True)
    features = features.merge(calendar, on="date", how="left", validate="many_to_one")
    features = features.merge(market_returns.reset_index(), on="date", how="left", validate="many_to_one")
    features["beta_to_market_60"] = _rolling_beta_to_market(features)
    features["log_adv20_amount"] = _safe_log(features["adv20_amount"])
    features["log_amount"] = _safe_log(features["amount"])
    z_inputs = {
        "z_ret_5": features["return_5"],
        "z_neg_ret_5": -features["return_5"],
        "z_ret_10": features["return_10"],
        "z_neg_ret_3": -features["return_3"],
        "z_neg_ret_20": -features["return_20"],
        "z_ret_20_skip_5": features["ret_20_skip_5"],
        "z_neg_gap_ret_1": -features["gap_ret_1"],
        "z_log_adv20_amount": features["log_adv20_amount"],
        "z_realized_vol_20": features["realized_vol_20"],
        "z_neg_realized_vol_20": -features["realized_vol_20"],
        "z_turnover_spike_5": features["turnover_spike_5"],
        "z_turnover_spike_10": features["turnover_spike_10"],
        "z_beta_to_market_60": features["beta_to_market_60"],
    }
    for column, values in z_inputs.items():
        features[column] = _cs_zscore(features, values)
    return features.replace([math.inf, -math.inf], np.nan)


def build_cn_calendar_seasonality_factor_frame(
    features: pd.DataFrame,
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
        values_active = values_by_name.get(name)
        if values_active is None:
            continue
        values, active = values_active
        mask = capacity_mask & active.fillna(False)
        frame = features.loc[mask, ["date", "asset_id", "market", "amount", "adv20_amount"]].copy()
        frame["family"] = str(_field(spec, "family"))
        frame["source_evidence_status"] = str(_field(spec, "source_evidence_status"))
        frame["factor_name"] = name
        frame["factor_value"] = pd.to_numeric(values.loc[mask], errors="coerce")
        direction = str(_field(spec, "direction"))
        if direction in {"lower_is_better", "higher_is_worse"}:
            frame["factor_value"] = -frame["factor_value"]
        rows.append(frame.dropna(subset=["factor_value", "amount", "adv20_amount"]))
    if not rows:
        return _empty_factor_frame()
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def build_cn_calendar_seasonality_reference_frame(features: pd.DataFrame) -> pd.DataFrame:
    if features.empty:
        return _empty_factor_frame()
    base = features[["date", "asset_id", "market", "amount", "adv20_amount"]].copy()
    references = {
        "calendar_plain_reversal_reference_5": features["z_neg_ret_5"] + 0.25 * features["z_log_adv20_amount"],
        "calendar_residual_momentum_reference_20": features["z_ret_20_skip_5"] - 0.25 * features["z_beta_to_market_60"],
        "calendar_lowvol_liquidity_reference": features["z_neg_realized_vol_20"] + features["z_log_adv20_amount"],
        "calendar_gap_reversal_reference": features["z_neg_gap_ret_1"] + features["z_neg_ret_3"],
        "calendar_liquidity_reference": features["z_log_adv20_amount"],
    }
    rows = []
    for name, values in references.items():
        frame = base.copy()
        frame["factor_name"] = name
        frame["factor_value"] = pd.to_numeric(values, errors="coerce")
        rows.append(frame.dropna(subset=["factor_value"]))
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def build_cn_calendar_seasonality_exposure_frame(
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
    return exposure.replace([math.inf, -math.inf], np.nan).reset_index(drop=True)


def build_cn_calendar_seasonality_labels(features: pd.DataFrame, *, horizons: tuple[int, ...]) -> pd.DataFrame:
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


def write_cn_calendar_seasonality_residual_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "cn_calendar_seasonality_residual_prescreen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "cn_calendar_seasonality_residual_prescreen.md").write_text(
        render_cn_calendar_seasonality_residual_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "cn_calendar_seasonality_residual_prescreen_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(output_path / "cn_calendar_seasonality_calendar_coverage.csv", result.get("calendar_coverage", []), CALENDAR_COVERAGE_COLUMNS)
    _write_csv(output_path / "cn_calendar_seasonality_reference_correlations.csv", result.get("reference_correlations", []), ["lead_factor_name", *REFERENCE_CORRELATION_COLUMNS])
    _write_csv(output_path / "cn_calendar_seasonality_exposure_correlations.csv", result.get("exposure_correlations", []), ["lead_factor_name", *EXPOSURE_CORRELATION_COLUMNS])
    _write_csv(output_path / "cn_calendar_seasonality_raw_yearly_ic.csv", result.get("raw_yearly_ic", []), ["factor_name", *YEARLY_IC_COLUMNS])
    _write_csv(output_path / "cn_calendar_seasonality_industry_neutral_yearly_ic.csv", result.get("industry_neutral_yearly_ic", []), ["factor_name", *YEARLY_IC_COLUMNS])
    _write_csv(output_path / "cn_calendar_seasonality_residual_yearly_ic.csv", result.get("residual_yearly_ic", []), ["factor_name", *YEARLY_IC_COLUMNS])
    _write_csv(output_path / "cn_calendar_seasonality_raw_ic_observations.csv", result.get("raw_ic_observations", []), IC_OBSERVATION_COLUMNS)
    _write_csv(output_path / "cn_calendar_seasonality_industry_neutral_ic_observations.csv", result.get("industry_neutral_ic_observations", []), IC_OBSERVATION_COLUMNS)
    _write_csv(output_path / "cn_calendar_seasonality_residual_ic_observations.csv", result.get("residual_ic_observations", []), IC_OBSERVATION_COLUMNS)


def render_cn_calendar_seasonality_residual_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# CN Calendar Seasonality Residual Prescreen Round164",
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
        "| Factor | H | Raw IC | Neutral IC | Residual IC | Residual ICIR | 2015 IC | Calendar OK | Lead | Blockers |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for row in result.get("results", []):
        lines.append(
            "| {factor} | {horizon} | {raw_ic:.4f} | {neutral_ic:.4f} | {resid_ic:.4f} | {resid_icir:.3f} | {stress:.4f} | {cal} | {lead} | {blockers} |".format(
                factor=row["factor_name"],
                horizon=row["horizon"],
                raw_ic=row["raw_mean_spearman_ic"],
                neutral_ic=row["industry_neutral_mean_spearman_ic"],
                resid_ic=row["residual_mean_spearman_ic"],
                resid_icir=row["residual_icir"],
                stress=row["stress_2015_mean_spearman_ic"],
                cal="yes" if row["calendar_coverage_ok"] else "no",
                lead="yes" if row["residual_research_lead"] else "no",
                blockers=", ".join(row.get("blockers", [])) if row.get("blockers") else "none",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This is a residual research prescreen, not a portfolio or promotion stage.",
            "- All 8 Round163 candidates are counted in multiple-testing accounting.",
            "- Any lead only earns a later cost/capacity preflight; if no lead survives, rotate families instead of tuning calendar windows.",
        ]
    )
    return "\n".join(lines) + "\n"


def _candidate_value_series(features: pd.DataFrame) -> dict[str, tuple[pd.Series, pd.Series]]:
    return {
        "turn_of_month_reversal_liquid_5_5": (
            features["z_neg_ret_5"] + 0.25 * features["z_log_adv20_amount"] - 0.20 * features["z_realized_vol_20"],
            features["ex_ante_turn_of_month_window"],
        ),
        "turn_of_month_residual_momentum_20_5": (
            features["z_ret_20_skip_5"] - 0.25 * features["z_beta_to_market_60"],
            features["ex_ante_turn_of_month_window"],
        ),
        "month_end_crowding_exhaustion_10_5": (
            features["z_ret_10"] + features["z_turnover_spike_10"] + features["z_realized_vol_20"],
            features["ex_ante_last_3_trading_days_of_month"],
        ),
        "month_start_liquidity_recovery_5_5": (
            0.45 * features["z_log_adv20_amount"] + 0.35 * features["z_neg_ret_5"] - 0.20 * features["z_realized_vol_20"],
            features["ex_ante_first_3_trading_days_of_month"],
        ),
        "pre_holiday_liquidity_avoidance_5_3": (
            features["z_turnover_spike_5"] + features["z_ret_5"] - features["z_realized_vol_20"],
            features["ex_ante_pre_holiday_1_to_3_trading_days"],
        ),
        "post_holiday_gap_reversal_quality_3_5": (
            0.50 * features["z_neg_gap_ret_1"] + 0.30 * features["z_neg_ret_3"] + 0.20 * features["z_neg_realized_vol_20"],
            features["ex_ante_first_3_sessions_after_holiday"],
        ),
        "weekday_monday_reversal_quality_5_5": (
            0.45 * features["z_neg_ret_5"] + 0.35 * features["z_neg_realized_vol_20"] + 0.20 * features["z_log_adv20_amount"],
            features["ex_ante_weekday_monday"],
        ),
        "quarter_end_liquidity_window_reversal_20_5": (
            0.40 * features["z_neg_ret_20"] + 0.35 * features["z_log_adv20_amount"] - 0.25 * features["z_realized_vol_20"],
            features["ex_ante_quarter_end_window"],
        ),
    }


def _calendar_state_frame(dates: pd.Series) -> pd.DataFrame:
    calendar = pd.DataFrame({"date": pd.to_datetime(dates, errors="coerce").dropna().drop_duplicates().sort_values()})
    calendar = calendar.reset_index(drop=True)
    calendar["weekday"] = calendar["date"].dt.weekday
    month_group = calendar["date"].dt.to_period("M")
    quarter_group = calendar["date"].dt.to_period("Q")
    calendar["month_rank_start"] = calendar.groupby(month_group).cumcount() + 1
    month_count = calendar.groupby(month_group)["date"].transform("count")
    calendar["month_rank_end"] = month_count - calendar["month_rank_start"] + 1
    calendar["quarter_rank_start"] = calendar.groupby(quarter_group).cumcount() + 1
    quarter_count = calendar.groupby(quarter_group)["date"].transform("count")
    calendar["quarter_rank_end"] = quarter_count - calendar["quarter_rank_start"] + 1
    pre_holiday = pd.Series(False, index=calendar.index)
    post_holiday = pd.Series(False, index=calendar.index)
    gaps_to_next = calendar["date"].shift(-1) - calendar["date"]
    gaps_from_prev = calendar["date"] - calendar["date"].shift(1)
    for idx in calendar.index[gaps_to_next.dt.days.fillna(0) > 3]:
        pre_holiday.iloc[max(0, idx - 2) : idx + 1] = True
    for idx in calendar.index[gaps_from_prev.dt.days.fillna(0) > 3]:
        post_holiday.iloc[idx : min(len(calendar), idx + 3)] = True
    calendar["ex_ante_first_3_trading_days_of_month"] = calendar["month_rank_start"] <= 3
    calendar["ex_ante_last_3_trading_days_of_month"] = calendar["month_rank_end"] <= 3
    calendar["ex_ante_turn_of_month_window"] = (
        calendar["ex_ante_first_3_trading_days_of_month"] | calendar["ex_ante_last_3_trading_days_of_month"]
    )
    calendar["ex_ante_weekday_monday"] = calendar["weekday"] == 0
    calendar["ex_ante_pre_holiday_1_to_3_trading_days"] = pre_holiday
    calendar["ex_ante_first_3_sessions_after_holiday"] = post_holiday
    calendar["ex_ante_quarter_end_window"] = calendar["quarter_rank_end"] <= 5
    keep = [
        "date",
        "ex_ante_first_3_trading_days_of_month",
        "ex_ante_last_3_trading_days_of_month",
        "ex_ante_turn_of_month_window",
        "ex_ante_weekday_monday",
        "ex_ante_pre_holiday_1_to_3_trading_days",
        "ex_ante_first_3_sessions_after_holiday",
        "ex_ante_quarter_end_window",
    ]
    return calendar[keep]


def _row_blockers(
    *,
    raw_summary: dict[str, Any],
    industry_summary: dict[str, Any],
    residual_summary: dict[str, Any],
    residual_yearly: list[dict[str, Any]],
    reference_correlations: list[dict[str, Any]],
    exposure_correlations: list[dict[str, Any]],
    industry_coverage: dict[str, Any],
    calendar_coverage: dict[str, Any],
    stress_2015: dict[str, Any],
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
    if any(row.get("failure") for row in residual_yearly):
        blockers.append("residual_yearly_ic_instability")
    if any(row.get("redundancy_class") == "highly_redundant" for row in reference_correlations):
        blockers.append("candidate_highly_redundant_with_calendar_reference")
    if any(row.get("exposure_class") == "high_exposure" for row in exposure_correlations):
        blockers.append("candidate_high_size_liquidity_or_volatility_exposure")
    if not calendar_coverage.get("calendar_coverage_ok", False):
        blockers.append("calendar_bucket_coverage_below_threshold")
    if stress_2015.get("failure", False):
        blockers.append("stress_2015_residual_failure")
    return _dedupe(blockers)


def _calendar_coverage(lead: pd.DataFrame, *, min_calendar_dates: int) -> dict[str, Any]:
    if lead.empty:
        return {
            "active_date_count": 0,
            "year_count": 0,
            "min_yearly_active_dates": 0,
            "calendar_coverage_ok": False,
        }
    dates = pd.to_datetime(lead["date"], errors="coerce").dropna().drop_duplicates()
    yearly = dates.groupby(dates.dt.year).count()
    min_yearly = int(yearly.min()) if not yearly.empty else 0
    required_yearly = min(3, int(min_calendar_dates))
    return {
        "active_date_count": int(len(dates)),
        "year_count": int(len(yearly)),
        "min_yearly_active_dates": min_yearly,
        "calendar_coverage_ok": bool(len(dates) >= min_calendar_dates and min_yearly >= required_yearly),
    }


def _stress_2015_summary(obs: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for row in obs if str(row.get("date", ""))[:4] == "2015"]
    if not rows:
        return {"observations": 0, "mean_spearman_ic": 0.0, "failure": False}
    values = [float(row.get("spearman_ic", 0.0)) for row in rows if math.isfinite(float(row.get("spearman_ic", 0.0)))]
    mean_ic = float(np.mean(values)) if values else 0.0
    return {"observations": len(values), "mean_spearman_ic": mean_ic, "failure": bool(len(values) < 3 or mean_ic <= 0.0)}


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    if bars.empty:
        return pd.DataFrame()
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    if "market" not in frame:
        frame["market"] = "CN"
    frame["market"] = frame["market"].fillna("CN").astype(str)
    if "adj_close" not in frame and "close" in frame:
        frame["adj_close"] = frame["close"]
    if "open" not in frame:
        frame["open"] = frame["adj_close"]
    if "close" not in frame:
        frame["close"] = frame["adj_close"]
    if "volume" not in frame:
        frame["volume"] = 0.0
    for column in ["open", "high", "low", "close", "adj_close", "volume", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = (
        frame[(frame["market"] == "CN") & (frame["adj_close"] > 0) & (frame["amount"] > 0)]
        .dropna(subset=["date", "asset_id", "market", "adj_close", "amount"])
        .drop_duplicates(["asset_id", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )
    if "high" not in frame:
        frame["high"] = frame[["open", "adj_close"]].max(axis=1)
    if "low" not in frame:
        frame["low"] = frame[["open", "adj_close"]].min(axis=1)
    return frame


def _rolling_beta_to_market(features: pd.DataFrame) -> pd.Series:
    rows = []
    for _, group in features[["asset_id", "date", "return_1d", "market_return_1d"]].groupby("asset_id", sort=False):
        cov = group["return_1d"].rolling(60, min_periods=20).cov(group["market_return_1d"])
        var = group["market_return_1d"].rolling(60, min_periods=20).var()
        rows.append(cov / _nonzero(var))
    return pd.concat(rows).sort_index()


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
        return default_cn_calendar_seasonality_specs()
    packet = json.loads(Path(preregistration_json).read_text(encoding="utf-8"))
    candidates = [candidate for candidate in packet.get("candidates", []) or [] if isinstance(candidate, dict)]
    return candidates or default_cn_calendar_seasonality_specs()


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


def _nonzero(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace(0.0, np.nan)


def _dedupe(values: list[str]) -> list[str]:
    output = []
    for value in values:
        if value not in output:
            output.append(value)
    return output


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: Sequence[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return ";".join(str(item) for item in value)
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


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
    value = pd.to_datetime(frame[column], errors="coerce").min()
    return None if pd.isna(value) else value.date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    value = pd.to_datetime(frame[column], errors="coerce").max()
    return None if pd.isna(value) else value.date().isoformat()
