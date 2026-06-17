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

_LIQUIDITY_GATED_FACTOR_SPECS: dict[str, str] = {
    "liquid_market_relative_strength": "market_relative_strength",
    "liquid_crash_recovery": "crash_recovery",
    "liquid_recovery_quality": "recovery_quality",
    "liquid_demand_pressure": "demand_pressure",
    "liquid_quiet_accumulation": "quiet_accumulation",
}

_STATE_ADAPTIVE_COMPONENTS = (
    "momentum",
    "market_relative_strength",
    "drawdown_resilience",
    "low_downside_volatility",
    "liquidity_resilience",
    "crash_recovery",
    "recovery_quality",
)


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
                    _factor_frame(
                        enriched,
                        f"average_amount_{window}",
                        _average_amount(enriched["amount"], window),
                        window,
                    ),
                    _factor_frame(
                        enriched,
                        f"crash_recovery_{window}",
                        _crash_recovery(enriched["adj_close"], window),
                        window,
                    ),
                    _factor_frame(
                        enriched,
                        f"recovery_quality_{window}",
                        _recovery_quality(enriched["adj_close"], enriched["_return"], window),
                        window,
                    ),
                    _factor_frame(
                        enriched,
                        f"demand_pressure_{window}",
                        _demand_pressure(enriched["adj_close"], enriched["amount"], window),
                        window,
                    ),
                    _factor_frame(
                        enriched,
                        f"quiet_accumulation_{window}",
                        _quiet_accumulation(enriched["_return"], enriched["amount"], window),
                        window,
                    ),
                ]
            )
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    base = pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS]
    cross_sectional = _cross_sectional_relative_factors(base)
    expanded = pd.concat([base, cross_sectional], ignore_index=True) if not cross_sectional.empty else base
    liquidity_gated = _liquidity_gated_factors(expanded)
    if not liquidity_gated.empty:
        expanded = pd.concat([expanded, liquidity_gated], ignore_index=True)
    state_adaptive = _state_adaptive_factors(expanded)
    if not state_adaptive.empty:
        expanded = pd.concat([expanded, state_adaptive], ignore_index=True)
    composites = _composite_factors(expanded)
    factors = pd.concat([expanded, composites], ignore_index=True) if not composites.empty else expanded
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


def _average_amount(amount: pd.Series, window: int) -> pd.Series:
    return np.log1p(amount.where(amount > 0).rolling(window).mean())


def _crash_recovery(price: pd.Series, window: int) -> pd.Series:
    recovery_window = _short_window(window)
    current_drawdown = _drawdown_resilience(price, window)
    recovery = _momentum(price, recovery_window)
    value = recovery * (-current_drawdown.clip(upper=0.0))
    return value.replace([np.inf, -np.inf], np.nan)


def _recovery_quality(price: pd.Series, returns: pd.Series, window: int) -> pd.Series:
    recovery_window = _short_window(window)
    downside_volatility = returns.clip(upper=0.0).rolling(window).std(ddof=0).replace(0, np.nan)
    current_drawdown = _drawdown_resilience(price, window)
    with np.errstate(divide="ignore", invalid="ignore"):
        value = _momentum(price, recovery_window) / downside_volatility + current_drawdown
    return value.replace([np.inf, -np.inf], np.nan)


def _demand_pressure(price: pd.Series, amount: pd.Series, window: int) -> pd.Series:
    half_window = _half_window(window)
    return (_momentum(price, half_window) * _log_amount_acceleration(amount, window)).replace([np.inf, -np.inf], np.nan)


def _quiet_accumulation(returns: pd.Series, amount: pd.Series, window: int) -> pd.Series:
    value = _log_amount_acceleration(amount, window) - returns.rolling(window).std(ddof=0)
    return value.replace([np.inf, -np.inf], np.nan)


def _log_amount_acceleration(amount: pd.Series, window: int) -> pd.Series:
    half_window = _half_window(window)
    recent_amount = amount.replace(0, np.nan).rolling(half_window).mean()
    prior_amount = recent_amount.shift(half_window)
    with np.errstate(divide="ignore", invalid="ignore"):
        value = np.log(recent_amount / prior_amount)
    return value.replace([np.inf, -np.inf], np.nan)


