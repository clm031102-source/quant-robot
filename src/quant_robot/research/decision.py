from __future__ import annotations

import math
from typing import Any

import pandas as pd


def build_benchmark_curve(bars: pd.DataFrame, benchmark_asset_id: str | None = None) -> pd.DataFrame:
    _require_columns(bars, ["date", "asset_id", "adj_close"], "bars")
    frame = bars[["date", "asset_id", "adj_close"]].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    frame = frame.dropna(subset=["adj_close"]).sort_values(["asset_id", "date"]).reset_index(drop=True)
    if benchmark_asset_id is not None:
        frame = frame[frame["asset_id"].astype(str) == str(benchmark_asset_id)].copy()
        if frame.empty:
            raise ValueError(f"Benchmark asset is not present in bars: {benchmark_asset_id}")
        frame["benchmark_return"] = frame["adj_close"].pct_change().fillna(0.0)
        frame["benchmark_equity"] = (1.0 + frame["benchmark_return"]).cumprod()
        frame["benchmark_asset_id"] = str(benchmark_asset_id)
        return frame[["date", "benchmark_return", "benchmark_equity", "benchmark_asset_id"]].reset_index(drop=True)

    frame["asset_return"] = frame.groupby("asset_id", sort=False)["adj_close"].pct_change().fillna(0.0)
    curve = (
        frame.groupby("date", as_index=False)["asset_return"]
        .mean()
        .rename(columns={"asset_return": "benchmark_return"})
        .sort_values("date")
        .reset_index(drop=True)
    )
    curve["benchmark_equity"] = (1.0 + curve["benchmark_return"]).cumprod()
    curve["benchmark_asset_id"] = "equal_weight"
    return curve[["date", "benchmark_return", "benchmark_equity", "benchmark_asset_id"]]


def compare_strategy_to_benchmark(
    equity_curve: pd.DataFrame,
    benchmark_curve: pd.DataFrame,
    cash_annual_return: float = 0.0,
    periods_per_year: float = 252.0,
) -> dict[str, float]:
    strategy_return = _total_return_from_curve(equity_curve, "period_return", "equity")
    benchmark_return = _total_return_from_curve(benchmark_curve, "benchmark_return", "benchmark_equity")
    periods = max(len(benchmark_curve) - 1, 0)
    cash_total_return = (1.0 + float(cash_annual_return)) ** (periods / float(periods_per_year)) - 1.0 if periods_per_year > 0 else 0.0
    return _finite_dict(
        {
            "strategy_total_return": strategy_return,
            "benchmark_total_return": benchmark_return,
            "relative_return": strategy_return - benchmark_return,
            "cash_total_return": cash_total_return,
            "excess_over_cash": strategy_return - cash_total_return,
        }
    )


def regime_allowed_dates(
    bars: pd.DataFrame,
    benchmark_asset_id: str | None = None,
    lookback: int = 20,
    require_positive_momentum: bool = True,
) -> pd.DataFrame:
    if lookback < 1:
        raise ValueError("lookback must be at least 1")
    curve = build_benchmark_curve(bars, benchmark_asset_id=benchmark_asset_id)
    frame = curve[["date", "benchmark_equity"]].copy()
    frame["regime_momentum"] = frame["benchmark_equity"] / frame["benchmark_equity"].shift(lookback) - 1.0
    if require_positive_momentum:
        frame["regime_allowed"] = frame["regime_momentum"] > 0.0
    else:
        frame["regime_allowed"] = frame["regime_momentum"].notna()
    return frame[["date", "regime_momentum", "regime_allowed"]].reset_index(drop=True)


def decision_summary(
    strategy_metrics: dict[str, Any],
    benchmark_metrics: dict[str, Any],
    min_relative_return: float | None = None,
    max_drawdown_limit: float | None = None,
) -> dict[str, Any]:
    reasons: list[str] = []
    relative_return = _number(benchmark_metrics.get("relative_return"))
    max_dd = _number(strategy_metrics.get("max_drawdown"))
    capacity_limited_trades = int(_number(strategy_metrics.get("capacity_limited_trades")))
    if min_relative_return is not None and relative_return < float(min_relative_return):
        reasons.append("relative_return_below_threshold")
    if max_drawdown_limit is not None and max_dd < -abs(float(max_drawdown_limit)):
        reasons.append("drawdown_above_limit")
    if capacity_limited_trades > 0:
        reasons.append("capacity_limited_trades_present")
    return {
        "decision_status": "approved" if not reasons else "rejected",
        "rejection_reasons": reasons,
        "relative_return": relative_return,
        "max_drawdown": max_dd,
        "capacity_limited_trades": capacity_limited_trades,
        "min_relative_return": min_relative_return,
        "max_drawdown_limit": max_drawdown_limit,
    }


def _require_columns(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{name} is missing columns: {', '.join(missing)}")


def _total_return_from_curve(curve: pd.DataFrame, return_column: str, equity_column: str) -> float:
    if curve.empty:
        return 0.0
    if return_column in curve.columns:
        returns = pd.to_numeric(curve[return_column], errors="coerce").dropna()
        if not returns.empty:
            return float((1.0 + returns).prod() - 1.0)
    if equity_column in curve.columns:
        equity = pd.to_numeric(curve[equity_column], errors="coerce").dropna()
        if len(equity) >= 2 and float(equity.iloc[0]) != 0.0:
            return float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    return 0.0


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _finite_dict(values: dict[str, float]) -> dict[str, float]:
    return {key: value if math.isfinite(value) else 0.0 for key, value in values.items()}
