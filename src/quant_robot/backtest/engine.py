from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quant_robot.backtest.costs import round_trip_cost
from quant_robot.backtest.metrics import summarize_returns
from quant_robot.backtest.portfolio import select_top_n


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: pd.DataFrame
    positions: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict[str, float]


def run_factor_backtest(factors: pd.DataFrame, bars: pd.DataFrame, top_n: int = 10, cost_bps: float = 0.0) -> BacktestResult:
    required_factor_columns = ["date", "asset_id", "market", "factor_name", "factor_value"]
    required_bar_columns = ["date", "asset_id", "market", "adj_close"]
    _require_columns(factors, required_factor_columns, "factors")
    _require_columns(bars, required_bar_columns, "bars")

    selected = select_top_n(factors, top_n=top_n)
    bar_lookup = _price_lookup(bars)
    trades = _build_trades(selected, bar_lookup, round_trip_cost(cost_bps))
    equity_curve = _equity_curve(trades)
    metrics = summarize_returns(equity_curve["period_return"] if not equity_curve.empty else pd.Series(dtype=float))
    if not trades.empty:
        metrics["turnover"] = float(trades.groupby("signal_date")["target_weight"].sum().mean())
        metrics["average_holdings"] = float(trades.groupby("signal_date")["asset_id"].nunique().mean())
    else:
        metrics["turnover"] = 0.0
        metrics["average_holdings"] = 0.0
    return BacktestResult(equity_curve=equity_curve, positions=selected, trades=trades, metrics=metrics)


def _require_columns(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{name} is missing columns: {', '.join(missing)}")


def _price_lookup(bars: pd.DataFrame) -> dict[str, pd.DataFrame]:
    lookup = {}
    for asset_id, group in bars.sort_values(["asset_id", "date"]).groupby("asset_id", sort=False):
        lookup[asset_id] = group.reset_index(drop=True)
    return lookup


def _build_trades(selected: pd.DataFrame, bar_lookup: dict[str, pd.DataFrame], cost: float) -> pd.DataFrame:
    rows = []
    for row in selected.itertuples(index=False):
        asset_bars = bar_lookup.get(row.asset_id)
        if asset_bars is None:
            continue
        future = asset_bars[asset_bars["date"] > row.date].head(2)
        if len(future) < 2:
            continue
        entry = future.iloc[0]
        exit_ = future.iloc[1]
        gross_return = exit_["adj_close"] / entry["adj_close"] - 1.0
        net_return = gross_return - cost
        rows.append(
            {
                "signal_date": row.date,
                "entry_date": entry["date"],
                "exit_date": exit_["date"],
                "asset_id": row.asset_id,
                "market": row.market,
                "factor_name": row.factor_name,
                "target_weight": row.target_weight,
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
                "gross_return",
                "net_return",
                "weighted_return",
            ]
        )
    return pd.DataFrame(rows).sort_values(["signal_date", "factor_name", "asset_id"]).reset_index(drop=True)


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
