from __future__ import annotations

from dataclasses import asdict
from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_preregistration import DEFAULT_CAPACITY_FILTERS
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
    load_capacity_safe_bars,
)
from quant_robot.ops.event_factor_pit_ic_prescreen import summarize_event_factor_pit_ic_prescreen
from quant_robot.ops.lottery_extreme_upside_reversal_preregistration import (
    SAFETY,
    default_lottery_extreme_upside_candidate_specs,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "lottery_extreme_upside_reversal_prescreen"
NEXT_DIRECTION_WITH_LEADS = "round151_lottery_reference_dedup_before_portfolio_conversion"
NEXT_DIRECTION_WITHOUT_LEADS = "round151_rotate_from_lottery_family_after_ic_neutral_failure"
RESULT_COLUMNS = [
    "factor_name",
    "horizon",
    "ic_observations",
    "mean_spearman_ic",
    "icir",
    "ic_t_stat",
    "ic_p_value",
    "fdr_significant",
    "ic_positive_rate",
    "quantile_spread",
    "quantile_monotonicity",
    "industry_neutral_observations",
    "mean_industry_neutral_rank_ic",
    "industry_neutral_rank_ic_t_stat",
    "industry_neutral_retention_ratio",
    "size_neutral_observations",
    "mean_size_neutral_rank_ic",
    "size_neutral_rank_ic_t_stat",
    "size_neutral_retention_ratio",
    "max_reference_name",
    "max_reference_corr_abs",
    "reference_dedup_pass",
    "research_lead",
    "promotion_allowed",
    "blockers",
]


def build_lottery_extreme_upside_reversal_prescreen(
    *,
    bars: pd.DataFrame | None = None,
    bars_roots: Iterable[str | Path] | None = None,
    stock_basic: pd.DataFrame,
    candidate_specs: Sequence[Any] | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_industries: int = 2,
    min_assets_per_industry: int = 5,
    min_neutral_rank_ic: float = 0.01,
    min_neutral_ic_t_stat: float = 2.0,
    min_neutral_retention: float = 0.50,
    min_ic_years: int = 5,
    min_yearly_positive_ic_year_rate: float = 0.60,
    max_reference_corr_abs: float = 0.85,
    min_signal_date_amount: float = DEFAULT_CAPACITY_FILTERS["min_signal_date_amount"],
) -> dict[str, Any]:
    if bars is None:
        if bars_roots is None:
            raise ValueError("Either bars or bars_roots must be provided")
        clean_bars = load_capacity_safe_bars(
            bars_roots,
            analysis_start_date=analysis_start_date,
            analysis_end_date=analysis_end_date,
            include_final_holdout=include_final_holdout,
        )
    else:
        clean_bars = _filter_date_window(
            _normalise_bars(bars),
            start_date=analysis_start_date,
            end_date=analysis_end_date,
            include_final_holdout=include_final_holdout,
        )
    specs = tuple(candidate_specs or default_lottery_extreme_upside_candidate_specs())
    factor_frame = compute_lottery_extreme_upside_reversal_factors(
        clean_bars,
        candidate_specs=specs,
        min_signal_date_amount=min_signal_date_amount,
    )
    reference_frame = compute_lottery_public_reference_factors(
        clean_bars,
        min_signal_date_amount=min_signal_date_amount,
    )
    labels = make_forward_returns(
        clean_bars[["date", "asset_id", "market", "adj_close"]],
        horizons=horizons,
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_lottery_extreme_upside_reversal_prescreen(
        factor_frame,
        labels,
        stock_basic,
        reference_frame=reference_frame,
        expected_candidate_count=len(specs),
        candidate_specs=specs,
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
        min_neutral_rank_ic=min_neutral_rank_ic,
        min_neutral_ic_t_stat=min_neutral_ic_t_stat,
        min_neutral_retention=min_neutral_retention,
        min_ic_years=min_ic_years,
        min_yearly_positive_ic_year_rate=min_yearly_positive_ic_year_rate,
        max_reference_corr_abs=max_reference_corr_abs,
    )
    result["data_window"] = _data_window(clean_bars, factor_frame, labels)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "blocked_until_ic_neutral_reference_dedup_oos_clearance",
    }
    result["capacity_policy"] = {
        "min_signal_date_amount": min_signal_date_amount,
        "adv20_amount_filter_enabled": True,
        "extreme_return_filter_abs_return_lte": 0.50,
        "portfolio_backtest_allowed_before_prescreen_lead": False,
    }
    result["markdown"] = render_lottery_extreme_upside_reversal_prescreen_markdown(result)
    return result


def compute_lottery_extreme_upside_reversal_factors(
    bars: pd.DataFrame,
    *,
    candidate_specs: Sequence[Any] | None = None,
    min_signal_date_amount: float = DEFAULT_CAPACITY_FILTERS["min_signal_date_amount"],
) -> pd.DataFrame:
    specs = tuple(candidate_specs or default_lottery_extreme_upside_candidate_specs())
    features = _add_cross_sectional_features(_feature_frame(bars))
    if features.empty:
        return _empty_factor_frame()
    values = {
        "lottery_max_return_reversal_20": features["z_neg_max_return_20"] + 0.20 * features["z_log_adv20"],
        "lottery_limit_chase_exhaustion_20": (
            features["z_neg_limit_chase_exhaustion_20"] + 0.20 * features["z_log_adv20"]
        ),
        "lottery_upside_tail_asymmetry_reversal_60": (
            features["z_neg_upside_tail_asymmetry_60"] + 0.15 * features["z_log_adv20"]
        ),
        "lottery_climax_volume_reversal_20": features["z_neg_climax_volume_20"] + 0.20 * features["z_log_adv20"],
        "lottery_upper_shadow_reversal_20": features["z_neg_upper_shadow_positive_20"] + 0.20 * features["z_log_adv20"],
        "lottery_gapless_max_reversal_20": features["z_neg_gapless_max_20"] + 0.20 * features["z_log_adv20"],
    }
    allowed = {str(spec.factor_name) for spec in specs}
    rows: list[pd.DataFrame] = []
    base_columns = ["date", "asset_id", "market", "amount", "adv20_amount", "log_adv20"]
    capacity_mask = _capacity_mask(features, min_signal_date_amount=min_signal_date_amount)
    for factor_name, series in values.items():
        if factor_name not in allowed:
            continue
        frame = features.loc[capacity_mask, base_columns].copy()
        frame["factor_name"] = factor_name
        frame["factor_value"] = series.loc[capacity_mask]
        frame = frame.dropna(subset=["factor_value", "amount", "adv20_amount", "log_adv20"])
        rows.append(frame)
    if not rows:
        return _empty_factor_frame()
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def compute_lottery_public_reference_factors(
    bars: pd.DataFrame,
    *,
    min_signal_date_amount: float = DEFAULT_CAPACITY_FILTERS["min_signal_date_amount"],
) -> pd.DataFrame:
    features = _add_cross_sectional_features(_feature_frame(bars))
    if features.empty:
        return _empty_reference_frame()
    values = {
        "public_short_reversal_5": features["z_reversal_5"],
        "public_lowvol_20": features["z_neg_realized_vol_20"],
        "public_upside_tail_60": features["z_neg_upside_tail_asymmetry_60"],
        "public_volume_climax_20": features["z_neg_climax_volume_20"],
    }
    rows: list[pd.DataFrame] = []
    capacity_mask = _capacity_mask(features, min_signal_date_amount=min_signal_date_amount)
    for reference_name, series in values.items():
        frame = features.loc[capacity_mask, ["date", "asset_id", "market"]].copy()
        frame["reference_name"] = reference_name
        frame["reference_value"] = series.loc[capacity_mask]
        rows.append(frame.dropna(subset=["reference_value"]))
    if not rows:
        return _empty_reference_frame()
    return pd.concat(rows, ignore_index=True).sort_values(["reference_name", "date", "asset_id"]).reset_index(drop=True)


def summarize_lottery_extreme_upside_reversal_prescreen(
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    stock_basic: pd.DataFrame,
    *,
    reference_frame: pd.DataFrame | None = None,
    expected_candidate_count: int | None = None,
    candidate_specs: Sequence[Any] | None = None,
    horizons: tuple[int, ...] | None = None,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_industries: int = 2,
    min_assets_per_industry: int = 5,
    min_neutral_rank_ic: float = 0.01,
    min_neutral_ic_t_stat: float = 2.0,
    min_neutral_retention: float = 0.50,
    min_ic_years: int = 5,
    min_yearly_positive_ic_year_rate: float = 0.60,
    max_reference_corr_abs: float = 0.85,
    alpha: float = 0.05,
    min_abs_ic: float = 0.02,
    min_abs_icir: float = 0.30,
    min_positive_ic_rate: float = 0.55,
) -> dict[str, Any]:
    specs = tuple(candidate_specs or default_lottery_extreme_upside_candidate_specs())
    base = summarize_event_factor_pit_ic_prescreen(
        factor_frame,
        labels,
        stock_basic,
        expected_candidate_count=expected_candidate_count,
        candidate_specs=specs,
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
        min_neutral_rank_ic=min_neutral_rank_ic,
        min_neutral_ic_t_stat=min_neutral_ic_t_stat,
        min_neutral_retention=min_neutral_retention,
        min_ic_years=min_ic_years,
        min_yearly_positive_ic_year_rate=min_yearly_positive_ic_year_rate,
        alpha=alpha,
        min_abs_ic=min_abs_ic,
        min_abs_icir=min_abs_icir,
        min_positive_ic_rate=min_positive_ic_rate,
    )
    reference_rows, reference_observations = _reference_correlation_rows(
        factor_frame,
        reference_frame if reference_frame is not None else _empty_reference_frame(),
        min_cross_section=min_cross_section,
    )
    reference_by_factor = {row["factor_name"]: row for row in reference_rows}
    for row in base.get("results", []):
        reference = reference_by_factor.get(str(row.get("factor_name")), _empty_reference_summary(str(row.get("factor_name"))))
        row.update(reference)
        blockers = list(row.get("blockers", []))
        if int(row.get("reference_observations", 0)) <= 0:
            blockers.append("public_reference_observations_missing")
        if float(row.get("max_reference_corr_abs", 1.0)) >= max_reference_corr_abs:
            blockers.append("public_reference_redundancy_too_high")
        row["reference_dedup_pass"] = bool(
            int(row.get("reference_observations", 0)) > 0
            and float(row.get("max_reference_corr_abs", 1.0)) < max_reference_corr_abs
        )
        row["research_lead"] = bool(row.get("research_lead") and row["reference_dedup_pass"])
        row["promotion_allowed"] = False
        row["blockers"] = _dedupe(blockers)
    base["results"] = sorted(base.get("results", []), key=lambda item: (not item["research_lead"], -abs(item["mean_spearman_ic"])))
    summary = base["summary"]
    summary["research_lead_count"] = sum(1 for row in base["results"] if row["research_lead"])
    summary["reference_dedup_pass_count"] = sum(1 for row in base["results"] if row.get("reference_dedup_pass"))
    summary["reference_correlation_observation_rows"] = len(reference_observations)
    summary["promotion_allowed_candidates"] = 0
    summary["next_direction"] = NEXT_DIRECTION_WITH_LEADS if summary["research_lead_count"] else NEXT_DIRECTION_WITHOUT_LEADS
    base.update(
        {
            "stage": STAGE,
            "candidate_specs": [_spec_payload(spec) for spec in specs],
            "reference_dedup_policy": {
                "max_reference_corr_abs": max_reference_corr_abs,
                "reference_names": sorted(set(reference_frame["reference_name"].astype(str))) if reference_frame is not None and not reference_frame.empty else [],
                "method": "daily cross-sectional Spearman against public reversal, low-volatility, upside-tail, and volume-climax proxies",
            },
            "promotion_policy": {
                "promotion_allowed": False,
                "portfolio_backtest_allowed_before_prescreen": False,
                "requires_next_gate": "lottery_reference_dedup_before_portfolio_conversion",
                "reason": "This is a long-cycle IC, neutralization, and public-reference de-dup prescreen; portfolio grids remain blocked until walk-forward, cost/capacity, regime, and final-holdout gates clear.",
            },
            "multiple_testing_policy": {
                "alpha": alpha,
                "method": "Bonferroni and Benjamini-Hochberg FDR across lottery factor x horizon tests",
            },
            "reference_observations": reference_observations,
            "live_boundary_allowed": False,
            "safety": SAFETY,
        }
    )
    base["markdown"] = render_lottery_extreme_upside_reversal_prescreen_markdown(base)
    return base


def write_lottery_extreme_upside_reversal_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "lottery_extreme_upside_reversal_prescreen.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "lottery_extreme_upside_reversal_prescreen.md").write_text(
        render_lottery_extreme_upside_reversal_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "lottery_extreme_upside_reversal_prescreen_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(
        output_path / "lottery_extreme_upside_reversal_prescreen_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )
    _write_csv(
        output_path / "lottery_extreme_upside_reversal_prescreen_neutral_observations.csv",
        result.get("neutral_observations", []),
        ["factor_name", "horizon", "date", "industry_neutral_rank_ic", "size_neutral_rank_ic", "cross_section", "industry_count"],
    )
    _write_csv(
        output_path / "lottery_extreme_upside_reversal_prescreen_reference_observations.csv",
        result.get("reference_observations", []),
        ["factor_name", "reference_name", "date", "spearman_corr", "cross_section"],
    )


def render_lottery_extreme_upside_reversal_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    neutral = result.get("neutral_policy", {})
    reference = result.get("reference_dedup_policy", {})
    lines = [
        "# Lottery Extreme Upside Reversal Prescreen Round150",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Aligned rows: {summary.get('aligned_rows', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- FDR-significant tests: {summary.get('multiple_testing_lead_count', 0)}",
        f"- Neutral-gate pass tests: {summary.get('neutral_gate_pass_count', 0)}",
        f"- Reference de-dup pass tests: {summary.get('reference_dedup_pass_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Next direction: {summary.get('next_direction', NEXT_DIRECTION_WITHOUT_LEADS)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Gate Policy",
        "",
        f"- Min neutral RankIC: {neutral.get('min_neutral_rank_ic', 0):.4f}",
        f"- Min neutral t-stat: {neutral.get('min_neutral_ic_t_stat', 0):.2f}",
        f"- Min neutral retention: {neutral.get('min_neutral_retention', 0):.2f}",
        f"- Max public reference correlation: {reference.get('max_reference_corr_abs', 0):.2f}",
        "",
        "## Top Results",
        "",
        "| Factor | H | IC | ICIR | t | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | Ref | RefCorr | Lead |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|",
    ]
    for row in result.get("results", [])[:25]:
        lines.append(
            "| {factor_name} | {horizon} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {spread:.4f} | {ind:.4f} | {size:.4f} | {ref} | {corr:.3f} | {lead} |".format(
                factor_name=row.get("factor_name", ""),
                horizon=int(row.get("horizon", 0)),
                ic=_number(row.get("mean_spearman_ic")),
                icir=_number(row.get("icir")),
                t=_number(row.get("ic_t_stat")),
                pos=_number(row.get("ic_positive_rate")),
                spread=_number(row.get("quantile_spread")),
                ind=_number(row.get("mean_industry_neutral_rank_ic")),
                size=_number(row.get("mean_size_neutral_rank_ic")),
                ref=row.get("max_reference_name") or "none",
                corr=_number(row.get("max_reference_corr_abs")),
                lead="yes" if row.get("research_lead") else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This stage screens a public MAX-effect / lottery-demand hypothesis on long-cycle CN stock data.",
            "- Leads must survive raw IC, industry-neutral IC, size/liquidity-neutral IC, and public-reference de-duplication.",
            "- Portfolio backtests, parameter grids, paper-ready promotion, and live use remain blocked after this stage.",
        ]
    )
    return "\n".join(lines) + "\n"


def _feature_frame(bars: pd.DataFrame) -> pd.DataFrame:
    bars = _normalise_bars(bars)
    pieces: list[pd.DataFrame] = []
    for _, group in bars.sort_values(["asset_id", "date"]).groupby("asset_id", sort=False):
        group = group.copy().reset_index(drop=True)
        close = group["adj_close"]
        high = group["high"]
        low = group["low"]
        amount = group["amount"]
        returns = close.pct_change()
        adv20 = amount.rolling(20, min_periods=5).mean()
        amount_spike_5_20 = amount.rolling(5, min_periods=3).mean() / amount.rolling(20, min_periods=5).mean()
        price_range = (high - low).replace(0.0, float("nan"))
        positive_return = (returns > 0).astype(float)
        upper_shadow = ((high - close) / price_range) * positive_return
        gapless_return = returns.where(amount_spike_5_20 <= 2.0)
        frame = group[["date", "asset_id", "market", "amount"]].copy()
        frame["return_1d"] = returns
        frame["reversal_5"] = -close.pct_change(5)
        frame["adv20_amount"] = adv20
        frame["log_adv20"] = adv20.where(adv20 > 0).apply(math.log)
        frame["max_return_20"] = returns.rolling(20, min_periods=5).max()
        frame["max_return_60"] = returns.rolling(60, min_periods=15).max()
        frame["min_return_60"] = returns.rolling(60, min_periods=15).min()
        frame["amount_spike_5_20"] = amount_spike_5_20
        frame["limit_chase_count_20"] = (returns > 0.08).astype(float).rolling(20, min_periods=5).sum()
        frame["climax_volume_20"] = (returns * amount_spike_5_20).rolling(20, min_periods=5).max()
        frame["upper_shadow_positive_20"] = upper_shadow.rolling(20, min_periods=5).mean()
        frame["gapless_max_20"] = gapless_return.rolling(20, min_periods=5).max()
        frame["realized_vol_20"] = returns.rolling(20, min_periods=5).std(ddof=0)
        pieces.append(frame)
    if not pieces:
        return pd.DataFrame()
    features = pd.concat(pieces, ignore_index=True)
    features["upside_tail_asymmetry_60"] = features["max_return_60"] - features["min_return_60"].abs()
    features["limit_chase_exhaustion_20"] = features["limit_chase_count_20"] * features["amount_spike_5_20"]
    return features.replace([float("inf"), float("-inf")], float("nan"))


def _add_cross_sectional_features(features: pd.DataFrame) -> pd.DataFrame:
    if features.empty:
        return features
    frame = features.copy()
    z_inputs = {
        "z_reversal_5": frame["reversal_5"],
        "z_neg_max_return_20": -frame["max_return_20"],
        "z_neg_limit_chase_exhaustion_20": -frame["limit_chase_exhaustion_20"],
        "z_neg_upside_tail_asymmetry_60": -frame["upside_tail_asymmetry_60"],
        "z_neg_climax_volume_20": -frame["climax_volume_20"],
        "z_neg_upper_shadow_positive_20": -frame["upper_shadow_positive_20"],
        "z_neg_gapless_max_20": -frame["gapless_max_20"],
        "z_neg_realized_vol_20": -frame["realized_vol_20"],
        "z_log_adv20": frame["log_adv20"],
    }
    for column, series in z_inputs.items():
        frame[column] = _cs_zscore(frame, series)
    return frame


def _reference_correlation_rows(
    factor_frame: pd.DataFrame,
    reference_frame: pd.DataFrame,
    *,
    min_cross_section: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    factors = _normalise_factor_frame(factor_frame)
    references = _normalise_reference_frame(reference_frame)
    if factors.empty or references.empty:
        return [], []
    observations: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for factor_name, factor_group in factors.groupby("factor_name", sort=False):
        best_name = ""
        best_corr = -1.0
        best_obs = 0
        for reference_name, reference_group in references.groupby("reference_name", sort=False):
            merged = factor_group.merge(reference_group, on=["date", "asset_id", "market"], how="inner")
            corr_values: list[float] = []
            for signal_date, date_frame in merged.groupby("date", sort=True):
                valid = date_frame.dropna(subset=["factor_value", "reference_value"])
                if len(valid) < min_cross_section:
                    continue
                corr = _spearman(valid["factor_value"], valid["reference_value"])
                if not _is_finite(corr):
                    continue
                corr_values.append(abs(float(corr)))
                observations.append(
                    {
                        "factor_name": str(factor_name),
                        "reference_name": str(reference_name),
                        "date": pd.Timestamp(signal_date).date().isoformat(),
                        "spearman_corr": float(corr),
                        "cross_section": int(len(valid)),
                    }
                )
            if not corr_values:
                continue
            mean_abs_corr = float(pd.Series(corr_values).mean())
            if not best_name or mean_abs_corr > best_corr:
                best_name = str(reference_name)
                best_corr = mean_abs_corr
                best_obs = len(corr_values)
        summary_rows.append(
            {
                "factor_name": str(factor_name),
                "max_reference_name": best_name,
                "max_reference_corr_abs": best_corr if best_name else 1.0,
                "reference_observations": int(best_obs),
            }
        )
    return summary_rows, observations


def _capacity_mask(features: pd.DataFrame, *, min_signal_date_amount: float) -> pd.Series:
    return (
        (features["amount"] >= min_signal_date_amount)
        & (features["adv20_amount"] >= min_signal_date_amount)
        & (features["return_1d"].abs() <= 0.50)
    )


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "high", "low", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing required columns: {', '.join(missing)}")
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    for column in ["adj_close", "high", "low", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=required)
    frame = frame[(frame["market"] == "CN") & (frame["adj_close"] > 0) & (frame["high"] > 0) & (frame["low"] > 0)]
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _normalise_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return _empty_factor_frame()
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"])
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].fillna("CN").astype(str).str.upper()
    output["factor_name"] = output["factor_name"].astype(str)
    output["factor_value"] = pd.to_numeric(output["factor_value"], errors="coerce")
    return output.dropna(subset=["date", "asset_id", "market", "factor_name", "factor_value"]).reset_index(drop=True)


def _normalise_reference_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return _empty_reference_frame()
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"])
    output["asset_id"] = output["asset_id"].astype(str)
    output["market"] = output["market"].fillna("CN").astype(str).str.upper()
    output["reference_name"] = output["reference_name"].astype(str)
    output["reference_value"] = pd.to_numeric(output["reference_value"], errors="coerce")
    return output.dropna(subset=["date", "asset_id", "market", "reference_name", "reference_value"]).reset_index(drop=True)


def _filter_date_window(
    bars: pd.DataFrame,
    *,
    start_date: str,
    end_date: str,
    include_final_holdout: bool,
) -> pd.DataFrame:
    if bars.empty:
        return bars.copy()
    end = bars["date"].max() if include_final_holdout else pd.Timestamp(end_date)
    return bars[(bars["date"] >= pd.Timestamp(start_date)) & (bars["date"] <= end)].reset_index(drop=True)


def _cs_zscore(frame: pd.DataFrame, series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    grouped = values.groupby(frame["date"])
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return (values - mean) / std.replace(0.0, float("nan"))


def _spearman(left: pd.Series, right: pd.Series) -> float:
    aligned = pd.concat([left, right], axis=1).dropna()
    if len(aligned) < 2:
        return float("nan")
    left_values = aligned.iloc[:, 0]
    right_values = aligned.iloc[:, 1]
    if left_values.nunique() < 2 or right_values.nunique() < 2:
        return float("nan")
    return float(left_values.rank(method="average").corr(right_values.rank(method="average")))


def _data_window(bars: pd.DataFrame, factor_frame: pd.DataFrame, labels: pd.DataFrame) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "min_signal_date": _min_date(factor_frame, "date"),
        "max_signal_date": _max_date(factor_frame, "date"),
        "min_label_date": _min_date(labels, "date"),
        "max_label_date": _max_date(labels, "date"),
        "bar_rows": int(len(bars)),
        "bar_assets": int(bars["asset_id"].nunique()) if not bars.empty else 0,
        "factor_rows": int(len(factor_frame)),
    }


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["date", "asset_id", "market", "factor_name", "factor_value", "amount", "adv20_amount", "log_adv20"]
    )


def _empty_reference_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "asset_id", "market", "reference_name", "reference_value"])


def _empty_reference_summary(factor_name: str) -> dict[str, Any]:
    return {
        "factor_name": factor_name,
        "max_reference_name": "",
        "max_reference_corr_abs": 1.0,
        "reference_observations": 0,
    }


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _is_finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _spec_payload(spec: Any) -> dict[str, Any]:
    if hasattr(spec, "__dataclass_fields__"):
        payload = asdict(spec)
        for key, value in list(payload.items()):
            if isinstance(value, tuple):
                payload[key] = list(value)
        return payload
    return dict(spec)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
