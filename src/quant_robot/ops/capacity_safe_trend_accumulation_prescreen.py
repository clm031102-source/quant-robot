from __future__ import annotations

from dataclasses import asdict
from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_preregistration import (
    DEFAULT_CAPACITY_FILTERS,
    SAFETY,
)
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
    RESULT_COLUMNS,
    load_capacity_safe_bars,
    summarize_capacity_safe_price_volume_prescreen,
)
from quant_robot.ops.capacity_safe_trend_accumulation_preregistration import (
    default_capacity_safe_trend_accumulation_candidate_specs,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "capacity_safe_trend_accumulation_prescreen"


def build_capacity_safe_trend_accumulation_prescreen(
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
    specs = list(candidate_specs or default_capacity_safe_trend_accumulation_candidate_specs())
    bars = load_capacity_safe_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    factor_frame = compute_capacity_safe_trend_accumulation_factors(
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
    result["stage"] = STAGE
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
    result["promotion_policy"] = {
        "promotion_allowed": False,
        "portfolio_backtest_allowed_before_prescreen": False,
        "requires_next_gate": "candidate_correlation_dedup_before_portfolio_grid",
        "reason": "Round105 is a long-cycle statistical prescreen for the pre-registered trend/amount accumulation family.",
    }
    result["candidate_specs"] = [_spec_payload(spec) for spec in specs]
    result["live_boundary_allowed"] = False
    result["safety"] = SAFETY
    result["markdown"] = render_capacity_safe_trend_accumulation_prescreen_markdown(result)
    return result


def compute_capacity_safe_trend_accumulation_factors(
    bars: pd.DataFrame,
    *,
    candidate_specs: Sequence[Any] | None = None,
    min_signal_date_amount: float = DEFAULT_CAPACITY_FILTERS["min_signal_date_amount"],
) -> pd.DataFrame:
    specs = list(candidate_specs or default_capacity_safe_trend_accumulation_candidate_specs())
    features = _feature_frame(bars)
    if features.empty:
        return pd.DataFrame(
            columns=["date", "asset_id", "market", "factor_name", "factor_value", "amount", "adv20_amount"]
        )
    features = _add_cross_sectional_features(features)
    candidate_values = {
        "volume_weighted_momentum_quality_20": (
            0.50 * features["z_volume_weighted_return_20"]
            + 0.30 * features["z_return_efficiency_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "amount_accumulation_breakout_20_60": (
            0.45 * features["z_price_breakout_20"]
            + 0.35 * features["z_amount_trend_20_60"]
            + 0.20 * features["z_log_adv20"]
        ),
        "money_pressure_efficiency_20": (
            0.55 * features["z_money_pressure_20"]
            + 0.25 * features["z_return_efficiency_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "relative_amount_trend_confirmed_momentum_20_60": (
            0.45 * features["z_skip5_momentum_20"]
            + 0.35 * features["z_amount_trend_20_60"]
            + 0.20 * features["z_log_adv20"]
        ),
        "obv_proxy_trend_quality_20": (
            0.50 * features["z_obv_slope_20"]
            + 0.30 * features["z_momentum_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "high_volume_breakout_quality_20": (
            0.45 * features["z_close_to_20d_high"]
            + 0.35 * features["z_amount_zscore_20"]
            + 0.20 * features["z_return_efficiency_20"]
        ),
        "liquidity_qualified_relative_strength_60": (
            0.55 * features["z_momentum_60"]
            + 0.25 * features["z_amount_percentile_60"]
            + 0.20 * features["z_return_efficiency_20"]
        ),
        "price_path_efficiency_amount_confirmed_20": (
            0.50 * features["z_return_efficiency_20"]
            + 0.30 * features["z_amount_trend_20_60"]
            + 0.20 * features["z_log_adv20"]
        ),
        "accumulation_distribution_proxy_20": (
            0.50 * features["z_accumulation_distribution_20"]
            + 0.30 * features["z_momentum_20"]
            + 0.20 * features["z_log_adv20"]
        ),
        "turnover_expansion_momentum_10_40": (
            0.45 * features["z_momentum_20"]
            + 0.35 * features["z_amount_expansion_10_40"]
            + 0.20 * features["z_log_adv20"]
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


def write_capacity_safe_trend_accumulation_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "capacity_safe_trend_accumulation_prescreen.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "capacity_safe_trend_accumulation_prescreen.md").write_text(
        render_capacity_safe_trend_accumulation_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "capacity_safe_trend_accumulation_prescreen_results.csv",
        result.get("results", []),
        RESULT_COLUMNS,
    )
    _write_csv(
        output_path / "capacity_safe_trend_accumulation_prescreen_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )


def render_capacity_safe_trend_accumulation_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Capacity-Safe Trend Accumulation Prescreen",
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
            "- If no lead survives, the trend/amount accumulation family should rotate rather than receive same-family parameter tuning.",
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
        amount_mean_10 = amount.rolling(10, min_periods=5).mean()
        amount_mean_20 = amount.rolling(20, min_periods=5).mean()
        amount_mean_40 = amount.rolling(40, min_periods=10).mean()
        amount_mean_60 = amount.rolling(60, min_periods=10).mean()
        amount_sum_20 = amount.rolling(20, min_periods=5).sum()
        rolling_high_20 = high.rolling(20, min_periods=5).max()
        high_low_range = (high - low).where((high - low) != 0)
        clv = ((close - low) - (high - close)) / high_low_range
        frame = group[["date", "asset_id", "market", "amount"]].copy()
        frame["return_1d"] = returns
        frame["adv20_amount"] = amount_mean_20
        frame["momentum_20"] = close.pct_change(20)
        frame["momentum_60"] = close.pct_change(60)
        frame["skip5_momentum_20"] = close.shift(5).pct_change(20)
        frame["amount_trend_20_60"] = amount_mean_20 / amount_mean_60.where(amount_mean_60 != 0) - 1.0
        frame["amount_expansion_10_40"] = amount_mean_10 / amount_mean_40.where(amount_mean_40 != 0) - 1.0
        frame["amount_zscore_20"] = (amount - amount_mean_20) / amount.rolling(20, min_periods=5).std(ddof=0).where(
            lambda item: item != 0
        )
        frame["amount_percentile_60"] = amount / amount.rolling(60, min_periods=10).max().where(lambda item: item != 0)
        frame["return_efficiency_20"] = frame["momentum_20"] / returns.abs().rolling(20, min_periods=5).sum().where(
            lambda item: item != 0
        )
        frame["volume_weighted_return_20"] = (returns * amount).rolling(20, min_periods=5).sum() / amount_sum_20.where(
            amount_sum_20 != 0
        )
        frame["price_breakout_20"] = close / rolling_high_20.where(rolling_high_20 != 0) - 1.0
        frame["close_to_20d_high"] = frame["price_breakout_20"]
        frame["money_pressure_20"] = frame["volume_weighted_return_20"]
        frame["obv_slope_20"] = (np.sign(returns) * amount).rolling(20, min_periods=5).sum() / amount_sum_20.where(
            amount_sum_20 != 0
        )
        frame["accumulation_distribution_20"] = (clv * amount).rolling(20, min_periods=5).sum() / amount_sum_20.where(
            amount_sum_20 != 0
        )
        pieces.append(frame)
    if not pieces:
        return pd.DataFrame()
    features = pd.concat(pieces, ignore_index=True)
    features["log_adv20"] = np.log(features["adv20_amount"].where(features["adv20_amount"] > 0))
    return features.replace([float("inf"), float("-inf")], pd.NA)


def _add_cross_sectional_features(features: pd.DataFrame) -> pd.DataFrame:
    frame = features.copy()
    z_inputs = {
        "z_volume_weighted_return_20": frame["volume_weighted_return_20"],
        "z_return_efficiency_20": frame["return_efficiency_20"],
        "z_log_adv20": frame["log_adv20"],
        "z_price_breakout_20": frame["price_breakout_20"],
        "z_amount_trend_20_60": frame["amount_trend_20_60"],
        "z_money_pressure_20": frame["money_pressure_20"],
        "z_skip5_momentum_20": frame["skip5_momentum_20"],
        "z_obv_slope_20": frame["obv_slope_20"],
        "z_momentum_20": frame["momentum_20"],
        "z_close_to_20d_high": frame["close_to_20d_high"],
        "z_amount_zscore_20": frame["amount_zscore_20"],
        "z_momentum_60": frame["momentum_60"],
        "z_amount_percentile_60": frame["amount_percentile_60"],
        "z_accumulation_distribution_20": frame["accumulation_distribution_20"],
        "z_amount_expansion_10_40": frame["amount_expansion_10_40"],
    }
    for column, series in z_inputs.items():
        frame[column] = _cs_zscore(frame, series)
    return frame


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


def _cs_zscore(frame: pd.DataFrame, series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    grouped = values.groupby(frame["date"])
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return (values - mean) / std.replace(0, pd.NA)


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
