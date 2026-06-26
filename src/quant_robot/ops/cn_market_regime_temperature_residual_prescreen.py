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
from quant_robot.ops.cn_market_regime_temperature_preregistration import (
    SAFETY,
    default_cn_market_regime_temperature_specs,
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


STAGE = "cn_market_regime_temperature_residual_prescreen"
ROUND161_SOURCE_REPORT = "docs/research/cn_stock_cn_market_regime_temperature_preregistration_round161_2026-06-23.md"
NEXT_DIRECTION_WITH_LEADS = "round163_china_market_regime_temperature_state_coverage_dedup_preflight"
NEXT_DIRECTION_WITHOUT_LEADS = "round163_rotate_after_china_market_regime_temperature_residual_prescreen_failure"
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
    "state_coverage_ok",
    "residual_research_lead",
    "promotion_allowed",
    "portfolio_grid_allowed",
    "blockers",
]


def build_cn_market_regime_temperature_residual_prescreen(
    *,
    bars_roots: Iterable[str | Path],
    stock_basic: str | Path | pd.DataFrame | None,
    factor_inputs_root: str | Path | pd.DataFrame | None = None,
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
    factor_inputs = load_cn_market_regime_temperature_factor_inputs(
        factor_inputs_root,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
    )
    features = build_cn_market_regime_temperature_feature_frame(
        bars,
        factor_inputs=factor_inputs,
        stock_basic=stock_basic_frame,
        execution_lag=execution_lag,
    )
    result = summarize_cn_market_regime_temperature_residual_prescreen_from_features(
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
    result["factor_inputs_root"] = str(factor_inputs_root) if isinstance(factor_inputs_root, (str, Path)) else None
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
        "portfolio_grid_blocked_before_round162_completion": True,
    }
    result["sampling_policy"] = {
        "sample_every_n_dates": sample_every_n_dates,
        "sampling_used_for_correlations_only": True,
        "raw_industry_residual_ic_use_all_dates": True,
    }
    result["markdown"] = render_cn_market_regime_temperature_residual_prescreen_markdown(result)
    return result


def summarize_cn_market_regime_temperature_residual_prescreen_from_features(
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
    factor_frame = build_cn_market_regime_temperature_factor_frame(
        features,
        candidate_specs=candidate_specs,
        min_signal_date_amount=min_signal_date_amount,
    )
    reference_frame = build_cn_market_regime_temperature_reference_frame(features)
    exposure_frame = build_cn_market_regime_temperature_exposure_frame(features, stock_basic)
    labels = build_cn_market_regime_temperature_labels(features, horizons=requested_horizons)
    results: list[dict[str, Any]] = []
    raw_ic_rows: list[dict[str, Any]] = []
    industry_ic_rows: list[dict[str, Any]] = []
    residual_ic_rows: list[dict[str, Any]] = []
    reference_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []
    raw_yearly_rows: list[dict[str, Any]] = []
    industry_yearly_rows: list[dict[str, Any]] = []
    residual_yearly_rows: list[dict[str, Any]] = []
    state_coverage_rows: list[dict[str, Any]] = []
    factor_rows = 0
    industry_rows = 0
    residual_rows = 0

    for spec in candidate_specs:
        factor_name = str(_field(spec, "factor_name"))
        family = str(_field(spec, "family"))
        lead = factor_frame[factor_frame["factor_name"] == factor_name].reset_index(drop=True)
        factor_rows += len(lead)
        state_coverage = _state_coverage(lead)
        state_coverage_rows.append({"factor_name": factor_name, **state_coverage})
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
                state_coverage=state_coverage,
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
                    "state_coverage_ok": bool(state_coverage["state_coverage_ok"]),
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
            "source_preregistration": ROUND161_SOURCE_REPORT,
            "next_required_gate": "round162_china_market_regime_temperature_residual_prescreen",
            "lagged_regime_state_required": True,
            "portfolio_grid_blocked_before_residual_prescreen": True,
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed_before_state_coverage_dedup": False,
            "requires_state_coverage_dedup": True,
            "requires_cost_capacity_walk_forward": True,
            "requires_regime_coverage": True,
            "requires_multiple_testing_accounting": True,
            "next_direction": next_direction,
        },
        "results": sorted(results, key=lambda row: (not row["residual_research_lead"], row["family"], -abs(row["residual_mean_spearman_ic"]))),
        "state_coverage": state_coverage_rows,
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
    result["markdown"] = render_cn_market_regime_temperature_residual_prescreen_markdown(result)
    return result


def load_cn_market_regime_temperature_factor_inputs(
    factor_inputs_root: str | Path | pd.DataFrame | None,
    *,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
) -> pd.DataFrame:
    if factor_inputs_root is None:
        return pd.DataFrame(columns=["date", "asset_id", "market", "pb"])
    if isinstance(factor_inputs_root, pd.DataFrame):
        frame = factor_inputs_root.copy()
    else:
        root = Path(factor_inputs_root)
        files: list[Path] = []
        if root.is_file():
            files = [root]
        else:
            base = root / "processed" / "factor_inputs" if (root / "processed" / "factor_inputs").exists() else root
            files = sorted([*base.rglob("*.parquet"), *base.rglob("*.csv")])
        frames = [_read_table(file) for file in files]
        frames = [frame for frame in frames if not frame.empty]
        frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if frame.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", "pb"])
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    if "market" not in frame:
        frame["market"] = "CN"
    keep = ["date", "asset_id", "market", *[col for col in ["pb", "pe", "turnover_rate", "turnover_rate_f", "total_mv", "circ_mv"] if col in frame]]
    frame = frame[keep].dropna(subset=["date", "asset_id"])
    start = pd.Timestamp(analysis_start_date)
    end = pd.Timestamp(analysis_end_date)
    frame = frame[(frame["date"] >= start) & (frame["date"] <= end)]
    return frame.drop_duplicates(["date", "asset_id", "market"], keep="last").reset_index(drop=True)


def build_cn_market_regime_temperature_feature_frame(
    bars: pd.DataFrame,
    *,
    factor_inputs: pd.DataFrame | None = None,
    stock_basic: pd.DataFrame | None = None,
    execution_lag: int = 1,
    market_z_window: int = 252,
) -> pd.DataFrame:
    frame = _normalise_bars(bars)
    if frame.empty:
        return frame
    frame = _merge_factor_inputs(frame, factor_inputs)
    frame = _merge_stock_basic_industry(frame, stock_basic)
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    price = pd.to_numeric(frame["adj_close"] if "adj_close" in frame else frame["close"], errors="coerce")
    close = pd.to_numeric(frame["close"], errors="coerce")
    frame["price"] = price.where(price > 0, close)
    grouped = frame.groupby("asset_id", sort=False)
    frame["return_1d"] = grouped["price"].pct_change()
    frame["ret_5"] = grouped["price"].pct_change(5)
    frame["ret_10"] = grouped["price"].pct_change(10)
    frame["ret_20"] = grouped["price"].pct_change(20)
    frame["ret_60"] = grouped["price"].pct_change(60)
    frame["ret_20_skip_5"] = grouped["price"].shift(5) / grouped["price"].shift(25) - 1.0
    frame["forward_base_price"] = grouped["price"].shift(-int(execution_lag))
    for horizon in [5, 10, 20]:
        frame[f"forward_return_{horizon}"] = grouped["price"].shift(-(int(execution_lag) + horizon)) / frame["forward_base_price"] - 1.0
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    frame["volume"] = pd.to_numeric(frame.get("volume", pd.Series(index=frame.index)), errors="coerce")
    frame["adv20_amount"] = grouped["amount"].transform(lambda series: series.rolling(20, min_periods=5).mean())
    frame["log_adv20_amount"] = _safe_log(frame["adv20_amount"])
    frame["log_amount"] = _safe_log(frame["amount"])
    frame["realized_vol_20"] = grouped["return_1d"].transform(lambda series: series.rolling(20, min_periods=10).std())
    frame["amount_trend_20_60"] = grouped["amount"].transform(
        lambda series: series.rolling(20, min_periods=5).mean() / series.rolling(60, min_periods=20).mean() - 1.0
    )
    frame["turnover_spike_10"] = grouped["amount"].transform(
        lambda series: series / series.rolling(10, min_periods=5).mean() - 1.0
    )
    market = _market_temperature_frame(frame, market_z_window=market_z_window, execution_lag=execution_lag)
    frame = frame.merge(market, on="date", how="left", validate="many_to_one")
    frame["beta_to_market_60"] = _rolling_beta_to_market(frame)
    for column in [
        "ret_5",
        "ret_10",
        "ret_20",
        "ret_60",
        "ret_20_skip_5",
        "realized_vol_20",
        "log_adv20_amount",
        "amount_trend_20_60",
        "turnover_spike_10",
        "beta_to_market_60",
        "pb",
    ]:
        if column in frame:
            frame[f"z_{column}"] = _cs_zscore(frame, column)
    return frame.replace([math.inf, -math.inf], np.nan).reset_index(drop=True)


def build_cn_market_regime_temperature_factor_frame(
    features: pd.DataFrame,
    *,
    candidate_specs: Sequence[Any],
    min_signal_date_amount: float,
) -> pd.DataFrame:
    if features.empty:
        return _empty_factor_frame()
    values = _candidate_values(features)
    base = features[["date", "asset_id", "market", "amount", "adv20_amount", "lag_temp_state"]].copy()
    capacity_mask = (
        (pd.to_numeric(features["amount"], errors="coerce") >= min_signal_date_amount)
        & (pd.to_numeric(features["adv20_amount"], errors="coerce") >= min_signal_date_amount)
        & (pd.to_numeric(features["return_1d"], errors="coerce").abs() <= 0.50)
    )
    rows: list[pd.DataFrame] = []
    for spec in candidate_specs:
        factor_name = str(_field(spec, "factor_name"))
        series, active_mask = values.get(factor_name, (pd.Series(np.nan, index=features.index), pd.Series(False, index=features.index)))
        frame = base.loc[capacity_mask & active_mask].copy()
        frame["family"] = str(_field(spec, "family"))
        frame["factor_name"] = factor_name
        frame["factor_value"] = pd.to_numeric(series.loc[frame.index], errors="coerce")
        direction = str(_field(spec, "direction"))
        if direction in {"lower_is_better", "higher_is_worse"}:
            frame["factor_value"] = -frame["factor_value"]
        frame = frame.dropna(subset=["factor_value", "amount", "adv20_amount"])
        rows.append(frame)
    if not rows:
        return _empty_factor_frame()
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def build_cn_market_regime_temperature_reference_frame(features: pd.DataFrame) -> pd.DataFrame:
    if features.empty:
        return _empty_factor_frame()
    base = features[["date", "asset_id", "market"]].copy()
    refs = {
        "market_regime_return_20_reference": features.get("z_ret_20", pd.Series(np.nan, index=features.index)),
        "market_regime_lowvol_reference": -features.get("z_realized_vol_20", pd.Series(np.nan, index=features.index)),
        "market_regime_liquidity_reference": features.get("z_log_adv20_amount", pd.Series(np.nan, index=features.index)),
        "market_regime_value_reference": -features.get("z_pb", pd.Series(np.nan, index=features.index)),
    }
    rows = []
    for name, values in refs.items():
        frame = base.copy()
        frame["factor_name"] = name
        frame["factor_value"] = pd.to_numeric(values, errors="coerce")
        rows.append(frame.dropna(subset=["factor_value"]))
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def build_cn_market_regime_temperature_exposure_frame(
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
            "ret_20",
        ]
    ].rename(columns={"ret_20": "return_20"})
    exposure = _merge_stock_basic_industry(exposure, stock_basic)
    return exposure.replace([math.inf, -math.inf], np.nan).reset_index(drop=True)


