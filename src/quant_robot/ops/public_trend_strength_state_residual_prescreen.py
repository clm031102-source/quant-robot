from __future__ import annotations

from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from quant_robot.factors.public_rsrs import compute_public_rsrs_factors
from quant_robot.factors.public_technical import compute_public_technical_factors
from quant_robot.factors.public_trend_strength_state import (
    PUBLIC_TREND_STRENGTH_STATE_FACTOR_NAMES,
    compute_public_trend_strength_state_factors,
)
from quant_robot.factors.public_trend_volume import compute_public_trend_volume_factors
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
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
from quant_robot.ops.public_reference_multi_family_preregistration import SAFETY
from quant_robot.ops.public_reference_multi_family_prescreen import (
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


STAGE = "public_trend_strength_state_residual_prescreen"
ROUND219_SOURCE_REPORT = "docs/research/cn_stock_round219_family_rotation_public_trend_strength_state_2026-06-24.md"
NEXT_DIRECTION_WITH_LEADS = "round220_public_trend_strength_state_cost_capacity_preflight"
NEXT_DIRECTION_WITHOUT_LEADS = "round220_rotate_after_public_trend_strength_state_residual_prescreen_failure"
RESULT_COLUMNS = [
    "factor_name",
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
REFERENCE_FACTOR_NAMES = (
    "bollinger_reversal_20",
    "donchian_position_20",
    "rsrs_slope_18",
    "rsrs_zscore_18_60",
    "rsrs_reversal_18_60",
    "supertrend_volume_confirmed_10_3_20",
    "anti_supertrend_volume_confirmed_10_3_20",
    "smart_money_trend_20",
    "anti_smart_money_trend_20",
)


def build_public_trend_strength_state_residual_prescreen(
    *,
    bars_roots: Iterable[str | Path],
    stock_basic: str | Path | pd.DataFrame | None,
    candidate_factor_names: Sequence[str] = PUBLIC_TREND_STRENGTH_STATE_FACTOR_NAMES,
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
    bars = load_public_reference_multi_family_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    stock_basic_frame = _stock_basic_frame(stock_basic)
    features = build_public_trend_strength_state_bar_features(
        bars,
        horizons=tuple(horizons),
        execution_lag=execution_lag,
    )
    exposure_frame = build_public_trend_strength_state_exposure_frame(features, stock_basic_frame)
    factor_frame = build_public_trend_strength_state_factor_frame(
        bars,
        exposure_frame,
        candidate_factor_names=candidate_factor_names,
        min_signal_date_amount=min_signal_date_amount,
    )
    reference_frame = build_public_trend_strength_state_reference_frame(bars, exposure_frame)
    labels = build_public_trend_strength_state_labels(features, horizons=tuple(horizons))
    result = summarize_public_trend_strength_state_residual_prescreen(
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
    )
    result["bars_roots"] = [str(Path(root)) for root in bars_roots]
    result["stock_basic"] = str(stock_basic) if isinstance(stock_basic, (str, Path)) else None
    result["data_window"] = _data_window(bars, factor_frame, reference_frame, exposure_frame, labels)
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
        "portfolio_grid_blocked_before_residual_prescreen": True,
    }
    result["sampling_policy"] = {
        "sample_every_n_dates": sample_every_n_dates,
        "sampling_used_for_correlations_only": True,
        "raw_industry_residual_ic_use_all_dates": True,
    }
    result["markdown"] = render_public_trend_strength_state_residual_prescreen_markdown(result)
    return result


def summarize_public_trend_strength_state_residual_prescreen(
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
    high_corr_threshold: float = 0.85,
    high_mean_abs_corr_threshold: float = 0.70,
    moderate_corr_threshold: float = 0.70,
    moderate_mean_abs_corr_threshold: float = 0.50,
    high_exposure_corr_threshold: float = 0.85,
    high_exposure_mean_abs_corr_threshold: float = 0.60,
) -> dict[str, Any]:
    candidates = tuple(str(name) for name in candidate_factor_names)
    requested_horizons = tuple(int(horizon) for horizon in horizons)
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
        exposures_corr = _technical_exposure_correlations(
            sampled_lead_exposure,
            exposure_names=DEFAULT_EXPOSURE_COLUMNS,
            min_cross_section=min_cross_section,
            high_exposure_corr_threshold=high_exposure_corr_threshold,
            high_exposure_mean_abs_corr_threshold=high_exposure_mean_abs_corr_threshold,
        )
        for row in refs:
            reference_rows.append({"lead_factor_name": factor_name, **row})
        for row in exposures_corr:
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
                exposure_correlations=exposures_corr,
                min_industries=min_industries,
                min_assets_per_industry=min_assets_per_industry,
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
                    "reference_highly_redundant_count": int(
                        sum(row.get("redundancy_class") == "highly_redundant" for row in refs)
                    ),
                    "style_exposure_high_count": int(
                        sum(row.get("exposure_class") == "high_exposure" for row in exposures_corr)
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
        "generated_at": date.today().isoformat(),
        "source_context": {
            "source_audit": ROUND219_SOURCE_REPORT,
            "candidate_family": "public_trend_strength_state_residual",
            "portfolio_grid_blocked_at_this_stage": True,
            "public_reference_dedup_required": True,
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
        },
        "multiple_testing_policy": {
            "method": "all Round219 public trend-strength-state candidate x horizon tests counted before any promotion claim",
            "round219_candidate_count": len(candidates),
            "test_count": len(results),
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_grid_allowed_before_residual_prescreen": False,
            "requires_next_gate": "cost_capacity_walk_forward_after_residual_reference_gate",
            "reason": "Round219 residual prescreen is an IC/neutralization/reference-dedup gate only.",
        },
        "results": sorted(
            results,
            key=lambda row: (
                not row["residual_research_lead"],
                -abs(row["residual_mean_spearman_ic"]),
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
    result["markdown"] = render_public_trend_strength_state_residual_prescreen_markdown(result)
    return result


def build_public_trend_strength_state_bar_features(
    bars: pd.DataFrame,
    *,
    horizons: tuple[int, ...],
    execution_lag: int,
) -> pd.DataFrame:
    frame = _normalise_bars(bars)
    pieces = []
    for _, group in frame.groupby("asset_id", sort=False):
        group = group.copy()
        close = pd.to_numeric(group["adj_close"], errors="coerce")
        amount = pd.to_numeric(group["amount"], errors="coerce")
        returns = close.pct_change()
        piece = group[["date", "asset_id", "market", "amount"]].copy()
        piece["return_1d"] = returns
        piece["return_20"] = close.pct_change(20)
        piece["adv20_amount"] = amount.rolling(20, min_periods=5).mean()
        piece["amount_trend_20_60"] = amount.rolling(20, min_periods=5).mean() / _nonzero(
            amount.rolling(60, min_periods=20).mean()
        ) - 1.0
        piece["realized_vol_20"] = returns.rolling(20, min_periods=5).std(ddof=0)
        piece["log_adv20_amount"] = _safe_log(piece["adv20_amount"])
        piece["log_amount"] = _safe_log(piece["amount"])
        for horizon in horizons:
            entry = close.shift(-execution_lag)
            exit_ = close.shift(-(execution_lag + int(horizon)))
            piece[f"forward_return_{int(horizon)}"] = exit_ / entry - 1.0
        pieces.append(piece)
    return pd.concat(pieces, ignore_index=True).replace([float("inf"), float("-inf")], pd.NA) if pieces else pd.DataFrame()


def build_public_trend_strength_state_factor_frame(
    bars: pd.DataFrame,
    exposure_frame: pd.DataFrame,
    *,
    candidate_factor_names: Sequence[str],
    min_signal_date_amount: float,
) -> pd.DataFrame:
    factors = compute_public_trend_strength_state_factors(
        bars,
        factor_names=tuple(candidate_factor_names),
    )
    if factors.empty:
        return _empty_factor_frame()
    factors = _normalise_factor_frame(factors)
    exposure = _normalise_exposure_frame(exposure_frame)
    merged = factors.merge(
        exposure,
        on=["date", "asset_id", "market"],
        how="left",
        validate="many_to_one",
    )
    capacity_mask = (
        (merged["amount"] >= min_signal_date_amount)
        & (merged["adv20_amount"] >= min_signal_date_amount)
        & (merged["return_1d"].abs() <= 0.50)
    )
    merged["family"] = "public_trend_strength_state_residual"
    return (
        merged.loc[capacity_mask]
        .dropna(subset=["factor_value", "amount", "adv20_amount"])
        .sort_values(["factor_name", "date", "asset_id"])
        .reset_index(drop=True)
    )


def build_public_trend_strength_state_reference_frame(
    bars: pd.DataFrame,
    exposure_frame: pd.DataFrame,
) -> pd.DataFrame:
    references = []
    for builder, names in (
        (compute_public_technical_factors, ("bollinger_reversal_20", "donchian_position_20")),
        (compute_public_rsrs_factors, ("rsrs_slope_18", "rsrs_zscore_18_60", "rsrs_reversal_18_60")),
        (
            compute_public_trend_volume_factors,
            (
                "supertrend_volume_confirmed_10_3_20",
                "anti_supertrend_volume_confirmed_10_3_20",
                "smart_money_trend_20",
                "anti_smart_money_trend_20",
            ),
        ),
    ):
        frame = builder(bars, factor_names=names)
        if not frame.empty:
            references.append(_normalise_factor_frame(frame))
    if not references:
        return _empty_factor_frame()
    reference = pd.concat(references, ignore_index=True)
    meta = _normalise_exposure_frame(exposure_frame)[["date", "asset_id", "market", "amount", "adv20_amount"]]
    return (
        reference.merge(meta, on=["date", "asset_id", "market"], how="left", validate="many_to_one")
        .dropna(subset=["factor_value"])
        .sort_values(["factor_name", "date", "asset_id"])
        .reset_index(drop=True)
    )


def build_public_trend_strength_state_exposure_frame(
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


def build_public_trend_strength_state_labels(features: pd.DataFrame, *, horizons: tuple[int, ...]) -> pd.DataFrame:
    rows = []
    for horizon in horizons:
        column = f"forward_return_{int(horizon)}"
        if features.empty or column not in features:
            continue
        labels = features[["date", "asset_id", "market", column]].rename(columns={column: "forward_return"}).copy()
        labels["horizon"] = int(horizon)
        rows.append(labels.dropna(subset=["forward_return"]))
    return pd.concat(rows, ignore_index=True).reset_index(drop=True) if rows else _empty_label_frame()


def write_public_trend_strength_state_residual_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "public_trend_strength_state_residual_prescreen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "public_trend_strength_state_residual_prescreen.md").write_text(
        render_public_trend_strength_state_residual_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "public_trend_strength_state_residual_prescreen_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(output_path / "public_trend_strength_state_reference_correlations.csv", result.get("reference_correlations", []), ["lead_factor_name", *REFERENCE_CORRELATION_COLUMNS])
    _write_csv(output_path / "public_trend_strength_state_exposure_correlations.csv", result.get("exposure_correlations", []), ["lead_factor_name", *EXPOSURE_CORRELATION_COLUMNS])
    _write_csv(output_path / "public_trend_strength_state_raw_yearly_ic.csv", result.get("raw_yearly_ic", []), ["factor_name", *YEARLY_IC_COLUMNS])
    _write_csv(output_path / "public_trend_strength_state_industry_neutral_yearly_ic.csv", result.get("industry_neutral_yearly_ic", []), ["factor_name", *YEARLY_IC_COLUMNS])
    _write_csv(output_path / "public_trend_strength_state_residual_yearly_ic.csv", result.get("residual_yearly_ic", []), ["factor_name", *YEARLY_IC_COLUMNS])
    _write_csv(output_path / "public_trend_strength_state_raw_ic_observations.csv", result.get("raw_ic_observations", []), IC_OBSERVATION_COLUMNS)
    _write_csv(output_path / "public_trend_strength_state_industry_neutral_ic_observations.csv", result.get("industry_neutral_ic_observations", []), IC_OBSERVATION_COLUMNS)
    _write_csv(output_path / "public_trend_strength_state_residual_ic_observations.csv", result.get("residual_ic_observations", []), IC_OBSERVATION_COLUMNS)


def render_public_trend_strength_state_residual_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Public Trend-Strength State Residual Prescreen Round219",
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
        "| Factor | H | Raw IC | Neutral IC | Residual IC | Residual ICIR | Ref High | Exposure High | Lead | Blockers |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("results", []):
        lines.append(
            "| {factor} | {horizon} | {raw_ic:.4f} | {neutral_ic:.4f} | {resid_ic:.4f} | {resid_icir:.3f} | {ref_high} | {exp_high} | {lead} | {blockers} |".format(
                factor=row["factor_name"],
                horizon=row["horizon"],
                raw_ic=row["raw_mean_spearman_ic"],
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
            "- This is not a promotion or portfolio-construction stage.",
            "- Residual leads only earn the right to a later cost/capacity walk-forward preflight.",
            "- If zero residual leads survive, the public trend-strength-state family must rotate instead of tuning windows.",
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
    min_industries: int,
    min_assets_per_industry: int,
    min_industry_neutral_mean_ic: float,
    min_industry_neutral_icir: float,
    min_industry_neutral_positive_ic_rate: float,
    min_residual_mean_ic: float,
    min_residual_icir: float,
    min_residual_positive_ic_rate: float,
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
    return _dedupe(blockers)


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    if "volume" not in frame and "vol" in frame:
        frame["volume"] = frame["vol"]
    if "volume" not in frame:
        frame["volume"] = 0.0
    if "open" not in frame:
        frame["open"] = frame.get("adj_close", frame.get("close"))
    if "close" not in frame:
        frame["close"] = frame.get("adj_close")
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str)
    for column in ["open", "high", "low", "close", "adj_close", "volume", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return (
        frame[(frame["market"] == "CN") & (frame["adj_close"] > 0) & (frame["amount"] > 0)]
        .dropna(subset=["date", "asset_id", "market", "adj_close", "high", "low", "amount"])
        .drop_duplicates(["asset_id", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _normalise_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return _empty_factor_frame()
    normalised = frame.copy()
    normalised["date"] = pd.to_datetime(normalised["date"])
    normalised["asset_id"] = normalised["asset_id"].astype(str)
    normalised["market"] = normalised["market"].astype(str)
    normalised["factor_name"] = normalised["factor_name"].astype(str)
    normalised["factor_value"] = pd.to_numeric(normalised["factor_value"], errors="coerce")
    for column in ["amount", "adv20_amount", "log_adv20_amount", "log_amount", "realized_vol_20", "amount_trend_20_60", "return_20", "return_1d"]:
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
    for column in ["amount", "adv20_amount", "log_adv20_amount", "log_amount", "realized_vol_20", "amount_trend_20_60", "return_20", "return_1d"]:
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
    return pd.DataFrame(columns=["date", "asset_id", "market", "amount", "adv20_amount", "family", "factor_name", "factor_value"])


def _empty_label_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "asset_id", "market", "horizon", "forward_return"])


def _nonzero(values: pd.Series) -> pd.Series:
    return values.where(values.abs() > 1e-12)


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
