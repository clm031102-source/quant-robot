from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


PUBLIC_TREND_STRENGTH_STATE_FACTOR_NAMES = (
    "adx_trend_strength_exhaustion_reversal_14_20",
    "adx_choppiness_mean_reversion_quality_14_20",
    "kama_efficiency_trend_decay_10_30",
    "aroon_range_exhaustion_reversal_25_20",
    "williams_range_failure_reversal_14_20",
    "trend_strength_state_residual_composite_20",
)


def compute_public_trend_strength_state_factors(
    bars: pd.DataFrame,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "high", "low", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(
            "Bars are missing columns for public trend-strength-state factor calculation: "
            + ", ".join(missing)
        )
    requested = _resolve_requested_factor_names(factor_names)

    frame = _feature_frame(bars)
    mask = frame["state_tradeable"].fillna(False)
    range_exhaustion = 1.0 - pd.to_numeric(frame["range_position_20"], errors="coerce")
    aroon_spread = pd.to_numeric(frame["aroon_down_25"], errors="coerce") - pd.to_numeric(
        frame["aroon_up_25"],
        errors="coerce",
    )
    williams_oversold = -pd.to_numeric(frame["williams_r_14"], errors="coerce")

    adx_exhaustion = (
        0.55 * _cs_z(frame, frame["adx_14"])
        + 0.35 * _cs_z(frame, range_exhaustion)
        - 0.10 * _cs_z(frame, frame["momentum_20"])
    ).where(mask)
    choppiness_quality = (
        _cs_z(frame, frame["choppiness_20"])
        - 0.50 * _cs_z(frame, frame["downside_vol_20"])
        - 0.25 * _cs_z(frame, pd.to_numeric(frame["momentum_20"], errors="coerce").abs())
    ).where(mask)
    kama_decay = (
        _cs_z(frame, frame["kama_efficiency_decay_10_30"])
        - 0.25 * _cs_z(frame, frame["downside_vol_20"])
    ).where(mask)
    aroon_exhaustion = (
        _cs_z(frame, aroon_spread)
        + 0.35 * _cs_z(frame, range_exhaustion)
    ).where(mask)
    williams_reversal = (
        _cs_z(frame, williams_oversold)
        - 0.25 * _cs_z(frame, frame["downside_vol_20"])
    ).where(mask)
    composite = pd.concat(
        [adx_exhaustion, choppiness_quality, kama_decay, aroon_exhaustion, williams_reversal],
        axis=1,
    ).mean(axis=1, skipna=True).where(mask)

    values_by_name = {
        "adx_trend_strength_exhaustion_reversal_14_20": adx_exhaustion,
        "adx_choppiness_mean_reversion_quality_14_20": choppiness_quality,
        "kama_efficiency_trend_decay_10_30": kama_decay,
        "aroon_range_exhaustion_reversal_25_20": aroon_exhaustion,
        "williams_range_failure_reversal_14_20": williams_reversal,
        "trend_strength_state_residual_composite_20": composite,
    }
    pieces = [_factor_frame(frame, name, values_by_name[name]) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return PUBLIC_TREND_STRENGTH_STATE_FACTOR_NAMES
    supported = set(PUBLIC_TREND_STRENGTH_STATE_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported public trend-strength-state factor_names: {', '.join(unknown)}")
    return factor_names


def _feature_frame(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    pieces: list[pd.DataFrame] = []
    for _, group in frame.groupby("asset_id", sort=False):
        item = group.copy()
        price = pd.to_numeric(item["adj_close"], errors="coerce")
        high = pd.to_numeric(item["high"], errors="coerce")
        low = pd.to_numeric(item["low"], errors="coerce")
        amount = pd.to_numeric(item["amount"], errors="coerce")
        returns = price.pct_change()
        true_range = _true_range(high, low, price)
        rolling_high_14 = high.rolling(14).max()
        rolling_low_14 = low.rolling(14).min()
        rolling_high_20 = high.rolling(20).max()
        rolling_low_20 = low.rolling(20).min()

        item["return_1d"] = returns
        item["momentum_20"] = price.pct_change(20)
        item["downside_vol_20"] = returns.clip(upper=0.0).rolling(20).std(ddof=0)
        item["amount_20"] = amount.rolling(20).mean()
        item["adx_14"] = _adx(high, low, price, 14)
        item["choppiness_20"] = _choppiness(true_range, rolling_high_20, rolling_low_20, 20)
        item["kama_efficiency_10"] = _efficiency_ratio(price, 10)
        item["kama_efficiency_decay_10_30"] = item["kama_efficiency_10"].rolling(30).max() - item["kama_efficiency_10"]
        item["aroon_up_25"] = _aroon(high, 25, find_high=True)
        item["aroon_down_25"] = _aroon(low, 25, find_high=False)
        item["williams_r_14"] = -100.0 * _safe_div(rolling_high_14 - price, rolling_high_14 - rolling_low_14)
        item["range_position_20"] = _safe_div(price - rolling_low_20, rolling_high_20 - rolling_low_20)
        pieces.append(item)

    out = pd.concat(pieces, ignore_index=True)
    out["amount_20_rank"] = _cs_rank(out, out["amount_20"])
    out["state_tradeable"] = (
        (out["amount_20_rank"] > 0.25)
        & (pd.to_numeric(out["return_1d"], errors="coerce").abs() <= 0.50)
    )
    return out


def _adx(high: pd.Series, low: pd.Series, price: pd.Series, window: int) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0.0), up_move, 0.0),
        index=high.index,
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0.0), down_move, 0.0),
        index=high.index,
    )
    true_range_sum = _true_range(high, low, price).rolling(window).sum()
    plus_di = 100.0 * _safe_div(plus_dm.rolling(window).sum(), true_range_sum)
    minus_di = 100.0 * _safe_div(minus_dm.rolling(window).sum(), true_range_sum)
    dx = 100.0 * _safe_div((plus_di - minus_di).abs(), plus_di + minus_di)
    return dx.rolling(window).mean()


def _choppiness(true_range: pd.Series, rolling_high: pd.Series, rolling_low: pd.Series, window: int) -> pd.Series:
    ratio = _safe_div(true_range.rolling(window).sum(), rolling_high - rolling_low)
    with np.errstate(divide="ignore", invalid="ignore"):
        value = 100.0 * np.log10(ratio) / np.log10(float(window))
    return value.replace([np.inf, -np.inf], np.nan)


def _efficiency_ratio(price: pd.Series, window: int) -> pd.Series:
    direction = (price - price.shift(window)).abs()
    volatility = price.diff().abs().rolling(window).sum()
    return _safe_div(direction, volatility).clip(lower=0.0, upper=1.0)


def _aroon(values: pd.Series, window: int, *, find_high: bool) -> pd.Series:
    def score(item: np.ndarray) -> float:
        position = int(np.nanargmax(item) if find_high else np.nanargmin(item))
        return 100.0 * float(position + 1) / float(window)

    return values.rolling(window).apply(score, raw=True)


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


def _safe_div(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    with np.errstate(divide="ignore", invalid="ignore"):
        value = numerator / denominator.replace(0.0, np.nan)
    return value.replace([np.inf, -np.inf], np.nan)


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
            "lookback_window": 30 if "kama" in name else 20,
        }
    )