def build_cn_market_regime_temperature_labels(features: pd.DataFrame, *, horizons: tuple[int, ...]) -> pd.DataFrame:
    rows = []
    for horizon in horizons:
        column = f"forward_return_{int(horizon)}"
        if column not in features:
            continue
        labels = features[["date", "asset_id", "market", column]].rename(columns={column: "forward_return"}).copy()
        labels["horizon"] = int(horizon)
        rows.append(labels.dropna(subset=["forward_return"]))
    if not rows:
        return pd.DataFrame(columns=["date", "asset_id", "market", "horizon", "forward_return"])
    return pd.concat(rows, ignore_index=True).reset_index(drop=True)


def write_cn_market_regime_temperature_residual_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "cn_market_regime_temperature_residual_prescreen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "cn_market_regime_temperature_residual_prescreen.md").write_text(
        render_cn_market_regime_temperature_residual_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "cn_market_regime_temperature_residual_prescreen_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(output_path / "cn_market_regime_temperature_state_coverage.csv", result.get("state_coverage", []), ["factor_name", "date_count", "state_count", "min_state_date_count", "state_coverage_ok"])
    _write_csv(output_path / "cn_market_regime_temperature_reference_correlations.csv", result.get("reference_correlations", []), ["lead_factor_name", *REFERENCE_CORRELATION_COLUMNS])
    _write_csv(output_path / "cn_market_regime_temperature_exposure_correlations.csv", result.get("exposure_correlations", []), ["lead_factor_name", *EXPOSURE_CORRELATION_COLUMNS])
    _write_csv(output_path / "cn_market_regime_temperature_raw_yearly_ic.csv", result.get("raw_yearly_ic", []), ["factor_name", *YEARLY_IC_COLUMNS])
    _write_csv(output_path / "cn_market_regime_temperature_industry_neutral_yearly_ic.csv", result.get("industry_neutral_yearly_ic", []), ["factor_name", *YEARLY_IC_COLUMNS])
    _write_csv(output_path / "cn_market_regime_temperature_residual_yearly_ic.csv", result.get("residual_yearly_ic", []), ["factor_name", *YEARLY_IC_COLUMNS])
    _write_csv(output_path / "cn_market_regime_temperature_raw_ic_observations.csv", result.get("raw_ic_observations", []), IC_OBSERVATION_COLUMNS)
    _write_csv(output_path / "cn_market_regime_temperature_industry_neutral_ic_observations.csv", result.get("industry_neutral_ic_observations", []), IC_OBSERVATION_COLUMNS)
    _write_csv(output_path / "cn_market_regime_temperature_residual_ic_observations.csv", result.get("residual_ic_observations", []), IC_OBSERVATION_COLUMNS)


