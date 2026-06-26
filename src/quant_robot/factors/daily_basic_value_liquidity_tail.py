from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


DAILY_BASIC_VALUE_LIQUIDITY_TAIL_FACTOR_NAMES = (
    "value_liquid_low_tail_20",
    "dividend_value_liquid_low_tail_20",
    "value_low_turnover_low_tail_20",
)


def compute_daily_basic_value_liquidity_tail_factors(
    bars: pd.DataFrame,
    daily_basic_inputs: pd.DataFrame,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    _require_columns(
        bars,
        ["date", "asset_id", "market", "amount", "adj_close", "high", "low"],
        "bars",
    )
    _require_columns(
        daily_basic_inputs,
        [
            "date",
            "asset_id",
            "market",
            "turnover_rate",
            "turnover_rate_f",
            "volume_ratio",
            "pe_ttm",
            "pb",
            "ps_ttm",
            "dv_ttm",
            "total_mv",
            "circ_mv",
        ],
        "daily-basic inputs",
    )
    requested = _resolve_requested_factor_names(factor_names)
    frame = _build_research_frame(bars, daily_basic_inputs)
    builders = {
        "value_liquid_low_tail_20": lambda: _value_liquid_low_tail(frame),
        "dividend_value_liquid_low_tail_20": lambda: _dividend_value_liquid_low_tail(frame),
        "value_low_turnover_low_tail_20": lambda: _value_low_turnover_low_tail(frame),
    }
    pieces = [_factor_frame(frame, name, builders[name]()) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return DAILY_BASIC_VALUE_LIQUIDITY_TAIL_FACTOR_NAMES
    supported = set(DAILY_BASIC_VALUE_LIQUIDITY_TAIL_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported daily-basic value liquidity tail factor_names: {', '.join(unknown)}")
    return factor_names


def _build_research_frame(bars: pd.DataFrame, daily_basic_inputs: pd.DataFrame) -> pd.DataFrame:
    bar_cols = ["date", "asset_id", "market", "amount", "adj_close", "high", "low"]
    input_cols = [
        "date",
        "asset_id",
        "market",
        "turnover_rate",
        "turnover_rate_f",
        "volume_ratio",
        "pe_ttm",
        "pb",
        "ps_ttm",
        "dv_ttm",
        "total_mv",
        "circ_mv",
    ]
    bar_frame = bars.loc[:, bar_cols].copy()
    input_frame = daily_basic_inputs.loc[:, input_cols].copy()
    bar_frame["date"] = pd.to_datetime(bar_frame["date"]).dt.date
    input_frame["date"] = pd.to_datetime(input_frame["date"]).dt.date
    frame = bar_frame.merge(input_frame, on=["date", "asset_id", "market"], how="left")
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    _add_price_liquidity_features(frame)
    _add_tradeable_gate(frame)
    return frame


def _add_price_liquidity_features(frame: pd.DataFrame) -> None:
    frame["amount"] = _numeric(frame, "amount")
    frame["amount_rank"] = _cs_rank(frame, frame["amount"])
    pieces = []
    for _, group in frame.groupby("asset_id", sort=False):
        item = group.copy()
        close = _numeric(item, "adj_close")
        high = _numeric(item, "high")
        low = _numeric(item, "low")
        returns = close.pct_change()
        low20 = close.rolling(20, min_periods=5).min()
        high20 = close.rolling(20, min_periods=5).max()
        item["return_1"] = returns
        item["adv20_amount"] = item["amount"].rolling(20, min_periods=5).mean()
        item["range_position_20"] = (close - low20) / (high20 - low20).replace(0, np.nan)
        item["downside_vol_20"] = returns.clip(upper=0).rolling(20, min_periods=5).std(ddof=0)
        item["hl_range_20"] = ((high / low.replace(0, np.nan)) - 1.0).rolling(20, min_periods=5).mean()
        pieces.append(item[["return_1", "adv20_amount", "range_position_20", "downside_vol_20", "hl_range_20"]])
    features = pd.concat(pieces).sort_index()
    for column in features.columns:
        frame[column] = pd.to_numeric(features[column], errors="coerce").replace([np.inf, -np.inf], np.nan)

    frame["adv20_rank"] = _cs_rank(frame, frame["adv20_amount"])
    frame["turnover_rank"] = _cs_rank(frame, _numeric(frame, "turnover_rate"))
    frame["downside_vol_rank"] = _cs_rank(frame, frame["downside_vol_20"])


def _add_tradeable_gate(frame: pd.DataFrame) -> None:
    frame["value_tail_tradeable"] = (
        (frame["adv20_rank"] > 0.20)
        & (frame["amount_rank"] > 0.20)
        & (frame["turnover_rank"] <= 1.0)
        & (frame["downside_vol_rank"] <= 0.80)
        & (frame["range_position_20"] >= 0.15)
        & (frame["return_1"].abs() <= 0.35)
    )


def _value_liquid_low_tail(frame: pd.DataFrame) -> pd.Series:
    value = _value_score(frame)
    liquidity = _liquidity_score(frame)
    tail = _tail_score(frame)
    return _size_bucket_rank(frame, value + 0.60 * liquidity + tail)


def _dividend_value_liquid_low_tail(frame: pd.DataFrame) -> pd.Series:
    value = _value_score(frame)
    dividend = _cs_z(frame, _numeric(frame, "dv_ttm"))
    liquidity = _liquidity_score(frame)
    tail = _tail_score(frame)
    return _size_bucket_rank(frame, value + dividend + 0.50 * liquidity + tail)


def _value_low_turnover_low_tail(frame: pd.DataFrame) -> pd.Series:
    value = _value_score(frame)
    turnover_band = -(_numeric(frame, "turnover_rank") - 0.30).abs()
    low_turnover = _cs_z(frame, turnover_band)
    tail = _tail_score(frame)
    return _size_bucket_rank(frame, value + low_turnover + tail)


def _value_score(frame: pd.DataFrame) -> pd.Series:
    return (
        _cs_z(frame, _safe_inverse(frame, "pb"))
        + _cs_z(frame, _safe_inverse(frame, "pe_ttm"))
        + 0.50 * _cs_z(frame, _safe_inverse(frame, "ps_ttm"))
    )


def _liquidity_score(frame: pd.DataFrame) -> pd.Series:
    mid_liquidity = -(_numeric(frame, "adv20_rank") - 0.65).abs()
    return _cs_z(frame, mid_liquidity)


def _tail_score(frame: pd.DataFrame) -> pd.Series:
    low_downside = _cs_z(frame, -_numeric(frame, "downside_vol_20")).fillna(0.0)
    range_position = _cs_z(frame, _numeric(frame, "range_position_20")).fillna(0.0)
    low_intraday_range = _cs_z(frame, -_numeric(frame, "hl_range_20")).fillna(0.0)
    return low_downside + 0.50 * range_position + 0.25 * low_intraday_range


def _size_bucket_rank(
    frame: pd.DataFrame,
    score: pd.Series,
    *,
    size_bucket_count: int = 5,
) -> pd.Series:
    work = pd.DataFrame(
        {
            "score": pd.to_numeric(score, errors="coerce"),
            "size": _safe_log(frame["circ_mv"]),
            "date": frame["date"],
            "market": frame["market"],
            "tradeable": frame["value_tail_tradeable"].fillna(False),
        }
    )
    result = pd.Series(np.nan, index=frame.index, dtype=float)
    valid = work.dropna(subset=["score", "size"])
    valid = valid[valid["tradeable"]]
    for _, group in valid.groupby(["date", "market"], sort=False):
        bucket_total = min(size_bucket_count, len(group))
        if bucket_total < 1:
            continue
        size_order = group["size"].rank(method="first")
        buckets = pd.qcut(size_order, q=bucket_total, labels=False, duplicates="drop")
        for _, bucket_group in group.groupby(buckets, sort=False):
            ranked = bucket_group["score"].rank(method="average", pct=True)
            result.loc[bucket_group.index] = ranked.to_numpy(dtype=float)
    return result


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce")


def _safe_inverse(frame: pd.DataFrame, column: str) -> pd.Series:
    values = _numeric(frame, column)
    return (1.0 / values.where(values > 0)).replace([np.inf, -np.inf], np.nan)


def _safe_log(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return np.log(numeric.where(numeric > 0)).replace([np.inf, -np.inf], np.nan)


def _cs_rank(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce").groupby([frame["date"], frame["market"]], sort=False).rank(pct=True)


def _cs_z(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric_values = pd.to_numeric(values, errors="coerce")
    grouped = numeric_values.groupby([frame["date"], frame["market"]], sort=False)
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return ((numeric_values - mean) / std.where(std > 1e-12)).replace([np.inf, -np.inf], np.nan)


def _factor_frame(frame: pd.DataFrame, name: str, values: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": frame["date"].to_numpy(),
            "asset_id": frame["asset_id"].to_numpy(),
            "market": frame["market"].to_numpy(),
            "factor_name": name,
            "factor_value": values.to_numpy(),
            "lookback_window": 20,
        }
    )


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} are missing columns: {', '.join(missing)}")
