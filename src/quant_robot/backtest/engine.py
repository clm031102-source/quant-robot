from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quant_robot.backtest.costs import capacity_limited, estimate_trade_cost_rate
from quant_robot.backtest.metrics import summarize_returns
from quant_robot.backtest.portfolio import select_top_n
from quant_robot.research.overlap import overlap_aware_return_stats


EXTREME_TRADE_ABS_GROSS_RETURN_THRESHOLD = 5.0


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: pd.DataFrame
    positions: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict[str, float]


def run_factor_backtest(
    factors: pd.DataFrame,
    bars: pd.DataFrame,
    top_n: int = 10,
    cost_bps: float = 0.0,
    portfolio_scope: str = "market",
    execution_lag: int = 1,
    holding_period: int = 1,
    rebalance_interval: int = 1,
    target_gross_exposure: float = 1.0,
    periods_per_year: float = 252,
    commission_bps: float | None = None,
    slippage_bps: float | None = None,
    market_impact_bps: float = 0.0,
    max_participation_rate: float | None = None,
    portfolio_value: float = 1_000_000.0,
) -> BacktestResult:
    required_factor_columns = ["date", "asset_id", "market", "factor_name", "factor_value"]
    required_bar_columns = ["date", "asset_id", "market", "adj_close"]
    _require_columns(factors, required_factor_columns, "factors")
    _require_columns(bars, required_bar_columns, "bars")
    if execution_lag < 1:
        raise ValueError("execution_lag must be at least 1")
    if holding_period < 1:
        raise ValueError("holding_period must be at least 1")
    if rebalance_interval < 1:
        raise ValueError("rebalance_interval must be at least 1")
    if target_gross_exposure <= 0.0 or target_gross_exposure > 1.0:
        raise ValueError("target_gross_exposure must be greater than 0 and at most 1")
    if max_participation_rate is not None and max_participation_rate <= 0.0:
        raise ValueError("max_participation_rate must be positive when provided")
    if portfolio_value <= 0.0:
        raise ValueError("portfolio_value must be positive")

    factors = _normalize_date_column(factors)
    bars = _normalize_date_column(bars)
    selected = _scale_signal_sleeves(
        select_top_n(factors, top_n=top_n, portfolio_scope=portfolio_scope),
        holding_period,
        rebalance_interval,
        target_gross_exposure,
    )
    bar_lookup = _price_lookup(bars)
    trades = _build_trades(
        selected,
        bar_lookup,
        cost_bps,
        execution_lag,
        holding_period,
        commission_bps=commission_bps,
        slippage_bps=slippage_bps,
        market_impact_bps=market_impact_bps,
        max_participation_rate=max_participation_rate,
        portfolio_value=portfolio_value,
    )
    equity_curve = _equity_curve(trades)
    metrics = summarize_returns(
        equity_curve["period_return"] if not equity_curve.empty else pd.Series(dtype=float),
        periods_per_year=periods_per_year,
    )
    metrics.update(
        _overlap_metrics(
            equity_curve["period_return"] if not equity_curve.empty else pd.Series(dtype=float),
            periods_per_year=periods_per_year,
            holding_period=holding_period,
        )
    )
    metrics.update(_trade_return_metrics(trades))
    if not trades.empty:
        metrics["turnover"] = float(trades.groupby("signal_date")["target_weight"].sum().mean())
        metrics["average_holdings"] = float(trades.groupby("signal_date")["asset_id"].nunique().mean())
        metrics["avg_cost_rate"] = float(trades["cost_rate"].mean())
        metrics["max_cost_rate"] = float(trades["cost_rate"].max())
        metrics["avg_participation_rate"] = float(trades["participation_rate"].mean())
        metrics["max_participation_rate"] = float(trades["participation_rate"].max())
        metrics["capacity_limited_trades"] = int(trades["capacity_limited"].sum())
    else:
        metrics["turnover"] = 0.0
        metrics["average_holdings"] = 0.0
        metrics["avg_cost_rate"] = 0.0
        metrics["max_cost_rate"] = 0.0
        metrics["avg_participation_rate"] = 0.0
        metrics["max_participation_rate"] = 0.0
        metrics["capacity_limited_trades"] = 0
    return BacktestResult(equity_curve=equity_curve, positions=selected, trades=trades, metrics=metrics)


def _trade_return_metrics(trades: pd.DataFrame) -> dict[str, float | bool]:
    if trades.empty or "gross_return" not in trades.columns:
        return {
            "max_trade_gross_return": 0.0,
            "max_abs_trade_gross_return": 0.0,
            "p99_abs_trade_gross_return": 0.0,
            "extreme_trade_return_flag": False,
        }
    gross = pd.to_numeric(trades["gross_return"], errors="coerce").dropna()
    if gross.empty:
        return {
            "max_trade_gross_return": 0.0,
            "max_abs_trade_gross_return": 0.0,
            "p99_abs_trade_gross_return": 0.0,
            "extreme_trade_return_flag": False,
        }
    abs_gross = gross.abs()
    max_abs = float(abs_gross.max())
    return {
        "max_trade_gross_return": float(gross.max()),
        "max_abs_trade_gross_return": max_abs,
        "p99_abs_trade_gross_return": float(abs_gross.quantile(0.99)),
        "extreme_trade_return_flag": bool(max_abs > EXTREME_TRADE_ABS_GROSS_RETURN_THRESHOLD),
    }


