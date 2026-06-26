from __future__ import annotations

from dataclasses import asdict
from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_preregistration import (
    DEFAULT_CAPACITY_FILTERS,
    SAFETY,
    default_capacity_safe_price_volume_candidate_specs,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "capacity_safe_price_volume_prescreen"
DEFAULT_ANALYSIS_START_DATE = "2015-01-01"
DEFAULT_ANALYSIS_END_DATE = "2025-12-31"
DEFAULT_HORIZONS = (5, 20)
RESULT_COLUMNS = [
    "factor_name",
    "horizon",
    "ic_observations",
    "mean_spearman_ic",
    "ic_std",
    "icir",
    "ic_t_stat",
    "ic_p_value",
    "bonferroni_significant",
    "fdr_significant",
    "ic_positive_rate",
    "quantile_spread",
    "quantile_monotonicity",
    "avg_top_quantile_turnover",
    "median_cross_section",
    "unique_dates",
    "unique_assets",
    "median_amount",
    "median_adv20_amount",
    "research_lead",
    "promotion_allowed",
    "blockers",
]


def build_capacity_safe_price_volume_prescreen(
    *,
    bars_roots: Iterable[str | Path],
    candidate_specs: Sequence[Any] | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = DEFAULT_CAPACITY_FILTERS["min_signal_date_amount"],
) -> dict[str, Any]:
    specs = list(candidate_specs or default_capacity_safe_price_volume_candidate_specs())
    bars = load_capacity_safe_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    factor_frame = compute_capacity_safe_price_volume_factors(
        bars,
        candidate_specs=specs,
        min_signal_date_amount=min_signal_date_amount,
    )
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=horizons,
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_capacity_safe_price_volume_prescreen(
        factor_frame,
        labels,
        expected_candidate_count=len(specs),
        candidate_specs=specs,
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
    )
    result["data_window"] = _data_window(bars, factor_frame, labels)
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
        "portfolio_backtest_allowed_before_prescreen_lead": False,
    }
    result["markdown"] = render_capacity_safe_price_volume_prescreen_markdown(result)
    return result


