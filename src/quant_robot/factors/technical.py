from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


_COMPOSITE_FACTOR_SPECS: dict[str, tuple[str, ...]] = {
    "trend_resilience": ("momentum", "drawdown_resilience", "liquidity_resilience"),
    "risk_confirmed_momentum": ("risk_adjusted_momentum", "drawdown_resilience", "amount_stability"),
    "defensive_reversal": ("reversal", "low_downside_volatility", "liquidity_resilience"),
    "liquidity_confirmed_breakout": ("momentum", "amount_stability", "liquidity_resilience"),
}


def compute_basic_factors(bars: pd.DataFrame, windows: tuple[int, ...] = (5, 20)) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "volume", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing columns for factor calculation: {', '.join(missing)}")

    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame.sort_values(["asset_id", "date"])
    pieces: list[pd.DataFrame] = []
    for _, group in frame.groupby("asset_id", sort=False):
        enriched = group.copy()
        enriched["_return"] = enriched["adj_close"].pct_change()
        for window in windows:
            pieces.extend(
                [
                    _factor_frame(enriched, f"momentum_{window}", _momentum(enriched["adj_close"], window), window),
                    _factor_frame(
                        enriched,
                        f"risk_adjusted_momentum_{window}",
                        _risk_adjusted_momentum(enriched["adj_close"], enriched["_return"], window),
                        window,
                    ),
                    _factor_frame(enriched, f"reversal_{window}", -_momentum(enriched["adj_close"], window), window),
                    _factor_frame(enriched, f"volatility_{window}", enriched["_return"].rolling(window).std(ddof=0), window),
                    _factor_frame(
                        enriched,
                        f"low_volatility_{window}",
                        -enriched["_return"].rolling(window).std(ddof=0),
                        window,
                    ),
                    _factor_frame(
                        enriched,
                        f"low_downside_volatility_{window}",
                        _low_downside_volatility(enriched["_return"], window),
                        window,
                    ),
                    _factor_frame(
                        enriched,
                        f"drawdown_resilience_{window}",
                        _drawdown_resilience(enriched["adj_close"], window),
                        window,
                    ),
                    _factor_frame(
                        enriched,
                        f"volume_change_{window}",
                        enriched["volume"] / enriched["volume"].rolling(window).mean() - 1.0,
                        window,
                    ),
                    _factor_frame(enriched, f"liquidity_{window}", _amihud(enriched["_return"], enriched["amount"]), window),
                    _factor_frame(
                        enriched,
                        f"liquidity_resilience_{window}",
                        -_amihud(enriched["_return"], enriched["amount"]),
                        window,
                    ),
                    _factor_frame(
                        enriched,
                        f"amount_stability_{window}",
                        _amount_stability(enriched["amount"], window),
                        window,
                    ),
                ]
            )
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    base = pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS]
    composites = _composite_factors(base)
    factors = pd.concat([base, composites], ignore_index=True) if not composites.empty else base
    return factors[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _momentum(price: pd.Series, window: int) -> pd.Series:
    return price / price.shift(window) - 1.0


def _risk_adjusted_momentum(price: pd.Series, returns: pd.Series, window: int) -> pd.Series:
    volatility = returns.rolling(window).std(ddof=0).replace(0, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        value = _momentum(price, window) / volatility
    return value.replace([np.inf, -np.inf], np.nan)


def _low_downside_volatility(returns: pd.Series, window: int) -> pd.Series:
    downside = returns.clip(upper=0.0)
    return -downside.rolling(window).std(ddof=0)


def _drawdown_resilience(price: pd.Series, window: int) -> pd.Series:
    rolling_high = price.rolling(window).max()
    with np.errstate(divide="ignore", invalid="ignore"):
        value = price / rolling_high - 1.0
    return value.replace([np.inf, -np.inf], np.nan)


def _amihud(returns: pd.Series, amount: pd.Series) -> pd.Series:
    with np.errstate(divide="ignore", invalid="ignore"):
        value = returns.abs() / amount.replace(0, np.nan)
    return value.replace([np.inf, -np.inf], np.nan)


def _amount_stability(amount: pd.Series, window: int) -> pd.Series:
    amount_change = amount.replace(0, np.nan).pct_change()
    return -amount_change.rolling(window).std(ddof=0)


def _composite_factors(factors: pd.DataFrame) -> pd.DataFrame:
    if factors.empty:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    rows = []
    for window in sorted(pd.to_numeric(factors["lookback_window"], errors="coerce").dropna().astype(int).unique()):
        window_factors = factors[factors["lookback_window"].astype(int) == window]
        for composite_name, components in _COMPOSITE_FACTOR_SPECS.items():
            component_names = [f"{component}_{window}" for component in components]
            wide = _factor_wide_frame(window_factors, component_names)
            if wide.empty:
                continue
            ranked = wide.groupby(["date", "market"], group_keys=False)[component_names].rank(
                method="average",
                pct=True,
            )
            output = wide[["date", "asset_id", "market"]].copy()
            output["factor_name"] = f"{composite_name}_{window}"
            output["factor_value"] = ranked.mean(axis=1, skipna=False)
            output["lookback_window"] = window
            rows.append(output)
    if not rows:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(rows, ignore_index=True)[FACTOR_COLUMNS]


def _factor_wide_frame(factors: pd.DataFrame, component_names: list[str]) -> pd.DataFrame:
    frame = factors[factors["factor_name"].isin(component_names)]
    if frame.empty or set(component_names) - set(frame["factor_name"]):
        return pd.DataFrame()
    wide = frame.pivot_table(
        index=["date", "asset_id", "market"],
        columns="factor_name",
        values="factor_value",
        aggfunc="first",
    ).reset_index()
    if set(component_names) - set(wide.columns):
        return pd.DataFrame()
    return wide.dropna(subset=component_names).reset_index(drop=True)


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
