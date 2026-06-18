from __future__ import annotations

import math
from typing import Any

import pandas as pd


def overlap_aware_return_stats(
    returns: pd.Series,
    *,
    periods_per_year: float = 252.0,
    holding_period: int = 1,
    max_lag: int | None = None,
) -> dict[str, Any]:
    values = pd.to_numeric(returns, errors="coerce").dropna().astype(float)
    observations = int(len(values))
    lag_count = _lag_count(observations=observations, holding_period=holding_period, max_lag=max_lag)
    if observations == 0:
        return _empty_stats(observations=0, max_lag=lag_count)

    mean_return = float(values.mean())
    variance = float(values.var(ddof=1)) if observations > 1 else 0.0
    volatility = math.sqrt(max(variance, 0.0))
    if observations < 2 or volatility == 0.0:
        return {
            **_empty_stats(observations=observations, max_lag=lag_count),
            "mean_return": mean_return,
            "volatility": volatility,
        }

    naive_sharpe = mean_return / volatility * math.sqrt(periods_per_year)
    autocorrelations = _autocorrelations(values, lag_count)
    long_run_variance = _newey_west_long_run_variance(values, lag_count)
    variance_inflation = long_run_variance / variance if variance > 0.0 else 1.0
    if variance_inflation <= 0.0 or not math.isfinite(variance_inflation):
        variance_inflation = 1.0
    effective_sample_size = observations / variance_inflation
    adjusted_volatility = math.sqrt(max(long_run_variance, 0.0))
    adjusted_sharpe = mean_return / adjusted_volatility * math.sqrt(periods_per_year) if adjusted_volatility > 0.0 else 0.0
    standard_error = math.sqrt(max(long_run_variance, 0.0) / observations)
    t_stat = mean_return / standard_error if standard_error > 0.0 else 0.0

    return {
        "usable": True,
        "observations": observations,
        "mean_return": mean_return,
        "volatility": volatility,
        "periods_per_year": float(periods_per_year),
        "holding_period": int(holding_period),
        "max_lag": lag_count,
        "naive_sharpe": _finite(naive_sharpe),
        "autocorr_adjusted_sharpe": _finite(adjusted_sharpe),
        "newey_west_long_run_variance": _finite(long_run_variance),
        "newey_west_standard_error_mean": _finite(standard_error),
        "newey_west_t_stat_mean": _finite(t_stat),
        "variance_inflation": _finite(variance_inflation),
        "effective_sample_size": _finite(max(0.0, min(float(observations), effective_sample_size))),
        "autocorrelations": autocorrelations,
        "overlap_risk_flag": bool(int(holding_period) > 1 and lag_count > 0),
    }


def _lag_count(*, observations: int, holding_period: int, max_lag: int | None) -> int:
    if observations <= 1:
        return 0
    if max_lag is not None:
        requested = int(max_lag)
    else:
        requested = max(0, int(holding_period) - 1)
    return max(0, min(requested, observations - 1))


def _autocorrelations(values: pd.Series, max_lag: int) -> list[float]:
    if max_lag <= 0:
        return []
    centered = values - float(values.mean())
    variance_sum = float((centered * centered).sum())
    if variance_sum <= 0.0:
        return [0.0 for _ in range(max_lag)]
    correlations = []
    for lag in range(1, max_lag + 1):
        numerator = float((centered.iloc[lag:].to_numpy() * centered.iloc[:-lag].to_numpy()).sum())
        correlations.append(_finite(numerator / variance_sum))
    return correlations


def _newey_west_long_run_variance(values: pd.Series, max_lag: int) -> float:
    centered = values - float(values.mean())
    n = len(centered)
    gamma0 = float((centered * centered).sum() / max(n - 1, 1))
    if max_lag <= 0:
        return gamma0
    long_run_variance = gamma0
    for lag in range(1, max_lag + 1):
        cov = float((centered.iloc[lag:].to_numpy() * centered.iloc[:-lag].to_numpy()).sum() / max(n - 1, 1))
        weight = 1.0 - lag / (max_lag + 1.0)
        long_run_variance += 2.0 * weight * cov
    return max(long_run_variance, 0.0)


def _empty_stats(*, observations: int, max_lag: int) -> dict[str, Any]:
    return {
        "usable": False,
        "observations": int(observations),
        "mean_return": 0.0,
        "volatility": 0.0,
        "periods_per_year": 252.0,
        "holding_period": 1,
        "max_lag": int(max_lag),
        "naive_sharpe": 0.0,
        "autocorr_adjusted_sharpe": 0.0,
        "newey_west_long_run_variance": 0.0,
        "newey_west_standard_error_mean": 0.0,
        "newey_west_t_stat_mean": 0.0,
        "variance_inflation": 1.0,
        "effective_sample_size": 0.0,
        "autocorrelations": [],
        "overlap_risk_flag": False,
    }


def _finite(value: float) -> float:
    return float(value) if math.isfinite(float(value)) else 0.0

