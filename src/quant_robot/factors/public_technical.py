from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


PUBLIC_TECHNICAL_FACTOR_NAMES = (
    "rsi_reversal_14",
    "bollinger_reversal_20",
    "donchian_position_20",
    "macd_histogram_12_26_9",
)


def compute_public_technical_factors(
    bars: pd.DataFrame,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "high", "low"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing columns for public technical factor calculation: {', '.join(missing)}")
    requested = _resolve_requested_factor_names(factor_names)

    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame.sort_values(["asset_id", "date"])
    pieces: list[pd.DataFrame] = []
    for _, group in frame.groupby("asset_id", sort=False):
        enriched = group.copy()
        price = pd.to_numeric(enriched["adj_close"], errors="coerce")
        high = pd.to_numeric(enriched["high"], errors="coerce")
        low = pd.to_numeric(enriched["low"], errors="coerce")
        if "rsi_reversal_14" in requested:
            pieces.append(_factor_frame(enriched, "rsi_reversal_14", 100.0 - _rsi(price, 14), 14))
        if "bollinger_reversal_20" in requested:
            pieces.append(_factor_frame(enriched, "bollinger_reversal_20", _bollinger_reversal(price, 20), 20))
        if "donchian_position_20" in requested:
            pieces.append(_factor_frame(enriched, "donchian_position_20", _donchian_position(price, high, low, 20), 20))
        if "macd_histogram_12_26_9" in requested:
            pieces.append(_factor_frame(enriched, "macd_histogram_12_26_9", _macd_histogram(price, 12, 26, 9), 26))
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return PUBLIC_TECHNICAL_FACTOR_NAMES
    supported = set(PUBLIC_TECHNICAL_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported public technical factor_names: {', '.join(unknown)}")
    return factor_names


def _rsi(price: pd.Series, window: int) -> pd.Series:
    delta = price.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = avg_gain / avg_loss.replace(0.0, np.nan)
        rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.mask((avg_loss == 0.0) & (avg_gain > 0.0), 100.0)
    rsi = rsi.mask((avg_gain == 0.0) & (avg_loss > 0.0), 0.0)
    rsi = rsi.mask((avg_gain == 0.0) & (avg_loss == 0.0), 50.0)
    return rsi


def _bollinger_reversal(price: pd.Series, window: int) -> pd.Series:
    center = price.rolling(window).mean()
    width = price.rolling(window).std(ddof=0).replace(0.0, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        value = -((price - center) / width)
    return value.replace([np.inf, -np.inf], np.nan)


def _donchian_position(price: pd.Series, high: pd.Series, low: pd.Series, window: int) -> pd.Series:
    upper = high.rolling(window).max()
    lower = low.rolling(window).min()
    width = (upper - lower).replace(0.0, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        value = (price - lower) / width
    return value.replace([np.inf, -np.inf], np.nan).clip(lower=0.0, upper=1.0)


def _macd_histogram(price: pd.Series, fast: int, slow: int, signal: int) -> pd.Series:
    fast_ema = price.ewm(span=fast, adjust=False, min_periods=fast).mean()
    slow_ema = price.ewm(span=slow, adjust=False, min_periods=slow).mean()
    macd = fast_ema - slow_ema
    signal_line = macd.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return macd - signal_line


def _factor_frame(group: pd.DataFrame, name: str, values: pd.Series, window: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": group["date"].to_numpy(),
            "asset_id": group["asset_id"].to_numpy(),
            "market": group["market"].to_numpy(),
            "factor_name": name,
            "factor_value": values.to_numpy(),
            "lookback_window": window,
        }
    )
