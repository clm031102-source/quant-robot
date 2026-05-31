from __future__ import annotations

import math

import pandas as pd


def max_drawdown(equity_curve: pd.Series) -> float:
    if equity_curve.empty:
        return 0.0
    running_max = equity_curve.cummax()
    drawdowns = equity_curve / running_max - 1.0
    return float(drawdowns.min())


def summarize_returns(returns: pd.Series, periods_per_year: float = 252) -> dict[str, float]:
    clean = returns.dropna()
    if clean.empty:
        return {
            "total_return": 0.0,
            "annualized_return": 0.0,
            "annualized_volatility": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
        }
    equity = (1.0 + clean).cumprod()
    total_return = float(equity.iloc[-1] - 1.0)
    annualized_return = float(equity.iloc[-1] ** (periods_per_year / len(clean)) - 1.0)
    annualized_volatility = float(clean.std(ddof=0) * math.sqrt(periods_per_year))
    sharpe = 0.0 if annualized_volatility == 0 else float((clean.mean() * periods_per_year) / annualized_volatility)
    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown(equity),
        "win_rate": float((clean > 0).mean()),
    }