def _overlap_metrics(returns: pd.Series, *, periods_per_year: float, holding_period: int) -> dict[str, object]:
    stats = overlap_aware_return_stats(
        returns,
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    return {
        key if key.startswith("overlap_") else f"overlap_{key}": value
        for key, value in stats.items()
    }


def _require_columns(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{name} is missing columns: {', '.join(missing)}")


def _normalize_date_column(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"]).dt.date
    return result


def _scale_signal_sleeves(
    selected: pd.DataFrame,
    holding_period: int,
    rebalance_interval: int,
    target_gross_exposure: float,
) -> pd.DataFrame:
    if selected.empty:
        return selected
    scaled = selected.copy()
    sleeve_scale = 1.0 if holding_period <= 1 else min(float(rebalance_interval) / float(holding_period), 1.0)
    scaled["target_weight"] = scaled["target_weight"] * sleeve_scale * float(target_gross_exposure)
    return scaled


def _price_lookup(bars: pd.DataFrame) -> dict[str, pd.DataFrame]:
    lookup = {}
    for asset_id, group in bars.sort_values(["asset_id", "date"]).groupby("asset_id", sort=False):
        lookup[asset_id] = group.reset_index(drop=True)
    return lookup


def _build_trades(
    selected: pd.DataFrame,
    bar_lookup: dict[str, pd.DataFrame],
    cost_bps: float,
    execution_lag: int,
    holding_period: int,
    *,
    commission_bps: float | None,
    slippage_bps: float | None,
    market_impact_bps: float,
    max_participation_rate: float | None,
    portfolio_value: float,
) -> pd.DataFrame:
    rows = []
    for row in selected.itertuples(index=False):
        asset_bars = bar_lookup.get(row.asset_id)
        if asset_bars is None:
            continue
        needed_future_bars = execution_lag + holding_period
        future = asset_bars[asset_bars["date"] > row.date].head(needed_future_bars)
        if len(future) < needed_future_bars:
            continue
        entry = future.iloc[execution_lag - 1]
        exit_ = future.iloc[execution_lag + holding_period - 1]
        participation_rate = _participation_rate(row.target_weight, entry, portfolio_value)
        cost_rate = estimate_trade_cost_rate(
            cost_bps,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            market_impact_bps=market_impact_bps,
            participation_rate=participation_rate,
            max_participation_rate=max_participation_rate,
        )
        gross_return = exit_["adj_close"] / entry["adj_close"] - 1.0
        net_return = gross_return - cost_rate
        rows.append(
            {
                "signal_date": row.date,
                "entry_date": entry["date"],
                "exit_date": exit_["date"],
                "asset_id": row.asset_id,
                "market": row.market,
                "factor_name": row.factor_name,
                "target_weight": row.target_weight,
                "target_notional": abs(row.target_weight) * portfolio_value,
                "entry_amount": _entry_amount(entry),
                "participation_rate": participation_rate,
                "capacity_limited": capacity_limited(participation_rate, max_participation_rate),
                "cost_rate": cost_rate,
                "gross_return": gross_return,
                "net_return": net_return,
                "weighted_return": row.target_weight * net_return,
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "signal_date",
                "entry_date",
                "exit_date",
                "asset_id",
                "market",
                "factor_name",
                "target_weight",
                "target_notional",
                "entry_amount",
                "participation_rate",
                "capacity_limited",
                "cost_rate",
                "gross_return",
                "net_return",
                "weighted_return",
            ]
        )
    return pd.DataFrame(rows).sort_values(["signal_date", "factor_name", "asset_id"]).reset_index(drop=True)


def _participation_rate(target_weight: float, entry: pd.Series, portfolio_value: float) -> float:
    entry_amount = _entry_amount(entry)
    if entry_amount <= 0.0:
        return 0.0
    return abs(float(target_weight)) * float(portfolio_value) / entry_amount


def _entry_amount(entry: pd.Series) -> float:
    try:
        value = float(entry.get("amount", 0.0))
    except (TypeError, ValueError):
        return 0.0
    return value if value > 0.0 else 0.0


def _equity_curve(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(columns=["date", "period_return", "equity"])
    returns = (
        trades.groupby("exit_date", as_index=False)
        .agg(period_return=("weighted_return", "sum"))
        .rename(columns={"exit_date": "date"})
        .sort_values("date")
        .reset_index(drop=True)
    )
    returns["equity"] = (1.0 + returns["period_return"]).cumprod()
    return returns
