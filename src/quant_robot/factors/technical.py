from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


TECHNICAL_FACTOR_PREFIXES = (
    "momentum",
    "risk_adjusted_momentum",
    "reversal",
    "volatility",
    "low_volatility",
    "volume_change",
    "liquidity",
    "high_liquidity",
)


def technical_factor_names(windows: tuple[int, ...]) -> tuple[str, ...]:
    return tuple(f"{prefix}_{window}" for window in windows for prefix in TECHNICAL_FACTOR_PREFIXES)


def compute_basic_factors(
    bars: pd.DataFrame,
    windows: tuple[int, ...] = (5, 20),
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "volume", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing columns for factor calculation: {', '.join(missing)}")
    requested = _resolve_requested_factor_names(technical_factor_names(windows), factor_names, "technical")

    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame.sort_values(["asset_id", "date"])
    pieces: list[pd.DataFrame] = []
    for _, group in frame.groupby("asset_id", sort=False):
        enriched = group.copy()
        enriched["_return"] = enriched["adj_close"].pct_change()
        for window in windows:
            momentum_name = f"momentum_{window}"
            risk_adjusted_name = f"risk_adjusted_momentum_{window}"
            reversal_name = f"reversal_{window}"
            volatility_name = f"volatility_{window}"
            low_volatility_name = f"low_volatility_{window}"
            volume_change_name = f"volume_change_{window}"
            liquidity_name = f"liquidity_{window}"
            high_liquidity_name = f"high_liquidity_{window}"
            if momentum_name in requested:
                pieces.append(_factor_frame(enriched, momentum_name, _momentum(enriched["adj_close"], window), window))
            if risk_adjusted_name in requested:
                pieces.append(
                    _factor_frame(
                        enriched,
                        risk_adjusted_name,
                        _risk_adjusted_momentum(enriched["adj_close"], enriched["_return"], window),
                        window,
                    )
                )
            if reversal_name in requested:
                pieces.append(_factor_frame(enriched, reversal_name, -_momentum(enriched["adj_close"], window), window))
            if volatility_name in requested:
                volatility = enriched["_return"].rolling(window).std(ddof=0)
                pieces.append(_factor_frame(enriched, volatility_name, volatility, window))
            if low_volatility_name in requested:
                volatility = enriched["_return"].rolling(window).std(ddof=0)
                pieces.append(_factor_frame(enriched, low_volatility_name, -volatility, window))
            if volume_change_name in requested:
                pieces.append(
                    _factor_frame(
                        enriched,
                        volume_change_name,
                        enriched["volume"] / enriched["volume"].rolling(window).mean() - 1.0,
                        window,
                    )
                )
            if liquidity_name in requested:
                liquidity = _amihud(enriched["_return"], enriched["amount"]).rolling(window).mean()
                pieces.append(_factor_frame(enriched, liquidity_name, liquidity, window))
            if high_liquidity_name in requested:
                liquidity = _amihud(enriched["_return"], enriched["amount"]).rolling(window).mean()
                pieces.append(
                    _factor_frame(enriched, high_liquidity_name, -liquidity, window)
                )
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(
    supported: tuple[str, ...],
    factor_names: tuple[str, ...] | None,
    label: str,
) -> tuple[str, ...]:
    if factor_names is None:
        return supported
    supported_set = set(supported)
    unknown = [name for name in factor_names if name not in supported_set]
    if unknown:
        raise ValueError(f"Unsupported {label} factor_names: {', '.join(unknown)}")
    return factor_names


def _momentum(price: pd.Series, window: int) -> pd.Series:
    return price / price.shift(window) - 1.0


def _risk_adjusted_momentum(price: pd.Series, returns: pd.Series, window: int) -> pd.Series:
    volatility = returns.rolling(window).std(ddof=0).replace(0, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        value = _momentum(price, window) / volatility
    return value.replace([np.inf, -np.inf], np.nan)


def _amihud(returns: pd.Series, amount: pd.Series) -> pd.Series:
    with np.errstate(divide="ignore", invalid="ignore"):
        value = returns.abs() / amount.replace(0, np.nan)
    return value.replace([np.inf, -np.inf], np.nan)


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
