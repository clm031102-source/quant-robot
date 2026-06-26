from __future__ import annotations

from datetime import date
import csv
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    _sanitize,
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
from quant_robot.ops.public_tradeable_indicator_composite_preregistration import (
    ROUND as SOURCE_PREREGISTRATION_ROUND,
    SAFETY,
    SOURCE_EVIDENCE_STATUS,
    default_public_tradeable_indicator_composite_candidate_specs,
)
from quant_robot.ops.public_trend_strength_state_residual_prescreen import (
    build_public_trend_strength_state_reference_frame,
)


STAGE = "public_tradeable_indicator_composite_residual_prescreen"
ROUND = 265
SOURCE_PREREGISTRATION = "docs/research/cn_stock_round264_public_tradeable_indicator_composite_preregistration_2026-06-26.md"
NEXT_DIRECTION_WITH_LEADS = "round266_public_tradeable_indicator_composite_reference_dedup_walk_forward_preflight"
NEXT_DIRECTION_WITHOUT_LEADS = "round266_rotate_after_public_tradeable_indicator_composite_residual_prescreen_failure"
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
    "quantile_spread",
    "quantile_monotonicity",
    "avg_top_quantile_turnover",
    "twenty_fifteen_mean_spearman_ic",
    "twenty_fifteen_ic_observations",
    "twenty_fifteen_failure",
    "residual_yearly_failure_count",
    "reference_highly_redundant_count",
    "style_exposure_high_count",
    "residual_research_lead",
    "promotion_allowed",
    "portfolio_grid_allowed",
    "blockers",
]


def round264_candidate_names() -> tuple[str, ...]:
    return tuple(spec.factor_name for spec in default_public_tradeable_indicator_composite_candidate_specs())