def render_cn_market_regime_temperature_residual_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# CN Market Regime Temperature Residual Prescreen Round162",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Industry-neutral rows: {summary.get('industry_neutral_rows', 0)}",
        f"- Residual rows: {summary.get('residual_rows', 0)}",
        f"- Residual research leads: {summary.get('residual_research_lead_count', 0)}",
        f"- Portfolio grid candidates: {summary.get('portfolio_grid_allowed_candidates', 0)}",
        f"- Promotion candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Next direction: `{summary.get('next_direction', '')}`",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Results",
        "",
        "| Factor | Raw IC | Neutral IC | Residual IC | Residual ICIR | IC+ | State OK | Lead | Blockers |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in result.get("results", []):
        lines.append(
            "| {factor} | {raw:.4f} | {neutral:.4f} | {resid:.4f} | {icir:.3f} | {pos:.1%} | {state} | {lead} | {blockers} |".format(
                factor=row.get("factor_name", ""),
                raw=row.get("raw_mean_spearman_ic", 0.0),
                neutral=row.get("industry_neutral_mean_spearman_ic", 0.0),
                resid=row.get("residual_mean_spearman_ic", 0.0),
                icir=row.get("residual_icir", 0.0),
                pos=row.get("residual_positive_ic_rate", 0.0),
                state=row.get("state_coverage_ok", False),
                lead=row.get("residual_research_lead", False),
                blockers=", ".join(row.get("blockers", [])) if row.get("blockers") else "none",
            )
        )
    return "\n".join(lines) + "\n"