def load_capacity_safe_bars(
    bars_roots: Iterable[str | Path],
    *,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
) -> pd.DataFrame:
    files: list[Path] = []
    for root in bars_roots:
        root_path = Path(root)
        bars_root = root_path / "bars" if (root_path / "bars").exists() else root_path
        files.extend(sorted(bars_root.rglob("*.parquet")))
        files.extend(sorted(bars_root.rglob("*.csv")))
    frames = [_read_bars_file(file) for file in files if "market=CN" in str(file) or "bars" in str(file)]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        raise FileNotFoundError(f"No CN bars files found under: {', '.join(str(root) for root in bars_roots)}")
    bars = pd.concat(frames, ignore_index=True)
    bars = _normalise_bars(bars)
    start = pd.Timestamp(analysis_start_date)
    end = pd.Timestamp(analysis_end_date)
    if include_final_holdout:
        end = max(end, bars["date"].max())
    bars = bars[(bars["date"] >= start) & (bars["date"] <= end)]
    return (
        bars.drop_duplicates(["asset_id", "market", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def compute_capacity_safe_price_volume_factors(
    bars: pd.DataFrame,
    *,
    candidate_specs: Sequence[Any] | None = None,
    min_signal_date_amount: float = DEFAULT_CAPACITY_FILTERS["min_signal_date_amount"],
) -> pd.DataFrame:
    specs = list(candidate_specs or default_capacity_safe_price_volume_candidate_specs())
    features = _feature_frame(bars)
    if features.empty:
        return pd.DataFrame(
            columns=["date", "asset_id", "market", "factor_name", "factor_value", "amount", "adv20_amount"]
        )
    features = _add_cross_sectional_features(features)
    candidate_values = {
        "pv_lowvol_reversal_blend_20": (
            0.45 * features["z_reversal_5"]
            + 0.35 * features["z_neg_pv_corr_20"]
            + 0.20 * features["z_neg_downside_vol_20"]
        ),
        "range_contraction_lowvol_reversal_20": (
            0.40 * features["z_reversal_5"]
            + 0.35 * features["z_neg_hl_range_20"]
            + 0.25 * features["z_neg_realized_vol_20"]
        ),
        "volume_contraction_reversal_lowvol_20": (
            0.45 * features["z_reversal_5"]
            + 0.35 * features["z_neg_amount_trend_20"]
            + 0.20 * features["z_neg_downside_vol_20"]
        ),
        "price_volume_trend_quality_20_60": (
            0.40 * features["z_skip5_momentum_20"]
            + 0.35 * features["z_momentum_60"]
            + 0.25 * features["z_return_efficiency_20"]
        ),
        "skip5_momentum_lowvol_20": (
            0.60 * features["z_skip5_momentum_20"] + 0.40 * features["z_neg_realized_vol_20"]
        ),
        "pv_corr_reversal_capacity_safe_20": (
            0.70 * features["z_neg_pv_corr_20"] + 0.30 * features["z_log_adv20"]
        ),
        "bollinger_reversal_lowvol_liquid_20": (
            0.55 * features["z_bollinger_reversal_20"]
            + 0.25 * features["z_neg_realized_vol_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "rsi_reversal_lowvol_liquid_14_20": (
            0.55 * features["z_rsi_reversal_14"]
            + 0.25 * features["z_neg_downside_vol_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "amount_stability_reversal_5_20": (
            0.50 * features["z_reversal_5"]
            + 0.30 * features["z_neg_abs_amount_trend_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "donchian_pullback_lowvol_liquid_20": (
            0.45 * features["z_inverse_donchian_position_20"]
            + 0.30 * features["z_neg_realized_vol_20"]
            + 0.25 * features["z_log_adv20"]
        ),
    }
    allowed_names = {spec.factor_name for spec in specs}
    rows: list[pd.DataFrame] = []
    base_columns = ["date", "asset_id", "market", "amount", "adv20_amount"]
    capacity_mask = (
        (features["amount"] >= min_signal_date_amount)
        & (features["adv20_amount"] >= min_signal_date_amount)
        & (features["return_1d"].abs() <= 0.50)
    )
    for factor_name, values in candidate_values.items():
        if factor_name not in allowed_names:
            continue
        frame = features.loc[capacity_mask, base_columns].copy()
        frame["factor_name"] = factor_name
        frame["factor_value"] = values.loc[capacity_mask]
        frame = frame.dropna(subset=["factor_value", "amount", "adv20_amount"])
        rows.append(frame)
    if not rows:
        return pd.DataFrame(
            columns=["date", "asset_id", "market", "factor_name", "factor_value", "amount", "adv20_amount"]
        )
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def summarize_capacity_safe_price_volume_prescreen(
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    expected_candidate_count: int | None = None,
    candidate_specs: Sequence[Any] | None = None,
    horizons: tuple[int, ...] | None = None,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    alpha: float = 0.05,
    min_abs_ic: float = 0.02,
    min_abs_icir: float = 0.30,
    min_positive_ic_rate: float = 0.55,
    max_top_quantile_turnover: float = 0.90,
) -> dict[str, Any]:
    factor_frame = factor_frame.copy()
    labels = labels.copy()
    if not factor_frame.empty:
        factor_frame["date"] = pd.to_datetime(factor_frame["date"])
    if not labels.empty:
        labels["date"] = pd.to_datetime(labels["date"])
    results: list[dict[str, Any]] = []
    ic_rows: list[dict[str, Any]] = []
    aligned_rows = 0
    requested_horizons = tuple(horizons or tuple(sorted(labels["horizon"].unique()))) if not labels.empty else tuple()
    labels_by_horizon = {
        int(horizon): horizon_frame.drop(columns=["horizon"]).copy()
        for horizon, horizon_frame in labels[labels["horizon"].isin(requested_horizons)].groupby("horizon", sort=False)
    }
    for factor_name, factor_group in factor_frame.groupby("factor_name", sort=False):
        factor_group = factor_group.copy()
        for horizon in requested_horizons:
            label_group = labels_by_horizon.get(int(horizon))
            if label_group is None or label_group.empty:
                group = pd.DataFrame(columns=list(factor_group.columns) + list(labels.columns))
            else:
                group = factor_group.merge(
                    label_group,
                    on=["date", "asset_id", "market"],
                    how="inner",
                    validate="many_to_one",
                )
            aligned_rows += len(group)
            summary, observations = _summarize_factor_horizon(
                factor_name=str(factor_name),
                horizon=int(horizon),
                group=group,
                min_cross_section=min_cross_section,
                min_ic_observations=min_ic_observations,
            )
            results.append(summary)
            ic_rows.extend(observations)
    _apply_multiple_testing(results, alpha=alpha)
    for row in results:
        row["research_lead"] = _is_research_lead(
            row,
            min_abs_ic=min_abs_ic,
            min_abs_icir=min_abs_icir,
            min_positive_ic_rate=min_positive_ic_rate,
            max_top_quantile_turnover=max_top_quantile_turnover,
        )
        row["promotion_allowed"] = False
        row["blockers"] = _result_blockers(row)
    candidate_count = expected_candidate_count if expected_candidate_count is not None else factor_frame["factor_name"].nunique()
    result = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": {
            "passes": True,
            "candidate_count": int(candidate_count),
            "factor_names_with_rows": int(factor_frame["factor_name"].nunique()) if not factor_frame.empty else 0,
            "test_count": len(results),
            "research_lead_count": sum(1 for row in results if row["research_lead"]),
            "multiple_testing_lead_count": sum(1 for row in results if row["fdr_significant"]),
            "promotion_allowed_candidates": 0,
            "factor_rows": int(len(factor_frame)),
            "label_rows": int(len(labels)),
            "aligned_rows": int(aligned_rows),
            "horizons": sorted(int(horizon) for horizon in requested_horizons),
            "min_cross_section": min_cross_section,
            "min_ic_observations": min_ic_observations,
        },
        "candidate_specs": [_spec_payload(spec) for spec in (candidate_specs or default_capacity_safe_price_volume_candidate_specs())],
        "multiple_testing_policy": {
            "alpha": alpha,
            "method": "Bonferroni and Benjamini-Hochberg FDR across factor x horizon tests",
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_backtest_allowed_before_prescreen": False,
            "requires_next_gate": "candidate_correlation_dedup_before_portfolio_grid",
            "reason": "This is an Alphalens-style statistical prescreen, not a tradable portfolio validation.",
        },
        "results": sorted(results, key=lambda row: (not row["research_lead"], -abs(row["mean_spearman_ic"]))),
        "ic_observations": ic_rows,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_capacity_safe_price_volume_prescreen_markdown(result)
    return result


def write_capacity_safe_price_volume_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "capacity_safe_price_volume_prescreen.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "capacity_safe_price_volume_prescreen.md").write_text(
        render_capacity_safe_price_volume_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "capacity_safe_price_volume_prescreen_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(
        output_path / "capacity_safe_price_volume_prescreen_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )


def render_capacity_safe_price_volume_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Capacity-Safe Price-Volume Prescreen",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Aligned rows: {summary.get('aligned_rows', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- FDR-significant tests: {summary.get('multiple_testing_lead_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Final holdout included: {result.get('holdout_policy', {}).get('final_holdout_included', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Top Results",
        "",
        "| Factor | Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Mono | Turnover | FDR | Lead |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("results", [])[:20]:
        lines.append(
            "| {factor_name} | {horizon} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {spread:.4f} | {mono:.3f} | {turnover:.1%} | {fdr} | {lead} |".format(
                factor_name=row["factor_name"],
                horizon=row["horizon"],
                ic=row["mean_spearman_ic"],
                icir=row["icir"],
                t=row["ic_t_stat"],
                pos=row["ic_positive_rate"],
                spread=row["quantile_spread"],
                mono=row["quantile_monotonicity"],
                turnover=row["avg_top_quantile_turnover"],
                fdr="yes" if row["fdr_significant"] else "no",
                lead="yes" if row["research_lead"] else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This stage can create research leads only; it cannot promote a factor to paper-ready or live use.",
            "- Any lead must next pass correlation de-duplication, long-cycle walk-forward, cost/capacity, and regime checks.",
        ]
    )
    return "\n".join(lines) + "\n"


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
    ]
    if file.suffix == ".parquet":
        try:
            return pd.read_parquet(file, columns=columns)
        except Exception:
            frame = pd.read_parquet(file)
            return frame[[column for column in columns if column in frame.columns]]
    frame = pd.read_csv(file)
    return frame[[column for column in columns if column in frame.columns]]


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "high", "low", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing required columns: {', '.join(missing)}")
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["market"] = frame["market"].fillna("CN").astype(str)
    frame["asset_id"] = frame["asset_id"].astype(str)
    for column in ["adj_close", "high", "low", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=required)
    frame = frame[(frame["market"] == "CN") & (frame["adj_close"] > 0) & (frame["high"] > 0) & (frame["low"] > 0)]
    return frame


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
        amount_returns = amount.pct_change()
        adv20 = amount.rolling(20, min_periods=5).mean()
        rolling_high20 = high.rolling(20, min_periods=5).max()
        rolling_low20 = low.rolling(20, min_periods=5).min()
        range_width = (rolling_high20 - rolling_low20).replace(0, pd.NA)
        ma20 = close.rolling(20, min_periods=10).mean()
        std20 = close.rolling(20, min_periods=10).std(ddof=0).replace(0, pd.NA)
        rsi = _rsi(close, 14)
        frame = group[["date", "asset_id", "market", "amount"]].copy()
        frame["return_1d"] = returns
        frame["reversal_5"] = -close.pct_change(5)
        frame["momentum_20"] = close.pct_change(20)
        frame["momentum_60"] = close.pct_change(60)
        frame["skip5_momentum_20"] = close.shift(5).pct_change(20)
        frame["amount_trend_20"] = amount.rolling(5, min_periods=3).mean() / amount.rolling(20, min_periods=5).mean() - 1.0
        frame["pv_corr_20"] = returns.rolling(20, min_periods=10).corr(amount_returns)
        frame["adv20_amount"] = adv20
        frame["downside_vol_20"] = returns.clip(upper=0).rolling(20, min_periods=5).std(ddof=0)
        frame["realized_vol_20"] = returns.rolling(20, min_periods=5).std(ddof=0)
        frame["hl_range_20"] = ((high / low) - 1.0).rolling(20, min_periods=5).mean()
        frame["donchian_position_20"] = (close - rolling_low20) / range_width
        frame["return_efficiency_20"] = frame["momentum_20"] / returns.abs().rolling(20, min_periods=5).sum()
        frame["bollinger_reversal_20"] = -((close - ma20) / std20)
        frame["rsi_reversal_14"] = 100.0 - rsi
        pieces.append(frame)
    if not pieces:
        return pd.DataFrame()
    features = pd.concat(pieces, ignore_index=True)
    features["pv_divergence_20"] = -features["momentum_20"] * features["amount_trend_20"]
    features["range_position_20"] = features["donchian_position_20"]
    features["inverse_donchian_position_20"] = 1.0 - features["donchian_position_20"]
    features["log_adv20"] = features["adv20_amount"].where(features["adv20_amount"] > 0).apply(math.log)
    return features.replace([float("inf"), float("-inf")], pd.NA)


def _add_cross_sectional_features(features: pd.DataFrame) -> pd.DataFrame:
    frame = features.copy()
    z_inputs = {
        "z_reversal_5": frame["reversal_5"],
        "z_neg_pv_corr_20": -frame["pv_corr_20"],
        "z_neg_downside_vol_20": -frame["downside_vol_20"],
        "z_neg_hl_range_20": -frame["hl_range_20"],
        "z_neg_realized_vol_20": -frame["realized_vol_20"],
        "z_neg_amount_trend_20": -frame["amount_trend_20"],
        "z_skip5_momentum_20": frame["skip5_momentum_20"],
        "z_momentum_60": frame["momentum_60"],
        "z_return_efficiency_20": frame["return_efficiency_20"],
        "z_log_adv20": frame["log_adv20"],
        "z_bollinger_reversal_20": frame["bollinger_reversal_20"],
        "z_rsi_reversal_14": frame["rsi_reversal_14"],
        "z_neg_abs_amount_trend_20": -frame["amount_trend_20"].abs(),
        "z_inverse_donchian_position_20": frame["inverse_donchian_position_20"],
    }
    for column, series in z_inputs.items():
        frame[column] = _cs_zscore(frame, series)
    return frame


def _cs_zscore(frame: pd.DataFrame, series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    grouped = values.groupby(frame["date"])
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return (values - mean) / std.replace(0, pd.NA)


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window, min_periods=max(5, window // 2)).mean()
    loss = (-delta.clip(upper=0)).rolling(window, min_periods=max(5, window // 2)).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100.0 - 100.0 / (1.0 + rs)


def _summarize_factor_horizon(
    *,
    factor_name: str,
    horizon: int,
    group: pd.DataFrame,
    min_cross_section: int,
    min_ic_observations: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ic_values: list[float] = []
    cross_sections: list[int] = []
    quantile_returns: list[list[float]] = []
    top_sets: list[set[str]] = []
    dates: list[pd.Timestamp] = []
    observations: list[dict[str, Any]] = []
    for signal_date, date_frame in group.groupby("date", sort=True):
        date_frame = date_frame.dropna(subset=["factor_value", "forward_return"])
        if len(date_frame) < min_cross_section:
            continue
        ic = _spearman(date_frame["factor_value"], date_frame["forward_return"])
        if not _is_finite(ic):
            continue
        quantiles = _quantile_labels(date_frame["factor_value"])
        if quantiles is None:
            continue
        group_means = []
        for quantile in range(5):
            group_means.append(float(date_frame.loc[quantiles == quantile, "forward_return"].mean()))
        top_assets = set(date_frame.loc[quantiles == 4, "asset_id"].astype(str))
        ic_values.append(float(ic))
        cross_sections.append(int(len(date_frame)))
        quantile_returns.append(group_means)
        top_sets.append(top_assets)
        dates.append(pd.Timestamp(signal_date))
        observations.append(
            {
                "factor_name": factor_name,
                "horizon": horizon,
                "date": pd.Timestamp(signal_date).date().isoformat(),
                "spearman_ic": float(ic),
                "cross_section": int(len(date_frame)),
            }
        )
    if len(ic_values) < min_ic_observations:
        return _empty_result(factor_name, horizon, len(ic_values), group), observations
    ic_series = pd.Series(ic_values, dtype=float)
    mean_ic = float(ic_series.mean())
    ic_std = float(ic_series.std(ddof=1)) if len(ic_series) > 1 else 0.0
    icir = _safe_ratio(mean_ic, ic_std)
    t_stat = _t_stat(mean_ic, ic_std, len(ic_series))
    p_value = _normal_two_sided_p_value(t_stat)
    quantile_frame = pd.DataFrame(quantile_returns, columns=["q1", "q2", "q3", "q4", "q5"], index=dates)
    quantile_spread = float((quantile_frame["q5"] - quantile_frame["q1"]).mean())
    quantile_monotonicity = _spearman(pd.Series(range(1, 6)), pd.Series(quantile_frame.mean().to_list()))
    turnover = _average_top_quantile_turnover(top_sets)
    return (
        {
            "factor_name": factor_name,
            "horizon": horizon,
            "ic_observations": int(len(ic_values)),
            "mean_spearman_ic": mean_ic,
            "ic_std": ic_std,
            "icir": icir,
            "ic_t_stat": t_stat,
            "ic_p_value": p_value,
            "bonferroni_significant": False,
            "fdr_significant": False,
            "ic_positive_rate": float((ic_series > 0).mean()),
            "quantile_spread": quantile_spread,
            "quantile_monotonicity": float(quantile_monotonicity) if _is_finite(quantile_monotonicity) else 0.0,
            "avg_top_quantile_turnover": turnover,
            "median_cross_section": float(pd.Series(cross_sections).median()),
            "unique_dates": int(len(set(dates))),
            "unique_assets": int(group["asset_id"].nunique()),
            "median_amount": float(group["amount"].median()) if "amount" in group else 0.0,
            "median_adv20_amount": float(group["adv20_amount"].median()) if "adv20_amount" in group else 0.0,
            "research_lead": False,
            "promotion_allowed": False,
            "blockers": [],
        },
        observations,
    )


def _empty_result(factor_name: str, horizon: int, ic_observations: int, group: pd.DataFrame) -> dict[str, Any]:
    return {
        "factor_name": factor_name,
        "horizon": horizon,
        "ic_observations": int(ic_observations),
        "mean_spearman_ic": 0.0,
        "ic_std": 0.0,
        "icir": 0.0,
        "ic_t_stat": 0.0,
        "ic_p_value": 1.0,
        "bonferroni_significant": False,
        "fdr_significant": False,
        "ic_positive_rate": 0.0,
        "quantile_spread": 0.0,
        "quantile_monotonicity": 0.0,
        "avg_top_quantile_turnover": 1.0,
        "median_cross_section": 0.0,
        "unique_dates": 0,
        "unique_assets": int(group["asset_id"].nunique()) if "asset_id" in group else 0,
        "median_amount": float(group["amount"].median()) if "amount" in group and not group.empty else 0.0,
        "median_adv20_amount": float(group["adv20_amount"].median()) if "adv20_amount" in group and not group.empty else 0.0,
        "research_lead": False,
        "promotion_allowed": False,
        "blockers": [],
    }


def _apply_multiple_testing(results: list[dict[str, Any]], *, alpha: float) -> None:
    if not results:
        return
    p_values = [float(row["ic_p_value"]) for row in results]
    bonferroni_alpha = alpha / len(results)
    for row in results:
        row["bonferroni_significant"] = bool(row["ic_p_value"] <= bonferroni_alpha)
    sorted_pairs = sorted(enumerate(p_values), key=lambda pair: pair[1])
    largest_pass = -1
    for rank, (_, p_value) in enumerate(sorted_pairs, start=1):
        if p_value <= alpha * rank / len(results):
            largest_pass = rank - 1
    passing_indexes = {sorted_pairs[index][0] for index in range(largest_pass + 1)}
    for index, row in enumerate(results):
        row["fdr_significant"] = index in passing_indexes


def _is_research_lead(
    row: dict[str, Any],
    *,
    min_abs_ic: float,
    min_abs_icir: float,
    min_positive_ic_rate: float,
    max_top_quantile_turnover: float,
) -> bool:
    return bool(
        row["fdr_significant"]
        and row["mean_spearman_ic"] >= min_abs_ic
        and row["icir"] >= min_abs_icir
        and row["ic_positive_rate"] >= min_positive_ic_rate
        and row["quantile_spread"] > 0
        and row["quantile_monotonicity"] >= 0.70
        and row["avg_top_quantile_turnover"] <= max_top_quantile_turnover
    )


def _result_blockers(row: dict[str, Any]) -> list[str]:
    blockers = []
    if not row["fdr_significant"]:
        blockers.append("not_fdr_significant_after_multiple_testing")
    if row["mean_spearman_ic"] < 0.02:
        blockers.append("mean_ic_below_threshold")
    if row["icir"] < 0.30:
        blockers.append("icir_below_threshold")
    if row["ic_positive_rate"] < 0.55:
        blockers.append("ic_positive_rate_below_threshold")
    if row["quantile_spread"] <= 0:
        blockers.append("top_minus_bottom_quantile_not_positive")
    if row["quantile_monotonicity"] < 0.70:
        blockers.append("quantile_monotonicity_weak")
    if row["avg_top_quantile_turnover"] > 0.90:
        blockers.append("top_quantile_turnover_too_high")
    blockers.append("promotion_requires_later_walk_forward_cost_capacity_regime_gates")
    return blockers


def _spearman(left: pd.Series, right: pd.Series) -> float:
    aligned = pd.concat([left, right], axis=1).dropna()
    if len(aligned) < 2:
        return float("nan")
    return float(aligned.iloc[:, 0].rank(method="average").corr(aligned.iloc[:, 1].rank(method="average")))


def _quantile_labels(values: pd.Series) -> pd.Series | None:
    try:
        return pd.qcut(values.rank(method="first"), 5, labels=False)
    except ValueError:
        return None


def _average_top_quantile_turnover(top_sets: list[set[str]]) -> float:
    turnovers = []
    for previous, current in zip(top_sets, top_sets[1:]):
        if not previous:
            continue
        turnovers.append(1.0 - len(previous.intersection(current)) / len(previous))
    if not turnovers:
        return 0.0
    return float(pd.Series(turnovers).mean())


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        if numerator > 0:
            return float("inf")
        if numerator < 0:
            return float("-inf")
        return 0.0
    return float(numerator / denominator)


def _t_stat(mean: float, std: float, observations: int) -> float:
    if observations <= 1:
        return 0.0
    if std == 0:
        if mean > 0:
            return float("inf")
        if mean < 0:
            return float("-inf")
        return 0.0
    return float(mean / (std / math.sqrt(observations)))


def _normal_two_sided_p_value(t_stat: float) -> float:
    if math.isinf(t_stat):
        return 0.0
    if not math.isfinite(t_stat):
        return 1.0
    return float(math.erfc(abs(t_stat) / math.sqrt(2.0)))


def _is_finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _spec_payload(spec: Any) -> dict[str, Any]:
    if hasattr(spec, "__dataclass_fields__"):
        payload = asdict(spec)
        payload["windows"] = list(payload["windows"])
        payload["required_fields"] = list(payload["required_fields"])
        payload["public_reference_tags"] = list(payload["public_reference_tags"])
        return payload
    return dict(spec)


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
    }


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
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