def load_public_tradeable_indicator_composite_bars(
    bars_roots: Iterable[str | Path],
    *,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
) -> pd.DataFrame:
    start = pd.Timestamp(analysis_start_date)
    end = pd.Timestamp(analysis_end_date)
    files: list[Path] = []
    for root in bars_roots:
        bars_root = _resolve_bars_root(Path(root))
        files.extend(sorted(bars_root.rglob("*.parquet")))
        files.extend(sorted(bars_root.rglob("*.csv")))
    files = _filter_bar_files_by_date_window(files, start=start, end=None if include_final_holdout else end)
    frames = [
        _filter_bar_frame_to_date_window(
            _read_bars_file(file),
            start=start,
            end=None if include_final_holdout else end,
        )
        for file in files
    ]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        raise FileNotFoundError(f"No CN bar files found under: {', '.join(str(root) for root in bars_roots)}")
    bars = pd.concat(frames, ignore_index=True)
    bars = _normalise_bars(bars)
    if include_final_holdout:
        end = max(end, bars["date"].max())
    bars = bars[(bars["date"] >= start) & (bars["date"] <= end)]
    return (
        bars.drop_duplicates(["asset_id", "market", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def build_public_tradeable_indicator_composite_residual_prescreen(
    *,
    bars_roots: Iterable[str | Path],
    stock_basic: str | Path | pd.DataFrame | None,
    candidate_factor_names: Sequence[str] = round264_candidate_names(),
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
    min_quantile_spread: float = 0.0,
    min_quantile_monotonicity: float = 0.50,
    max_top_quantile_turnover: float = 0.90,
) -> dict[str, Any]:
    bars = load_public_tradeable_indicator_composite_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    stock_basic_frame = _stock_basic_frame(stock_basic)
    features = build_public_tradeable_indicator_composite_bar_features(
        bars,
        horizons=tuple(horizons),
        execution_lag=execution_lag,
    )
    exposure_frame = build_public_tradeable_indicator_composite_exposure_frame(features, stock_basic_frame)
    factor_frame = build_public_tradeable_indicator_composite_factor_frame(
        features,
        candidate_factor_names=candidate_factor_names,
        min_signal_date_amount=min_signal_date_amount,
    )
    reference_frame = build_public_trend_strength_state_reference_frame(
        bars,
        exposure_frame,
    )
    labels = build_public_tradeable_indicator_composite_labels(features, horizons=tuple(horizons))
    result = summarize_public_tradeable_indicator_composite_residual_prescreen(
        factor_frame,
        labels,
        reference_factor_frame=reference_frame,
        exposure_frame=exposure_frame,
        candidate_factor_names=candidate_factor_names,
        horizons=tuple(horizons),
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
        min_quantile_spread=min_quantile_spread,
        min_quantile_monotonicity=min_quantile_monotonicity,
        max_top_quantile_turnover=max_top_quantile_turnover,
    )
    result["bars_roots"] = [str(Path(root)) for root in bars_roots]
    result["stock_basic"] = str(stock_basic) if isinstance(stock_basic, (str, Path)) else None
    result["data_window"] = _data_window(bars, factor_frame, reference_frame, exposure_frame, labels)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "excluded_from_tuning_and_round265_prescreen",
    }
    result["capacity_policy"] = {
        "min_signal_date_amount": min_signal_date_amount,
        "adv20_amount_filter_enabled": True,
        "portfolio_grid_blocked_before_residual_prescreen": True,
    }
    result["sampling_policy"] = {
        "sample_every_n_dates": sample_every_n_dates,
        "sampling_used_for_reference_and_exposure_correlations_only": True,
        "raw_industry_residual_ic_use_all_dates": True,
    }
    result["markdown"] = render_public_tradeable_indicator_composite_residual_prescreen_markdown(result)
    return result


def summarize_public_tradeable_indicator_composite_residual_prescreen(
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    reference_factor_frame: pd.DataFrame | None,
    exposure_frame: pd.DataFrame | None,
    candidate_factor_names: Sequence[str],
    horizons: tuple[int, ...],
    sample_every_n_dates: int = 1,
    min_cross_section: int,
    min_ic_observations: int,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
    min_industry_neutral_mean_ic: float = 0.02,
    min_industry_neutral_icir: float = 0.20,
    min_industry_neutral_positive_ic_rate: float = 0.55,
    min_residual_mean_ic: float = 0.02,
    min_residual_icir: float = 0.20,
    min_residual_positive_ic_rate: float = 0.55,
    min_quantile_spread: float = 0.0,
    min_quantile_monotonicity: float = 0.50,
    max_top_quantile_turnover: float = 0.90,
    high_corr_threshold: float = 0.85,
    high_mean_abs_corr_threshold: float = 0.70,
    moderate_corr_threshold: float = 0.70,
    moderate_mean_abs_corr_threshold: float = 0.50,
    high_exposure_corr_threshold: float = 0.85,
    high_exposure_mean_abs_corr_threshold: float = 0.60,
) -> dict[str, Any]:
    candidates = tuple(str(name) for name in candidate_factor_names)
    requested_horizons = tuple(int(horizon) for horizon in horizons)
    specs_by_name = {spec.factor_name: spec for spec in default_public_tradeable_indicator_composite_candidate_specs()}
    factors = _normalise_factor_frame(factor_frame)
    reference = _normalise_factor_frame(reference_factor_frame if reference_factor_frame is not None else pd.DataFrame())
    exposures = _normalise_exposure_frame(exposure_frame if exposure_frame is not None else pd.DataFrame())
    label_frame = _normalise_labels(labels)
    results: list[dict[str, Any]] = []
    raw_ic_rows: list[dict[str, Any]] = []
    industry_ic_rows: list[dict[str, Any]] = []
    residual_ic_rows: list[dict[str, Any]] = []
    raw_yearly_rows: list[dict[str, Any]] = []
    industry_yearly_rows: list[dict[str, Any]] = []
    residual_yearly_rows: list[dict[str, Any]] = []
    reference_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []
    factor_rows = 0
    industry_rows = 0
    residual_rows = 0

    for factor_name in candidates:
        spec = specs_by_name.get(factor_name)
        family = spec.family if spec is not None else "public_tradeable_indicator_composite"
        lead = factors[factors["factor_name"] == factor_name].reset_index(drop=True)
        factor_rows += len(lead)
        lead_with_exposures = _merge_lead_exposures(lead, exposures)
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
        sampled_reference = _filter_dates(reference, sampled_residual["date"].unique()) if not sampled_residual.empty else reference
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
        sampled_lead_exposure = _sample_dates(lead_with_exposures, sample_every_n_dates=sample_every_n_dates)
        exposure_corr = _technical_exposure_correlations(
            sampled_lead_exposure,
            exposure_names=DEFAULT_EXPOSURE_COLUMNS,
            min_cross_section=min_cross_section,
            high_exposure_corr_threshold=high_exposure_corr_threshold,
            high_exposure_mean_abs_corr_threshold=high_exposure_mean_abs_corr_threshold,
        )
        for row in refs:
            reference_rows.append({"lead_factor_name": factor_name, **row})
        for row in exposure_corr:
            exposure_rows.append({"lead_factor_name": factor_name, **row})
        for horizon in requested_horizons:
            raw_obs = _lead_ic_observations(
                lead,
                label_frame,
                lead_factor_name=factor_name,
                horizon=horizon,
                min_cross_section=min_cross_section,
            )
            industry_obs = _lead_ic_observations(
                industry,
                label_frame,
                lead_factor_name=industry_factor_name,
                horizon=horizon,
                min_cross_section=min_cross_section,
            )
            residual_obs = _lead_ic_observations(
                residual,
                label_frame,
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
            quantile = _residual_quantile_summary(
                residual,
                label_frame,
                lead_factor_name=residual_factor_name,
                horizon=horizon,
                min_cross_section=min_cross_section,
                min_ic_observations=min_ic_observations,
            )
            twenty_fifteen = _twenty_fifteen_row(residual_yearly)
            blockers = _row_blockers(
                lead=lead,
                lead_with_exposures=lead_with_exposures,
                raw_summary=raw_summary,
                industry_summary=industry_summary,
                residual_summary=residual_summary,
                raw_yearly=raw_yearly,
                industry_yearly=industry_yearly,
                residual_yearly=residual_yearly,
                reference_correlations=refs,
                exposure_correlations=exposure_corr,
                quantile_summary=quantile,
                min_industries=min_industries,
                min_assets_per_industry=min_assets_per_industry,
                min_industry_neutral_mean_ic=min_industry_neutral_mean_ic,
                min_industry_neutral_icir=min_industry_neutral_icir,
                min_industry_neutral_positive_ic_rate=min_industry_neutral_positive_ic_rate,
                min_residual_mean_ic=min_residual_mean_ic,
                min_residual_icir=min_residual_icir,
                min_residual_positive_ic_rate=min_residual_positive_ic_rate,
                min_quantile_spread=min_quantile_spread,
                min_quantile_monotonicity=min_quantile_monotonicity,
                max_top_quantile_turnover=max_top_quantile_turnover,
            )
            residual_research_lead = not blockers
            results.append(
                {
                    "factor_name": factor_name,
                    "family": family,
                    "horizon": int(horizon),
                    "source_evidence_status": SOURCE_EVIDENCE_STATUS,
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
                    "quantile_spread": quantile["quantile_spread"],
                    "quantile_monotonicity": quantile["quantile_monotonicity"],
                    "avg_top_quantile_turnover": quantile["avg_top_quantile_turnover"],
                    "twenty_fifteen_mean_spearman_ic": twenty_fifteen["mean_spearman_ic"],
                    "twenty_fifteen_ic_observations": twenty_fifteen["ic_observations"],
                    "twenty_fifteen_failure": twenty_fifteen["failure"],
                    "residual_yearly_failure_count": int(sum(row.get("failure") for row in residual_yearly)),
                    "reference_highly_redundant_count": int(
                        sum(row.get("redundancy_class") == "highly_redundant" for row in refs)
                    ),
                    "style_exposure_high_count": int(
                        sum(row.get("exposure_class") == "high_exposure" for row in exposure_corr)
                    ),
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

    residual_lead_count = int(sum(row["residual_research_lead"] for row in results))
    next_direction = NEXT_DIRECTION_WITH_LEADS if residual_lead_count else NEXT_DIRECTION_WITHOUT_LEADS
    result: dict[str, Any] = {
        "stage": STAGE,
        "round": ROUND,
        "generated_at": date.today().isoformat(),
        "source_context": {
            "source_preregistration": SOURCE_PREREGISTRATION,
            "source_preregistration_round": SOURCE_PREREGISTRATION_ROUND,
            "candidate_family": "public_tradeable_indicator_composite",
            "portfolio_grid_blocked_at_this_stage": True,
            "public_reference_dedup_required": True,
            "public_indicators_are_hypotheses_not_profit_evidence": True,
        },
        "summary": {
            "passes": True,
            "candidate_count": len(candidates),
            "test_count": len(results),
            "factor_rows": int(factor_rows),
            "industry_neutral_rows": int(industry_rows),
            "residual_rows": int(residual_rows),
            "label_rows": int(len(label_frame)),
            "reference_factor_count": int(reference["factor_name"].nunique()) if not reference.empty else 0,
            "residual_research_lead_count": residual_lead_count,
            "promotion_allowed_candidates": 0,
            "portfolio_grid_allowed_candidates": 0,
            "portfolio_preflight_candidates": residual_lead_count,
            "next_direction": next_direction,
            "horizons": sorted(requested_horizons),
            "twenty_fifteen_diagnostic_count": int(
                sum(1 for row in results if int(row.get("twenty_fifteen_ic_observations", 0)) > 0)
            ),
        },
        "multiple_testing_policy": {
            "method": "all frozen Round264 public indicator composite candidate x horizon tests counted before any promotion claim",
            "round264_candidate_count": len(candidates),
            "test_count": len(results),
            "deflated_sharpe_or_reality_check_required_later": True,
        },
        "family_rotation_policy": {
            "current_family_id": "public_tradeable_indicator_composite",
            "current_family_round_count": 2,
            "max_rounds_before_review": 3,
            "rotate_if_zero_leads": residual_lead_count == 0,
            "next_direction_if_zero_leads": NEXT_DIRECTION_WITHOUT_LEADS,
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed_before_residual_prescreen": False,
            "requires_next_gate": "reference_dedup_walk_forward_cost_capacity_regime_preflight_after_residual_lead",
            "reason": "Round265 is a long-cycle residual IC, quantile-shape, turnover, 2015, and reference-overlap prescreen only.",
        },
        "results": sorted(
            results,
            key=lambda row: (
                not row["residual_research_lead"],
                -row["residual_mean_spearman_ic"],
                -row["quantile_spread"],
                row["factor_name"],
                row["horizon"],
            ),
        ),
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
    result["markdown"] = render_public_tradeable_indicator_composite_residual_prescreen_markdown(result)
    return result


def build_public_tradeable_indicator_composite_bar_features(
    bars: pd.DataFrame,
    *,
    horizons: tuple[int, ...],
    execution_lag: int,
) -> pd.DataFrame:
    frame = _normalise_bars(bars)
    pieces = []
    for _, group in frame.groupby("asset_id", sort=False):
        group = group.copy().reset_index(drop=True)
        close = pd.to_numeric(group["adj_close"], errors="coerce")
        open_ = pd.to_numeric(group["open"], errors="coerce")
        high = pd.to_numeric(group["high"], errors="coerce")
        low = pd.to_numeric(group["low"], errors="coerce")
        amount = pd.to_numeric(group["amount"], errors="coerce")
        returns = close.pct_change()
        amount_ma5 = amount.rolling(5, min_periods=3).mean()
        amount_ma20 = amount.rolling(20, min_periods=5).mean()
        amount_ma60 = amount.rolling(60, min_periods=20).mean()
        rolling_high20 = high.rolling(20, min_periods=5).max()
        rolling_low20 = low.rolling(20, min_periods=5).min()
        ma20 = close.rolling(20, min_periods=10).mean()
        std20 = close.rolling(20, min_periods=10).std(ddof=0)
        ema12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
        ema26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
        macd = ema12 - ema26
        macd_hist = macd - macd.ewm(span=9, adjust=False, min_periods=9).mean()
        atr10 = _average_true_range(high, low, close, 10)
        atr20 = _average_true_range(high, low, close, 20)
        rsi14 = _rsi(close, 14)
        frame_piece = group[["date", "asset_id", "market", "open", "high", "low", "close", "adj_close", "amount"]].copy()
        frame_piece["return_1d"] = returns
        frame_piece["return_5"] = close.pct_change(5)
        frame_piece["return_20"] = close.pct_change(20)
        frame_piece["skip5_momentum_20"] = close.shift(5).pct_change(20)
        frame_piece["adv20_amount"] = amount_ma20
        frame_piece["amount_trend_5_20"] = amount_ma5 / _nonzero(amount_ma20) - 1.0
        frame_piece["amount_trend_20_60"] = amount_ma20 / _nonzero(amount_ma60) - 1.0
        frame_piece["realized_vol_20"] = returns.rolling(20, min_periods=5).std(ddof=0)
        frame_piece["downside_vol_20"] = returns.clip(upper=0.0).rolling(20, min_periods=5).std(ddof=0)
        frame_piece["log_adv20_amount"] = _safe_log(frame_piece["adv20_amount"])
        frame_piece["log_amount"] = _safe_log(frame_piece["amount"])
        frame_piece["mfi_reversal_14"] = 100.0 - _money_flow_index(high, low, close, amount, 14)
        frame_piece["cmf_20"] = _chaikin_money_flow(high, low, close, amount, 20)
        frame_piece["obv_absorption_20"] = _obv_absorption(close, amount, 20)
        frame_piece["atr_ratio_20"] = atr20 / _nonzero(close)
        frame_piece["supertrend_distance_reversal_10_3"] = -(
            (close - close.rolling(10, min_periods=5).mean()) / _nonzero(3.0 * atr10)
        )
        frame_piece["bollinger_bandwidth_20"] = 4.0 * std20 / _nonzero(ma20)
        frame_piece["donchian_position_20"] = (close - rolling_low20) / _nonzero(rolling_high20 - rolling_low20)
        frame_piece["return_efficiency_20"] = frame_piece["return_20"] / _nonzero(
            returns.abs().rolling(20, min_periods=5).sum()
        )
        frame_piece["adx_trend_strength_14"] = _adx(high, low, close, 14)
        frame_piece["macd_hist_z_26"] = (macd_hist - macd_hist.rolling(26, min_periods=10).mean()) / _nonzero(
            macd_hist.rolling(26, min_periods=10).std(ddof=0)
        )
        frame_piece["rsi_midline_reclaim_14"] = (rsi14 - 50.0) - (rsi14 - 70.0).clip(lower=0.0)
        for horizon in horizons:
            entry = close.shift(-execution_lag)
            exit_ = close.shift(-(execution_lag + int(horizon)))
            frame_piece[f"forward_return_{int(horizon)}"] = exit_ / entry - 1.0
        pieces.append(frame_piece)
    if not pieces:
        return pd.DataFrame()
    features = pd.concat(pieces, ignore_index=True).replace([float("inf"), float("-inf")], pd.NA)
    return _add_public_tradeable_indicator_cross_sectional_features(features)


def build_public_tradeable_indicator_composite_factor_frame(
    features: pd.DataFrame,
    *,
    candidate_factor_names: Sequence[str],
    min_signal_date_amount: float,
) -> pd.DataFrame:
    if features.empty:
        return _empty_factor_frame()
    specs_by_name = {spec.factor_name: spec for spec in default_public_tradeable_indicator_composite_candidate_specs()}
    candidate_values = _candidate_value_series(features)
    capacity_mask = (
        (features["amount"] >= min_signal_date_amount)
        & (features["adv20_amount"] >= min_signal_date_amount)
        & (features["return_1d"].abs() <= 0.50)
    )
    rows: list[pd.DataFrame] = []
    for factor_name in candidate_factor_names:
        values = candidate_values.get(str(factor_name))
        spec = specs_by_name.get(str(factor_name))
        if values is None or spec is None:
            continue
        frame = features.loc[capacity_mask, ["date", "asset_id", "market", "amount", "adv20_amount"]].copy()
        frame["family"] = spec.family
        frame["factor_name"] = str(factor_name)
        frame["factor_value"] = values.loc[capacity_mask]
        frame = frame.dropna(subset=["factor_value", "amount", "adv20_amount"])
        rows.append(frame)
    if not rows:
        return _empty_factor_frame()
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def build_public_tradeable_indicator_composite_exposure_frame(
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
            "return_1d",
        ]
    ].copy()
    exposure = _merge_stock_basic_industry(exposure, stock_basic)
    return exposure.replace([float("inf"), float("-inf")], pd.NA).reset_index(drop=True)


def build_public_tradeable_indicator_composite_labels(features: pd.DataFrame, *, horizons: tuple[int, ...]) -> pd.DataFrame:
    rows = []
    for horizon in horizons:
        column = f"forward_return_{int(horizon)}"
        if features.empty or column not in features:
            continue
        labels = features[["date", "asset_id", "market", column]].rename(columns={column: "forward_return"}).copy()
        labels["horizon"] = int(horizon)
        rows.append(labels.dropna(subset=["forward_return"]))
    return pd.concat(rows, ignore_index=True).reset_index(drop=True) if rows else _empty_label_frame()


def write_public_tradeable_indicator_composite_residual_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "public_tradeable_indicator_composite_residual_prescreen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "public_tradeable_indicator_composite_residual_prescreen.md").write_text(
        render_public_tradeable_indicator_composite_residual_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "public_tradeable_indicator_composite_residual_prescreen_results.csv",
        result.get("results", []),
        RESULT_COLUMNS,
    )
    _write_csv(
        output_path / "public_tradeable_indicator_composite_reference_correlations.csv",
        result.get("reference_correlations", []),
        ["lead_factor_name", *REFERENCE_CORRELATION_COLUMNS],
    )
    _write_csv(
        output_path / "public_tradeable_indicator_composite_exposure_correlations.csv",
        result.get("exposure_correlations", []),
        ["lead_factor_name", *EXPOSURE_CORRELATION_COLUMNS],
    )
    _write_csv(
        output_path / "public_tradeable_indicator_composite_raw_yearly_ic.csv",
        result.get("raw_yearly_ic", []),
        ["factor_name", *YEARLY_IC_COLUMNS],
    )
    _write_csv(
        output_path / "public_tradeable_indicator_composite_industry_neutral_yearly_ic.csv",
        result.get("industry_neutral_yearly_ic", []),
        ["factor_name", *YEARLY_IC_COLUMNS],
    )
    _write_csv(
        output_path / "public_tradeable_indicator_composite_residual_yearly_ic.csv",
        result.get("residual_yearly_ic", []),
        ["factor_name", *YEARLY_IC_COLUMNS],
    )
    _write_csv(
        output_path / "public_tradeable_indicator_composite_raw_ic_observations.csv",
        result.get("raw_ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )
    _write_csv(
        output_path / "public_tradeable_indicator_composite_industry_neutral_ic_observations.csv",
        result.get("industry_neutral_ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )
    _write_csv(
        output_path / "public_tradeable_indicator_composite_residual_ic_observations.csv",
        result.get("residual_ic_observations", []),
        IC_OBSERVATION_COLUMNS,
    )


def render_public_tradeable_indicator_composite_residual_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Public Tradeable Indicator Composite Residual Prescreen Round265",
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
        f"- 2015 diagnostics with data: {summary.get('twenty_fifteen_diagnostic_count', 0)}",
        f"- Next direction: {summary.get('next_direction', NEXT_DIRECTION_WITHOUT_LEADS)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Results",
        "",
        "| Factor | Family | H | Raw IC | Neutral IC | Residual IC | Residual ICIR | Q5-Q1 | Mono | Turnover | 2015 IC | Ref High | Exposure High | Lead | Blockers |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("results", []):
        lines.append(
            "| {factor} | {family} | {horizon} | {raw_ic:.4f} | {neutral_ic:.4f} | {resid_ic:.4f} | {resid_icir:.3f} | {spread:.4f} | {mono:.3f} | {turnover:.1%} | {ic2015:.4f} | {ref_high} | {exp_high} | {lead} | {blockers} |".format(
                factor=row["factor_name"],
                family=row.get("family", ""),
                horizon=row["horizon"],
                raw_ic=row["raw_mean_spearman_ic"],
                neutral_ic=row["industry_neutral_mean_spearman_ic"],
                resid_ic=row["residual_mean_spearman_ic"],
                resid_icir=row["residual_icir"],
                spread=row["quantile_spread"],
                mono=row["quantile_monotonicity"],
                turnover=row["avg_top_quantile_turnover"],
                ic2015=row["twenty_fifteen_mean_spearman_ic"],
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
            "- This stage is not a Sharpe, total-return, win-rate, paper, or live-trading claim.",
            "- A residual lead only earns the next de-duplication and walk-forward preflight gate.",
            "- If zero residual leads survive, the family must rotate instead of tuning SuperTrend, OBV, RSI, MACD, or MFI parameters.",
            "- Final holdout data remains excluded.",
        ]
    )
    return "\n".join(lines) + "\n"


def _row_blockers(
    *,
    lead: pd.DataFrame,
    lead_with_exposures: pd.DataFrame,
    raw_summary: dict[str, Any],
    industry_summary: dict[str, Any],
    residual_summary: dict[str, Any],
    raw_yearly: list[dict[str, Any]],
    industry_yearly: list[dict[str, Any]],
    residual_yearly: list[dict[str, Any]],
    reference_correlations: list[dict[str, Any]],
    exposure_correlations: list[dict[str, Any]],
    quantile_summary: dict[str, Any],
    min_industries: int,
    min_assets_per_industry: int,
    min_industry_neutral_mean_ic: float,
    min_industry_neutral_icir: float,
    min_industry_neutral_positive_ic_rate: float,
    min_residual_mean_ic: float,
    min_residual_icir: float,
    min_residual_positive_ic_rate: float,
    min_quantile_spread: float,
    min_quantile_monotonicity: float,
    max_top_quantile_turnover: float,
) -> list[str]:
    blockers = []
    if lead.empty:
        blockers.append("factor_frame_empty")
    coverage = _industry_coverage(lead_with_exposures, min_assets_per_industry=min_assets_per_industry)
    if not raw_summary.get("minimum_observation_gate_passed", False):
        blockers.append("raw_ic_observations_below_threshold")
    if not coverage.get("industry_metadata_present", False):
        blockers.append("industry_metadata_missing")
    if int(coverage.get("median_industries", 0)) < min_industries:
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
    if not quantile_summary.get("minimum_observation_gate_passed", False):
        blockers.append("quantile_observations_below_threshold")
    if quantile_summary.get("quantile_spread", 0.0) < min_quantile_spread:
        blockers.append("quantile_spread_below_threshold")
    if quantile_summary.get("quantile_monotonicity", 0.0) < min_quantile_monotonicity:
        blockers.append("quantile_monotonicity_below_threshold")
    if quantile_summary.get("avg_top_quantile_turnover", 1.0) > max_top_quantile_turnover:
        blockers.append("top_quantile_turnover_too_high")
    if any(row.get("redundancy_class") == "highly_redundant" for row in reference_correlations):
        blockers.append("candidate_highly_redundant_with_public_technical_reference")
    if any(row.get("exposure_class") == "high_exposure" for row in exposure_correlations):
        blockers.append("candidate_high_size_liquidity_or_volatility_exposure")
    if any(row.get("failure") for row in raw_yearly):
        blockers.append("raw_yearly_ic_instability")
    if any(row.get("failure") for row in industry_yearly):
        blockers.append("industry_neutral_yearly_ic_instability")
    if any(row.get("failure") for row in residual_yearly):
        blockers.append("residual_yearly_ic_instability")
    if any(row.get("year") == 2015 and row.get("failure") for row in residual_yearly):
        blockers.append("twenty_fifteen_residual_ic_failure")
    return _dedupe(blockers)


def _residual_quantile_summary(
    residual: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    lead_factor_name: str,
    horizon: int,
    min_cross_section: int,
    min_ic_observations: int,
) -> dict[str, Any]:
    frame = residual[["date", "asset_id", "market", "factor_name", "factor_value"]].copy() if not residual.empty else pd.DataFrame()
    if frame.empty:
        return _empty_quantile_summary(lead_factor_name, horizon, 0)
    label = labels[labels["horizon"] == int(horizon)][["date", "asset_id", "market", "forward_return"]].copy()
    group = frame.merge(label, on=["date", "asset_id", "market"], how="inner", validate="many_to_one")
    quantile_returns: list[list[float]] = []
    top_sets: list[set[str]] = []
    observation_count = 0
    for _, date_frame in group.groupby("date", sort=True):
        date_frame = date_frame.dropna(subset=["factor_value", "forward_return"])
        if len(date_frame) < min_cross_section:
            continue
        quantiles = _quantile_labels(date_frame["factor_value"])
        if quantiles is None:
            continue
        group_means = []
        for quantile in range(5):
            group_means.append(float(date_frame.loc[quantiles == quantile, "forward_return"].mean()))
        quantile_returns.append(group_means)
        top_sets.append(set(date_frame.loc[quantiles == 4, "asset_id"].astype(str)))
        observation_count += 1
    if observation_count < min_ic_observations:
        return _empty_quantile_summary(lead_factor_name, horizon, observation_count)
    quantile_frame = pd.DataFrame(quantile_returns, columns=["q1", "q2", "q3", "q4", "q5"])
    means = quantile_frame.mean(axis=0)
    diffs = means.diff().dropna()
    return {
        "factor_name": lead_factor_name,
        "horizon": int(horizon),
        "quantile_observations": int(observation_count),
        "minimum_observation_gate_passed": True,
        "quantile_spread": float(means["q5"] - means["q1"]),
        "quantile_monotonicity": float((diffs > 0.0).mean()) if len(diffs) else 0.0,
        "avg_top_quantile_turnover": _average_top_quantile_turnover(top_sets),
    }


def _empty_quantile_summary(factor_name: str, horizon: int, observations: int) -> dict[str, Any]:
    return {
        "factor_name": factor_name,
        "horizon": int(horizon),
        "quantile_observations": int(observations),
        "minimum_observation_gate_passed": False,
        "quantile_spread": 0.0,
        "quantile_monotonicity": 0.0,
        "avg_top_quantile_turnover": 1.0,
    }


def _twenty_fifteen_row(yearly_rows: list[dict[str, Any]]) -> dict[str, Any]:
    for row in yearly_rows:
        if int(row.get("year", 0)) == 2015:
            return {
                "ic_observations": int(row.get("ic_observations", 0)),
                "mean_spearman_ic": float(row.get("mean_spearman_ic", 0.0)),
                "positive_ic_rate": float(row.get("positive_ic_rate", 0.0)),
                "failure": bool(row.get("failure", False)),
            }
    return {"ic_observations": 0, "mean_spearman_ic": 0.0, "positive_ic_rate": 0.0, "failure": True}


def _candidate_value_series(features: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        "mfi_cmf_exhaustion_reversal_liquid_14_20": (
            0.35 * features["z_mfi_reversal_14"]
            - 0.30 * features["z_cmf_20"]
            - 0.20 * features["z_return_5"]
            + 0.15 * features["z_log_adv20"]
        ),
        "supertrend_pullback_absorption_quality_10_3_20": (
            0.35 * features["z_supertrend_distance_reversal_10_3"]
            + 0.30 * features["z_obv_absorption_20"]
            - 0.20 * features["z_atr_ratio_20"]
            + 0.15 * features["z_log_adv20"]
        ),
        "obv_cmf_absorption_reversal_quality_20": (
            0.40 * features["z_obv_absorption_20"]
            - 0.30 * features["z_cmf_20"]
            - 0.20 * features["z_downside_vol_20"]
            + 0.10 * features["z_log_adv20"]
        ),
        "volume_dryup_pullback_liquid_reversal_5_20": (
            -0.40 * features["z_return_5"]
            - 0.30 * features["z_amount_trend_5_20"]
            - 0.20 * features["z_realized_vol_20"]
            + 0.10 * features["z_log_adv20"]
        ),
        "atr_bandwidth_compression_breakout_quality_20": (
            -0.35 * features["z_atr_ratio_20"]
            - 0.30 * features["z_bollinger_bandwidth_20"]
            + 0.20 * features["z_return_efficiency_20"]
            + 0.15 * features["z_log_adv20"]
        ),
        "donchian_atr_compression_breakout_efficiency_20": (
            0.35 * features["z_donchian_position_20"]
            - 0.30 * features["z_atr_ratio_20"]
            + 0.20 * features["z_return_efficiency_20"]
            + 0.15 * features["z_log_adv20"]
        ),
        "adx_efficiency_momentum_quality_14_20": (
            0.35 * features["z_adx_trend_strength_14"]
            + 0.30 * features["z_return_efficiency_20"]
            + 0.20 * features["z_skip5_momentum_20"]
            - 0.15 * features["z_realized_vol_20"]
        ),
        "macd_rsi_momentum_exhaustion_quality_14_26": (
            0.30 * features["z_macd_hist_z_26"]
            + 0.30 * features["z_rsi_midline_reclaim_14"]
            + 0.25 * features["z_return_efficiency_20"]
            + 0.15 * features["z_log_adv20"]
        ),
    }


def _add_public_tradeable_indicator_cross_sectional_features(features: pd.DataFrame) -> pd.DataFrame:
    frame = features.copy()
    z_inputs = {
        "z_mfi_reversal_14": frame["mfi_reversal_14"],
        "z_cmf_20": frame["cmf_20"],
        "z_return_5": frame["return_5"],
        "z_log_adv20": frame["log_adv20_amount"],
        "z_supertrend_distance_reversal_10_3": frame["supertrend_distance_reversal_10_3"],
        "z_obv_absorption_20": frame["obv_absorption_20"],
        "z_atr_ratio_20": frame["atr_ratio_20"],
        "z_downside_vol_20": frame["downside_vol_20"],
        "z_amount_trend_5_20": frame["amount_trend_5_20"],
        "z_realized_vol_20": frame["realized_vol_20"],
        "z_bollinger_bandwidth_20": frame["bollinger_bandwidth_20"],
        "z_return_efficiency_20": frame["return_efficiency_20"],
        "z_donchian_position_20": frame["donchian_position_20"],
        "z_adx_trend_strength_14": frame["adx_trend_strength_14"],
        "z_skip5_momentum_20": frame["skip5_momentum_20"],
        "z_macd_hist_z_26": frame["macd_hist_z_26"],
        "z_rsi_midline_reclaim_14": frame["rsi_midline_reclaim_14"],
    }
    for column, series in z_inputs.items():
        frame[column] = _cs_zscore(frame, series)
    return frame


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "high", "low", "adj_close", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing required columns: {', '.join(missing)}")
    frame = bars.copy()
    if "open" not in frame:
        frame["open"] = frame["adj_close"]
    if "close" not in frame:
        frame["close"] = frame["adj_close"]
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str)
    for column in ["open", "high", "low", "close", "adj_close", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return (
        frame[(frame["market"] == "CN") & (frame["adj_close"] > 0) & (frame["high"] > 0) & (frame["low"] > 0) & (frame["amount"] > 0)]
        .dropna(subset=["date", "asset_id", "market", "adj_close", "high", "low", "amount"])
        .drop_duplicates(["asset_id", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _resolve_bars_root(root_path: Path) -> Path:
    if (root_path / "processed" / "bars").exists():
        return root_path / "processed" / "bars"
    if (root_path / "bars").exists():
        return root_path / "bars"
    return root_path


def _filter_bar_files_by_date_window(files: list[Path], *, start: pd.Timestamp, end: pd.Timestamp | None) -> list[Path]:
    output: list[Path] = []
    start_year = int(start.year)
    end_year = int(end.year) if end is not None else None
    for file in files:
        year = _year_from_partition_path(file)
        if year is None:
            output.append(file)
            continue
        if year < start_year:
            continue
        if end_year is not None and year > end_year:
            continue
        output.append(file)
    return output


def _year_from_partition_path(file: Path) -> int | None:
    match = re.search(r"(?:^|[\\/])year=(\d{4})(?:[\\/]|$)", str(file))
    return int(match.group(1)) if match else None


def _filter_bar_frame_to_date_window(
    frame: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp | None,
) -> pd.DataFrame:
    if frame.empty or "date" not in frame:
        return frame
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    mask = output["date"] >= start
    if end is not None:
        mask &= output["date"] <= end
    return output.loc[mask].reset_index(drop=True)


def _read_bars_file(file: Path) -> pd.DataFrame:
    columns = [
        "date",
        "asset_id",
        "symbol",
        "market",
        "exchange",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "amount",
        "vwap",
    ]
    if file.suffix == ".parquet":
        try:
            return pd.read_parquet(file, columns=columns)
        except Exception:
            frame = pd.read_parquet(file)
            return frame[[column for column in columns if column in frame.columns]]
    frame = pd.read_csv(file)
    return frame[[column for column in columns if column in frame.columns]]


def _normalise_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return _empty_factor_frame()
    normalised = frame.copy()
    normalised["date"] = pd.to_datetime(normalised["date"])
    normalised["asset_id"] = normalised["asset_id"].astype(str)
    normalised["market"] = normalised["market"].astype(str)
    normalised["factor_name"] = normalised["factor_name"].astype(str)
    normalised["factor_value"] = pd.to_numeric(normalised["factor_value"], errors="coerce")
    for column in [
        "amount",
        "adv20_amount",
        "log_adv20_amount",
        "log_amount",
        "realized_vol_20",
        "amount_trend_20_60",
        "return_20",
        "return_1d",
    ]:
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
    for column in [
        "amount",
        "adv20_amount",
        "log_adv20_amount",
        "log_amount",
        "realized_vol_20",
        "amount_trend_20_60",
        "return_20",
        "return_1d",
    ]:
        if column in normalised:
            normalised[column] = pd.to_numeric(normalised[column], errors="coerce")
    if "industry" in normalised:
        normalised["industry"] = normalised["industry"].astype(str)
    return normalised.drop_duplicates(["date", "asset_id", "market"], keep="last").reset_index(drop=True)


def _normalise_labels(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return _empty_label_frame()
    normalised = frame.copy()
    normalised["date"] = pd.to_datetime(normalised["date"])
    normalised["asset_id"] = normalised["asset_id"].astype(str)
    normalised["market"] = normalised["market"].astype(str)
    normalised["horizon"] = normalised["horizon"].astype(int)
    normalised["forward_return"] = pd.to_numeric(normalised["forward_return"], errors="coerce")
    return normalised.dropna(subset=["forward_return"]).reset_index(drop=True)


def _money_flow_index(high: pd.Series, low: pd.Series, close: pd.Series, amount: pd.Series, window: int) -> pd.Series:
    typical = (high + low + close) / 3.0
    flow = typical * amount
    direction = typical.diff()
    positive = flow.where(direction > 0.0, 0.0).rolling(window, min_periods=max(5, window // 2)).sum()
    negative = flow.where(direction < 0.0, 0.0).rolling(window, min_periods=max(5, window // 2)).sum()
    ratio = positive / _nonzero(negative)
    return 100.0 - 100.0 / (1.0 + ratio)


def _chaikin_money_flow(high: pd.Series, low: pd.Series, close: pd.Series, amount: pd.Series, window: int) -> pd.Series:
    multiplier = ((close - low) - (high - close)) / _nonzero(high - low)
    flow = multiplier * amount
    return flow.rolling(window, min_periods=max(5, window // 2)).sum() / _nonzero(
        amount.rolling(window, min_periods=max(5, window // 2)).sum()
    )


def _obv_absorption(close: pd.Series, amount: pd.Series, window: int) -> pd.Series:
    returns = close.pct_change()
    signed_amount = np.sign(returns.fillna(0.0)) * amount
    obv_slope = signed_amount.rolling(window, min_periods=max(5, window // 2)).sum() / _nonzero(
        amount.rolling(window, min_periods=max(5, window // 2)).sum()
    )
    pullback = -close.pct_change(5)
    return obv_slope + pullback


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0.0), up_move, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0.0), down_move, 0.0), index=high.index)
    true_range_sum = _true_range(high, low, close).rolling(window, min_periods=max(5, window // 2)).sum()
    plus_di = 100.0 * plus_dm.rolling(window, min_periods=max(5, window // 2)).sum() / _nonzero(true_range_sum)
    minus_di = 100.0 * minus_dm.rolling(window, min_periods=max(5, window // 2)).sum() / _nonzero(true_range_sum)
    dx = 100.0 * (plus_di - minus_di).abs() / _nonzero(plus_di + minus_di)
    return dx.rolling(window, min_periods=max(5, window // 2)).mean()


def _average_true_range(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    return _true_range(high, low, close).rolling(window, min_periods=max(5, window // 2)).mean()


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    previous_close = close.shift(1)
    return pd.concat([high - low, (high - previous_close).abs(), (low - previous_close).abs()], axis=1).max(axis=1)


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0).rolling(window, min_periods=max(5, window // 2)).mean()
    loss = (-delta.clip(upper=0.0)).rolling(window, min_periods=max(5, window // 2)).mean()
    rs = gain / _nonzero(loss)
    return 100.0 - 100.0 / (1.0 + rs)


def _quantile_labels(values: pd.Series) -> pd.Series | None:
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.nunique(dropna=True) < 5:
        return None
    try:
        return pd.qcut(numeric.rank(method="first"), q=5, labels=False, duplicates="drop")
    except ValueError:
        return None


def _average_top_quantile_turnover(top_sets: list[set[str]]) -> float:
    turnovers = []
    for previous, current in zip(top_sets, top_sets[1:]):
        if not previous:
            continue
        turnovers.append(1.0 - len(previous.intersection(current)) / len(previous))
    if not turnovers:
        return 1.0
    return float(pd.Series(turnovers).mean())


def _cs_zscore(frame: pd.DataFrame, series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    grouped = values.groupby([frame["date"], frame["market"]], sort=False)
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return ((values - mean) / std.where(std > 1e-12)).replace([np.inf, -np.inf], np.nan)


def _stock_basic_frame(value: str | Path | pd.DataFrame | None) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    return _load_stock_basic(value) if value is not None else pd.DataFrame()


def _data_window(
    bars: pd.DataFrame,
    factor_frame: pd.DataFrame,
    reference_frame: pd.DataFrame,
    exposure_frame: pd.DataFrame,
    labels: pd.DataFrame,
) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "bar_rows": int(len(bars)),
        "asset_count": int(bars["asset_id"].nunique()) if "asset_id" in bars else 0,
        "factor_rows": int(len(factor_frame)),
        "reference_factor_rows": int(len(reference_frame)),
        "exposure_rows": int(len(exposure_frame)),
        "label_rows": int(len(labels)),
    }


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["date", "asset_id", "market", "amount", "adv20_amount", "family", "factor_name", "factor_value"]
    )


def _empty_label_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "asset_id", "market", "horizon", "forward_return"])


def _nonzero(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.where(numeric.abs() > 1e-12)


def _safe_log(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return np.log(numeric.where(numeric > 0.0))


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()


def _dedupe(values: list[str]) -> list[str]:
    output: list[str] = []
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
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    return value