def _candidate_values(features: pd.DataFrame) -> dict[str, tuple[pd.Series, pd.Series]]:
    idx = features.index
    false = pd.Series(False, index=idx)
    liq_cold = pd.to_numeric(features.get("lag_mkt_liquidity_temp_z"), errors="coerce") < -1.0
    hot = pd.to_numeric(features.get("lag_mkt_turnover_temp_z"), errors="coerce") > 1.0
    breadth_recovery = pd.to_numeric(features.get("lag_breadth_recovery_20"), errors="coerce") > 0.0
    dispersion_high = pd.to_numeric(features.get("lag_cross_sectional_dispersion_z"), errors="coerce") > 1.0
    index_low = pd.to_numeric(features.get("lag_index_location_252"), errors="coerce") < 0.35
    normal = pd.Series(True, index=idx)
    values = {
        "regime_cold_liquidity_reversal_quality_20_5": (
            _z(features, "ret_20", sign=-1.0) + 0.30 * _z(features, "log_adv20_amount") - 0.20 * _z(features, "realized_vol_20"),
            liq_cold.fillna(False),
        ),
        "regime_hot_turnover_exhaustion_avoidance_10_5": (
            _z(features, "turnover_spike_10") + _z(features, "ret_10") - _z(features, "realized_vol_20"),
            hot.fillna(False),
        ),
        "breadth_recovery_residual_momentum_20_10": (
            _z(features, "ret_20_skip_5") - 0.25 * _z(features, "beta_to_market_60"),
            breadth_recovery.fillna(False),
        ),
        "dispersion_high_lowvol_residual_reversal_20_5": (
            _z(features, "ret_20", sign=-1.0) - _z(features, "realized_vol_20") + 0.20 * _z(features, "log_adv20_amount"),
            dispersion_high.fillna(False),
        ),
        "index_location_low_residual_value_liquidity_60_10": (
            0.35 * _z(features, "pb", sign=-1.0) + 0.35 * _z(features, "log_adv20_amount") + 0.30 * _z(features, "ret_60", sign=-1.0),
            index_low.fillna(False),
        ),
        "market_temperature_state_interaction_composite_20_5": (
            0.35 * _z(features, "ret_20", sign=-1.0)
            + 0.25 * _z(features, "ret_20_skip_5")
            - 0.20 * _z(features, "realized_vol_20")
            + 0.20 * _z(features, "log_adv20_amount"),
            normal,
        ),
    }
    return {name: (pd.to_numeric(value, errors="coerce"), active.reindex(idx, fill_value=False)) for name, (value, active) in values.items()} or {"": (pd.Series(np.nan, index=idx), false)}