def _half_window(window: int) -> int:
    return max(1, int(window) // 2)


def _short_window(window: int) -> int:
    return max(2, int(window) // 3)


def _cross_sectional_relative_factors(factors: pd.DataFrame) -> pd.DataFrame:
    if factors.empty:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    rows = []
    for window in sorted(pd.to_numeric(factors["lookback_window"], errors="coerce").dropna().astype(int).unique()):
        source_name = f"momentum_{window}"
        window_factors = factors[factors["lookback_window"].astype(int) == window]
        wide = _factor_wide_frame(window_factors, [source_name])
        if wide.empty:
            continue
        grouped = wide.groupby(["date", "market"])[source_name]
        relative = wide[source_name] - grouped.transform("median")
        dispersion = grouped.transform(lambda values: values.std(ddof=0)).replace(0, np.nan)
        with np.errstate(divide="ignore", invalid="ignore"):
            breakout = relative / dispersion
        rows.extend(
            [
                _cross_sectional_factor_frame(wide, f"market_relative_strength_{window}", relative, window),
                _cross_sectional_factor_frame(
                    wide,
                    f"momentum_dispersion_breakout_{window}",
                    breakout.replace([np.inf, -np.inf], np.nan),
                    window,
                ),
            ]
        )
    if not rows:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(rows, ignore_index=True)[FACTOR_COLUMNS]


def _liquidity_gated_factors(factors: pd.DataFrame) -> pd.DataFrame:
    if factors.empty:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    rows = []
    for window in sorted(pd.to_numeric(factors["lookback_window"], errors="coerce").dropna().astype(int).unique()):
        amount_name = f"average_amount_{window}"
        liquidity_name = f"liquidity_resilience_{window}"
        window_factors = factors[factors["lookback_window"].astype(int) == window]
        for output_prefix, source_prefix in _LIQUIDITY_GATED_FACTOR_SPECS.items():
            source_name = f"{source_prefix}_{window}"
            wide = _factor_wide_frame(window_factors, [source_name, amount_name, liquidity_name])
            if wide.empty:
                continue
            grouped = wide.groupby(["date", "market"])
            amount_rank = grouped[amount_name].rank(method="average", pct=True)
            liquidity_rank = grouped[liquidity_name].rank(method="average", pct=True)
            values = wide[source_name].where((amount_rank > 0.5) & (liquidity_rank > 0.5))
            output = _cross_sectional_factor_frame(wide, f"{output_prefix}_{window}", values, window)
            rows.append(output.dropna(subset=["factor_value"]))
    if not rows:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(rows, ignore_index=True)[FACTOR_COLUMNS]


def _state_adaptive_factors(factors: pd.DataFrame) -> pd.DataFrame:
    if factors.empty:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    rows = []
    for window in sorted(pd.to_numeric(factors["lookback_window"], errors="coerce").dropna().astype(int).unique()):
        component_names = [f"{component}_{window}" for component in _STATE_ADAPTIVE_COMPONENTS]
        window_factors = factors[factors["lookback_window"].astype(int) == window]
        wide = _factor_wide_frame(window_factors, component_names)
        if wide.empty:
            continue
        grouped = wide.groupby(["date", "market"], group_keys=False)
        ranked = grouped[component_names].rank(method="average", pct=True)
        market_momentum = grouped[f"momentum_{window}"].transform("median")
        market_drawdown = grouped[f"drawdown_resilience_{window}"].transform("median")
        risk_on = market_momentum >= 0.0
        stress = (market_momentum < 0.0) | (market_drawdown < -0.05)
        trend_score = ranked[[f"momentum_{window}", f"market_relative_strength_{window}"]].mean(axis=1, skipna=False)
        defensive_score = ranked[
            [
                f"drawdown_resilience_{window}",
                f"low_downside_volatility_{window}",
                f"liquidity_resilience_{window}",
            ]
        ].mean(axis=1, skipna=False)
        recovery_score = ranked[
            [
                f"crash_recovery_{window}",
                f"recovery_quality_{window}",
                f"drawdown_resilience_{window}",
            ]
        ].mean(axis=1, skipna=False)
        rows.extend(
            [
                _cross_sectional_factor_frame(
                    wide,
                    f"state_adaptive_trend_defense_{window}",
                    trend_score.where(risk_on, defensive_score),
                    window,
                ),
                _cross_sectional_factor_frame(
                    wide,
                    f"state_stress_defensive_resilience_{window}",
                    defensive_score.where(stress),
                    window,
                ),
                _cross_sectional_factor_frame(
                    wide,
                    f"state_stress_recovery_leadership_{window}",
                    recovery_score.where(stress),
                    window,
                ),
            ]
        )
    if not rows:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(rows, ignore_index=True)[FACTOR_COLUMNS]


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


def _cross_sectional_factor_frame(frame: pd.DataFrame, name: str, values: pd.Series, window: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": frame["date"].to_numpy(),
            "asset_id": frame["asset_id"].to_numpy(),
            "market": frame["market"].to_numpy(),
            "factor_name": name,
            "factor_value": values.to_numpy(),
            "lookback_window": window,
        }
    )
