from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


PUBLIC_TREND_VOLUME_FACTOR_NAMES = (
    "supertrend_volume_confirmed_10_3_20",
    "smart_money_trend_20",
    "obv_breakout_low_tail_20",
    "anti_supertrend_volume_confirmed_10_3_20",
    "anti_smart_money_trend_20",
    "anti_obv_breakout_low_tail_20",
)


def compute_public_trend_volume_factors(
    bars: pd.DataFrame,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "high", "low", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing columns for public trend-volume factor calculation: {', '.join(missing)}")
    requested = _resolve_requested_factor_names(factor_names)

    frame = _feature_frame(bars)
    supertrend_volume = _supertrend_volume_score(frame)
    smart_money_trend = _smart_money_trend_score(frame)
    obv_breakout = _obv_breakout_score(frame)
    values_by_name = {
        "supertrend_volume_confirmed_10_3_20": supertrend_volume,
        "smart_money_trend_20": smart_money_trend,
        "obv_breakout_low_tail_20": obv_breakout,
        "anti_supertrend_volume_confirmed_10_3_20": -supertrend_volume,
        "anti_smart_money_trend_20": -smart_money_trend,
        "anti_obv_breakout_low_tail_20": -obv_breakout,
    }
    pieces = [_factor_frame(frame, name, values_by_name[name]) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return PUBLIC_TREND_VOLUME_FACTOR_NAMES
    supported = set(PUBLIC_TREND_VOLUME_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported public trend-volume factor_names: {', '.join(unknown)}")
    return factor_names


def _feature_frame(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    pieces = []
    for _, group in frame.groupby("asset_id", sort=False):
        item = group.copy()
        price = pd.to_numeric(item["adj_close"], errors="coerce")
        high = pd.to_numeric(item["high"], errors="coerce")
        low = pd.to_numeric(item["low"], errors="coerce")
        amount = pd.to_numeric(item["amount"], errors="coerce")
        returns = price.pct_change()
        rolling_high_10 = high.rolling(10).max()
        rolling_low_10 = low.rolling(10).min()
        rolling_high_20 = high.rolling(20).max()
        rolling_low_20 = low.rolling(20).min()
        atr_10 = _true_range(high, low, price).rolling(10).mean()
        channel_mid_10 = (rolling_high_10 + rolling_low_10) / 2.0
        supertrend_floor = channel_mid_10 - 3.0 * atr_10
        signed_amount = np.sign(returns.fillna(0.0)) * amount
        positive_flow = amount.where(returns > 0.0, 0.0).rolling(20).sum()
        negative_flow = amount.where(returns < 0.0, 0.0).rolling(20).sum()
        total_directional_flow = (positive_flow + negative_flow).replace(0.0, np.nan)
        obv = signed_amount.fillna(0.0).cumsum()
        item["return_1d"] = returns
        item["momentum_20"] = price.pct_change(20)
        item["adv20_amount"] = amount.rolling(20).mean()
        item["amount_trend_20"] = (amount.rolling(5).mean() / amount.rolling(20).mean().replace(0.0, np.nan)) - 1.0
        item["smart_money_pressure_20"] = (positive_flow - negative_flow) / total_directional_flow
        item["obv_slope_20"] = (obv - obv.shift(20)) / amount.rolling(20).sum().replace(0.0, np.nan)
        item["downside_vol_20"] = returns.clip(upper=0.0).rolling(20).std(ddof=0)
        item["hl_range_20"] = ((high / low.replace(0.0, np.nan)) - 1.0).rolling(20).mean()
        item["donchian_position_20"] = (price - rolling_low_20) / (rolling_high_20 - rolling_low_20).replace(0.0, np.nan)
        item["supertrend_distance_10_3"] = (price - supertrend_floor) / atr_10.replace(0.0, np.nan)
        item["supertrend_confirmed_10_3_20"] = (price > supertrend_floor) & (price > price.rolling(20).mean())
        pieces.append(item)
    out = pd.concat(pieces, ignore_index=True)
    out["adv20_rank"] = _cs_rank(out, out["adv20_amount"])
    out["downside_vol_rank"] = _cs_rank(out, out["downside_vol_20"])
    out["hl_range_rank"] = _cs_rank(out, out["hl_range_20"])
    out["log_adv20"] = np.log(pd.to_numeric(out["adv20_amount"], errors="coerce").where(out["adv20_amount"] > 0.0))
    hl_range = pd.to_numeric(out["hl_range_20"], errors="coerce")
    out["trend_volume_tradeable"] = (
        (out["adv20_rank"] >= 0.50)
        & (out["downside_vol_rank"] <= 0.75)
        & ((out["hl_range_rank"] <= 0.85) | (hl_range <= 0.08))
        & (pd.to_numeric(out["return_1d"], errors="coerce").abs() <= 0.50)
    )
    return out


def _supertrend_volume_score(frame: pd.DataFrame) -> pd.Series:
    value = (
        0.40 * _cs_z(frame, frame["supertrend_distance_10_3"])
        + 0.30 * _cs_z(frame, frame["smart_money_pressure_20"])
        + 0.20 * _cs_z(frame, frame["amount_trend_20"])
        + 0.10 * _cs_z(frame, frame["log_adv20"])
    )
    mask = frame["trend_volume_tradeable"].fillna(False) & frame["supertrend_confirmed_10_3_20"].fillna(False)
    return value.where(mask)


def _smart_money_trend_score(frame: pd.DataFrame) -> pd.Series:
    value = (
        0.45 * _cs_z(frame, frame["smart_money_pressure_20"])
        + 0.25 * _cs_z(frame, frame["amount_trend_20"])
        + 0.20 * _cs_z(frame, frame["momentum_20"])
        - 0.10 * _cs_z(frame, frame["downside_vol_20"])
    )
    mask = frame["trend_volume_tradeable"].fillna(False) & (pd.to_numeric(frame["momentum_20"], errors="coerce") > 0.0)
    return value.where(mask)


def _obv_breakout_score(frame: pd.DataFrame) -> pd.Series:
    value = (
        0.40 * _cs_z(frame, frame["obv_slope_20"])
        + 0.30 * _cs_z(frame, frame["donchian_position_20"])
        + 0.20 * _cs_z(frame, frame["amount_trend_20"])
        - 0.10 * _cs_z(frame, frame["downside_vol_20"])
    )
    mask = frame["trend_volume_tradeable"].fillna(False) & (pd.to_numeric(frame["donchian_position_20"], errors="coerce") >= 0.60)
    return value.where(mask)


def _true_range(high: pd.Series, low: pd.Series, price: pd.Series) -> pd.Series:
    previous_price = price.shift(1)
    ranges = pd.concat(
        [
            high - low,
            (high - previous_price).abs(),
            (low - previous_price).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def _cs_rank(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.groupby([frame["date"], frame["market"]], sort=False).rank(pct=True)


def _cs_z(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    grouped = numeric.groupby([frame["date"], frame["market"]], sort=False)
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return ((numeric - mean) / std.where(std > 1e-12)).replace([np.inf, -np.inf], np.nan)


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