def _market_temperature_frame(frame: pd.DataFrame, *, market_z_window: int, execution_lag: int) -> pd.DataFrame:
    daily = frame.groupby("date", sort=True).agg(
        mkt_ret_1d=("return_1d", "mean"),
        mkt_amount=("amount", "sum"),
        breadth_20=("ret_20", lambda series: float((pd.to_numeric(series, errors="coerce") > 0).mean())),
        cross_sectional_dispersion=("return_1d", "std"),
    ).reset_index()
    daily["mkt_curve"] = (1.0 + pd.to_numeric(daily["mkt_ret_1d"], errors="coerce").fillna(0.0)).cumprod()
    daily["mkt_liquidity_temp_z"] = _rolling_z(_safe_log(daily["mkt_amount"]), market_z_window)
    daily["mkt_turnover_temp_z"] = daily["mkt_liquidity_temp_z"]
    daily["cross_sectional_dispersion_z"] = _rolling_z(daily["cross_sectional_dispersion"], market_z_window)
    daily["breadth_recovery_20"] = daily["breadth_20"] - daily["breadth_20"].rolling(20, min_periods=5).mean()
    low = daily["mkt_curve"].rolling(252, min_periods=20).min()
    high = daily["mkt_curve"].rolling(252, min_periods=20).max()
    daily["index_location_252"] = (daily["mkt_curve"] - low) / (high - low).replace(0, np.nan)
    state = np.select(
        [
            daily["mkt_liquidity_temp_z"] < -1.0,
            daily["mkt_turnover_temp_z"] > 1.0,
            daily["cross_sectional_dispersion_z"] > 1.0,
        ],
        ["cold_liquidity", "hot_turnover", "high_dispersion"],
        default="normal",
    )
    daily["temp_state"] = state
    lag_cols = [
        "mkt_liquidity_temp_z",
        "mkt_turnover_temp_z",
        "breadth_recovery_20",
        "cross_sectional_dispersion_z",
        "index_location_252",
        "temp_state",
    ]
    for col in lag_cols:
        daily[f"lag_{col}"] = daily[col].shift(int(execution_lag))
    return daily


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    if bars.empty:
        return pd.DataFrame()
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    if "market" not in frame:
        frame["market"] = "CN"
    for col in ["open", "high", "low", "close", "adj_close", "volume", "amount"]:
        if col in frame:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame.dropna(subset=["date", "asset_id", "close"]).sort_values(["asset_id", "date"]).reset_index(drop=True)


