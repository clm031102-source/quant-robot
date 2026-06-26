from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


DAILY_BASIC_TECHNICAL_COMBO_FACTOR_NAMES = (
    "turnover_rate_low_liquid_mv_bucket_rank",
    "turnover_rate_f_low_liquid_mv_bucket_rank",
    "turnover_rate_low_adv_blend_mv_bucket_rank",
    "turnover_rate_f_low_adv_blend_mv_bucket_rank",
)


def compute_daily_basic_technical_combo_factors(
    bars: pd.DataFrame,
    daily_basic_inputs: pd.DataFrame,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    _require_columns(
        bars,
        ["date", "asset_id", "market", "amount"],
        "bars",
    )
    _require_columns(
        daily_basic_inputs,
        ["date", "asset_id", "market", "turnover_rate", "turnover_rate_f", "circ_mv"],
        "daily-basic inputs",
    )
    requested = _resolve_requested_factor_names(factor_names)
    frame = _merge_daily_basic_with_adv(bars, daily_basic_inputs)
    builders = {
        "turnover_rate_low_liquid_mv_bucket_rank": lambda: _liquid_bucket_rank(
            -pd.to_numeric(frame["turnover_rate"], errors="coerce"),
            frame["circ_mv"],
            frame["adv20_amount"],
            frame["date"],
        ),
        "turnover_rate_f_low_liquid_mv_bucket_rank": lambda: _liquid_bucket_rank(
            -pd.to_numeric(frame["turnover_rate_f"], errors="coerce"),
            frame["circ_mv"],
            frame["adv20_amount"],
            frame["date"],
        ),
        "turnover_rate_low_adv_blend_mv_bucket_rank": lambda: _adv_blend_bucket_rank(
            -pd.to_numeric(frame["turnover_rate"], errors="coerce"),
            frame["circ_mv"],
            frame["adv20_amount"],
            frame["date"],
        ),
        "turnover_rate_f_low_adv_blend_mv_bucket_rank": lambda: _adv_blend_bucket_rank(
            -pd.to_numeric(frame["turnover_rate_f"], errors="coerce"),
            frame["circ_mv"],
            frame["adv20_amount"],
            frame["date"],
        ),
    }
    pieces = [_factor_frame(frame, name, builders[name]()) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} are missing columns: {', '.join(missing)}")


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return DAILY_BASIC_TECHNICAL_COMBO_FACTOR_NAMES
    supported = set(DAILY_BASIC_TECHNICAL_COMBO_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported daily-basic technical combo factor_names: {', '.join(unknown)}")
    return factor_names


def _merge_daily_basic_with_adv(bars: pd.DataFrame, daily_basic_inputs: pd.DataFrame) -> pd.DataFrame:
    bar_frame = bars.copy()
    bar_frame["date"] = pd.to_datetime(bar_frame["date"]).dt.date
    bar_frame = bar_frame.sort_values(["asset_id", "date"])
    bar_frame["amount"] = pd.to_numeric(bar_frame["amount"], errors="coerce")
    bar_frame["adv20_amount"] = (
        bar_frame.groupby("asset_id", sort=False)["amount"]
        .transform(lambda series: series.rolling(20, min_periods=1).mean())
    )
    adv = bar_frame[["date", "asset_id", "market", "adv20_amount"]]

    inputs = daily_basic_inputs.copy()
    inputs["date"] = pd.to_datetime(inputs["date"]).dt.date
    merged = inputs.merge(adv, on=["date", "asset_id", "market"], how="left")
    return merged.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _liquid_bucket_rank(
    signal: pd.Series,
    circ_mv: pd.Series,
    adv20_amount: pd.Series,
    dates: pd.Series,
    *,
    size_bucket_count: int = 5,
    min_liquidity_rank: float = 0.50,
) -> pd.Series:
    frame = pd.DataFrame(
        {
            "signal": pd.to_numeric(signal, errors="coerce"),
            "size": _safe_log(circ_mv),
            "adv20_amount": pd.to_numeric(adv20_amount, errors="coerce"),
            "date": dates,
        }
    )
    result = pd.Series(np.nan, index=frame.index, dtype=float)
    valid = frame.dropna(subset=["signal", "size", "adv20_amount"])
    for _, group in valid.groupby("date", sort=False):
        bucket_total = min(size_bucket_count, len(group))
        if bucket_total < 1:
            continue
        size_order = group["size"].rank(method="first")
        buckets = pd.qcut(size_order, q=bucket_total, labels=False, duplicates="drop")
        for _, bucket_group in group.groupby(buckets, sort=False):
            liquid = bucket_group[
                bucket_group["adv20_amount"].rank(method="average", pct=True) >= min_liquidity_rank
            ]
            if liquid.empty:
                continue
            ranked = liquid["signal"].rank(method="average", pct=True)
            result.loc[liquid.index] = ranked.to_numpy(dtype=float)
    return result


def _adv_blend_bucket_rank(
    signal: pd.Series,
    circ_mv: pd.Series,
    adv20_amount: pd.Series,
    dates: pd.Series,
    *,
    size_bucket_count: int = 5,
    signal_weight: float = 0.55,
) -> pd.Series:
    frame = pd.DataFrame(
        {
            "signal": pd.to_numeric(signal, errors="coerce"),
            "size": _safe_log(circ_mv),
            "adv20_amount": pd.to_numeric(adv20_amount, errors="coerce"),
            "date": dates,
        }
    )
    result = pd.Series(np.nan, index=frame.index, dtype=float)
    valid = frame.dropna(subset=["signal", "size", "adv20_amount"])
    liquidity_weight = 1.0 - signal_weight
    for _, group in valid.groupby("date", sort=False):
        bucket_total = min(size_bucket_count, len(group))
        if bucket_total < 1:
            continue
        size_order = group["size"].rank(method="first")
        buckets = pd.qcut(size_order, q=bucket_total, labels=False, duplicates="drop")
        for _, bucket_group in group.groupby(buckets, sort=False):
            signal_rank = bucket_group["signal"].rank(method="average", pct=True)
            liquidity_rank = bucket_group["adv20_amount"].rank(method="average", pct=True)
            blended = signal_weight * signal_rank + liquidity_weight * liquidity_rank
            result.loc[bucket_group.index] = blended.rank(method="average", pct=True).to_numpy(dtype=float)
    return result


def _safe_log(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return np.log(numeric.where(numeric > 0)).replace([np.inf, -np.inf], np.nan)


def _factor_frame(inputs: pd.DataFrame, name: str, values: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": inputs["date"].to_numpy(),
            "asset_id": inputs["asset_id"].to_numpy(),
            "market": inputs["market"].to_numpy(),
            "factor_name": name,
            "factor_value": values.to_numpy(),
            "lookback_window": 20,
        }
    )