def _merge_factor_inputs(frame: pd.DataFrame, factor_inputs: pd.DataFrame | None) -> pd.DataFrame:
    if factor_inputs is None or factor_inputs.empty:
        output = frame.copy()
        output["pb"] = np.nan
        return output
    inputs = factor_inputs.copy()
    inputs["date"] = pd.to_datetime(inputs["date"], errors="coerce")
    inputs["asset_id"] = inputs["asset_id"].astype(str)
    if "market" not in inputs:
        inputs["market"] = "CN"
    cols = ["date", "asset_id", "market", *[col for col in ["pb", "pe", "turnover_rate", "turnover_rate_f", "total_mv", "circ_mv"] if col in inputs]]
    return frame.merge(inputs[cols], on=["date", "asset_id", "market"], how="left", validate="many_to_one")


def _rolling_beta_to_market(frame: pd.DataFrame) -> pd.Series:
    work = frame[["asset_id", "date", "return_1d", "mkt_ret_1d"]].copy()
    values = []
    for _, group in work.groupby("asset_id", sort=False):
        cov = group["return_1d"].rolling(60, min_periods=20).cov(group["mkt_ret_1d"])
        var = group["mkt_ret_1d"].rolling(60, min_periods=20).var()
        values.append(cov / var.replace(0, np.nan))
    return pd.concat(values).sort_index()


def _cs_zscore(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="coerce")
    mean = values.groupby(frame["date"]).transform("mean")
    std = values.groupby(frame["date"]).transform("std").replace(0, np.nan)
    return ((values - mean) / std).fillna(0.0)


def _rolling_z(series: pd.Series, window: int) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    mean = numeric.rolling(window, min_periods=max(5, min(window, 20))).mean()
    std = numeric.rolling(window, min_periods=max(5, min(window, 20))).std().replace(0, np.nan)
    return (numeric - mean) / std


def _z(features: pd.DataFrame, column: str, *, sign: float = 1.0) -> pd.Series:
    zcol = f"z_{column}"
    if zcol in features:
        return sign * pd.to_numeric(features[zcol], errors="coerce")
    return pd.Series(np.nan, index=features.index)


def _state_coverage(lead: pd.DataFrame) -> dict[str, Any]:
    if lead.empty or "lag_temp_state" not in lead:
        return {"date_count": 0, "state_count": 0, "min_state_date_count": 0, "state_coverage_ok": False}
    state_dates = lead.dropna(subset=["lag_temp_state"]).groupby("lag_temp_state")["date"].nunique()
    min_count = int(state_dates.min()) if not state_dates.empty else 0
    return {
        "date_count": int(lead["date"].nunique()),
        "state_count": int(len(state_dates)),
        "min_state_date_count": min_count,
        "state_coverage_ok": bool(len(state_dates) >= 1 and min_count >= 5),
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
    state_coverage: dict[str, Any],
    min_industries: int,
    min_industry_neutral_mean_ic: float,
    min_industry_neutral_icir: float,
    min_industry_neutral_positive_ic_rate: float,
    min_residual_mean_ic: float,
    min_residual_icir: float,
    min_residual_positive_ic_rate: float,
) -> list[str]:
    blockers: list[str] = []
    if industry_summary["mean_spearman_ic"] < min_industry_neutral_mean_ic:
        blockers.append("industry_neutral_mean_ic_below_threshold")
    if industry_summary["icir"] < min_industry_neutral_icir:
        blockers.append("industry_neutral_icir_below_threshold")
    if industry_summary["positive_ic_rate"] < min_industry_neutral_positive_ic_rate:
        blockers.append("industry_neutral_positive_ic_rate_below_threshold")
    if residual_summary["mean_spearman_ic"] < min_residual_mean_ic:
        blockers.append("residual_mean_ic_below_threshold")
    if residual_summary["icir"] < min_residual_icir:
        blockers.append("residual_icir_below_threshold")
    if residual_summary["positive_ic_rate"] < min_residual_positive_ic_rate:
        blockers.append("residual_positive_ic_rate_below_threshold")
    if sum(row.get("failure") for row in residual_yearly) > 0:
        blockers.append("residual_yearly_instability")
    if int(industry_coverage.get("median_industries", 0)) < min_industries:
        blockers.append("industry_breadth_below_threshold")
    if not state_coverage.get("state_coverage_ok", False):
        blockers.append("state_coverage_below_threshold")
    if any(row.get("redundancy_class") == "highly_redundant" for row in reference_correlations):
        blockers.append("candidate_highly_redundant_with_reference")
    if any(row.get("exposure_class") == "high_exposure" for row in exposure_correlations):
        blockers.append("candidate_high_size_liquidity_or_volatility_exposure")
    if raw_summary["ic_observations"] <= 0:
        blockers.append("no_raw_ic_observations")
    return blockers


def _load_candidate_specs(preregistration_json: str | Path | None, candidate_specs: Sequence[Any] | None) -> list[Any]:
    if candidate_specs is not None:
        return list(candidate_specs)
    if preregistration_json:
        payload = json.loads(Path(preregistration_json).read_text(encoding="utf-8"))
        return list(payload.get("candidates", []))
    return default_cn_market_regime_temperature_specs()


def _stock_basic_frame(stock_basic: str | Path | pd.DataFrame | None) -> pd.DataFrame:
    if isinstance(stock_basic, pd.DataFrame):
        return stock_basic.copy()
    return _load_stock_basic(stock_basic)


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.DataFrame()


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: Sequence[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            clean = dict(row)
            if isinstance(clean.get("blockers"), list):
                clean["blockers"] = "|".join(str(item) for item in clean["blockers"])
            writer.writerow(clean)


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "asset_id", "market", "family", "factor_name", "factor_value"])


def _field(spec: Any, name: str) -> Any:
    if isinstance(spec, dict):
        return spec.get(name)
    return getattr(spec, name)


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


def _data_window(bars: pd.DataFrame, features: pd.DataFrame, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "bar_rows": int(len(bars)),
        "feature_rows": int(len(features)),
        "factor_rows": int(result.get("summary", {}).get("factor_rows", 0)),
        "label_rows": int(result.get("summary", {}).get("label_rows", 0)),
        "asset_count": int(bars["asset_id"].nunique()) if "asset_id" in bars else 0,
    }
