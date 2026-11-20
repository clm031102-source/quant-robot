"""Realistic, strictly causal multi-asset portfolio backtest simulator.

Models integer lot sizes (e.g. 100-share CN ETFs, 1-share US ETFs), minimum commissions
(e.g. Huabao 5 CNY / US $1), bps commissions, adverse slippage, total-return dividend/split
adjustment via adj_close ratios, drawdown halt + cooldown recovery, and Buy-and-Hold benchmark.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from typing import Any

import numpy as np
import pandas as pd

from quant_robot.config.settings import CostConfig, RiskConfig, StrategySpec
from quant_robot.strategies.builtins import compute_target_weights, is_rebalance_day, should_rebalance_by_band


@dataclass
class BacktestReport:
    name: str
    market: str
    currency: str
    symbols: list[str]
    start_date: str
    end_date: str
    metrics: dict[str, float]
    benchmark_metrics: dict[str, float]
    yearly_returns: list[dict[str, Any]]
    equity_curve: pd.DataFrame
    trades: pd.DataFrame

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "market": self.market,
            "currency": self.currency,
            "symbols": self.symbols,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "metrics": self.metrics,
            "benchmark_metrics": self.benchmark_metrics,
            "yearly_returns": self.yearly_returns,
            "trade_count": int(len(self.trades)),
        }


def run_portfolio_backtest(
    bars: pd.DataFrame,
    *,
    name: str,
    market: str,
    currency: str,
    symbols: list[str],
    strategy: StrategySpec,
    cost: CostConfig,
    risk: RiskConfig,
    initial_cash: float = 10000.0,
    lot_size: int = 100,
    execution_price: str = "open",
    start_date: str | None = None,
    end_date: str | None = None,
    include_benchmark: bool = True,
) -> BacktestReport:
    """Run a strictly causal T+1 backtest on daily OHLCV bars."""
    if bars.empty:
        raise ValueError("Cannot run backtest on empty bars DataFrame")

    df = bars.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["symbol"] = df["symbol"].astype(str).str.upper()
    norm_symbols = [s.strip().upper() for s in symbols]
    df = df[df["symbol"].isin(norm_symbols)].sort_values(["date", "symbol"])

    adj_panel = df.pivot_table(index="date", columns="symbol", values="adj_close", aggfunc="last").sort_index().ffill()
    raw_close_panel = df.pivot_table(index="date", columns="symbol", values="close", aggfunc="last").sort_index().ffill()
    raw_open_panel = df.pivot_table(index="date", columns="symbol", values="open", aggfunc="last").sort_index().ffill()

    # Keep total-return factor so cash dividends & splits compound properly while lot rounding uses realistic prices.
    adj_ratio = (adj_panel / raw_close_panel).replace([np.inf, -np.inf], np.nan).ffill().fillna(1.0)
    adj_open_panel = raw_open_panel * adj_ratio

    all_dates = list(adj_panel.index)
    start_d = pd.to_datetime(start_date).date() if start_date else all_dates[0]
    end_d = pd.to_datetime(end_date).date() if end_date else all_dates[-1]
    sim_indices = [i for i, d in enumerate(all_dates) if start_d <= d <= end_d]
    if len(sim_indices) < 2:
        raise ValueError(f"Not enough trading sessions in range {start_d}..{end_d} (found {len(sim_indices)})")

    cash = float(initial_cash)
    # Track holdings in adjusted-price share equivalents scaled by raw lot granularity at trade time.
    shares: dict[str, float] = {s: 0.0 for s in norm_symbols}
    peak_nav = float(initial_cash)
    prev_nav = float(initial_cash)
    cooldown_left = 0
    pending_targets: dict[str, float] | None = None
    pending_reason = ""
    total_commission = 0.0
    total_slippage = 0.0
    equity_rows: list[dict[str, Any]] = []
    trade_rows: list[dict[str, Any]] = []

    exec_panel = adj_open_panel if execution_price == "open" else adj_panel
    raw_exec_panel = raw_open_panel if execution_price == "open" else raw_close_panel

    for pos_in_sim, idx in enumerate(sim_indices):
        cur_date: date = all_dates[idx]
        # 1) Execute pending T-1 signal at today's open/close (strictly causal!)
        day_trades = 0
        if pending_targets is not None:
            cash, filled = _execute_rebalance(
                cur_date=cur_date,
                cash=cash,
                shares=shares,
                target_weights=pending_targets,
                exec_prices=exec_panel.iloc[idx],
                raw_prices=raw_exec_panel.iloc[idx],
                lot_size=lot_size,
                cost=cost,
                reason=pending_reason,
            )
            for tr in filled:
                total_commission += tr["commission"]
                total_slippage += tr["slippage"]
                trade_rows.append(tr)
            day_trades = len(filled)
            pending_targets = None
            pending_reason = ""

        # 2) Mark-to-market at close
        close_prices = adj_panel.iloc[idx]
        mv = 0.0
        for sym, qty in shares.items():
            px = close_prices.get(sym)
            if qty > 0 and pd.notna(px) and float(px) > 0:
                mv += qty * float(px)
        nav = cash + mv
        peak_nav = max(peak_nav, nav)
        dd = (nav / peak_nav - 1.0) if peak_nav > 0 else 0.0
        daily_ret = (nav / prev_nav - 1.0) if prev_nav > 0 else 0.0

        equity_rows.append(
            {
                "date": cur_date.isoformat(),
                "nav": round(nav, 4),
                "cash": round(cash, 4),
                "market_value": round(mv, 4),
                "daily_return": daily_ret,
                "drawdown": dd,
                "peak_nav": round(peak_nav, 4),
                "trades": day_trades,
            }
        )

        # 3) Risk guard check at close -> schedules next-day exit + cooldown recovery
        if cooldown_left > 0:
            cooldown_left -= 1
            if cooldown_left == 0:
                # Reset peak only after full cooldown so strategy can cleanly re-enter without permanent deadlock.
                peak_nav = nav
            prev_nav = nav
            continue

        risk_triggered = False
        if risk.max_drawdown_halt is not None and (-dd) >= risk.max_drawdown_halt and mv > 0:
            risk_triggered = True
            pending_targets = {}
            pending_reason = f"drawdown_halt_{risk.max_drawdown_halt:.0%}"
            cooldown_left = max(1, risk.cooldown_sessions)
        elif risk.daily_loss_halt is not None and (-daily_ret) >= risk.daily_loss_halt and mv > 0:
            risk_triggered = True
            pending_targets = {}
            pending_reason = f"daily_loss_halt_{risk.daily_loss_halt:.1%}"
            cooldown_left = max(1, risk.cooldown_sessions)

        # 4) Compute T-close signal for T+1 execution
        if not risk_triggered and pos_in_sim + 1 < len(sim_indices):
            has_pos = any(q > 0 for q in shares.values())
            if is_rebalance_day(all_dates, idx, strategy.rebalance_frequency, has_positions=has_pos):
                history = adj_panel.iloc[: idx + 1]
                targets, _ = compute_target_weights(history, norm_symbols, strategy, risk)
                cur_weights = {
                    sym: (shares[sym] * float(close_prices[sym]) / nav)
                    for sym in norm_symbols
                    if shares[sym] > 0 and pd.notna(close_prices.get(sym)) and nav > 0
                }
                if not has_pos or should_rebalance_by_band(cur_weights, targets, strategy.rebalance_band):
                    pending_targets = targets
                    pending_reason = "initial_entry" if not has_pos else "scheduled_rebalance"

        prev_nav = nav

    eq_df = pd.DataFrame(equity_rows)
    trades_df = pd.DataFrame(trade_rows)
    metrics = compute_backtest_metrics(eq_df, initial_cash=initial_cash, total_commission=total_commission, total_slippage=total_slippage, trade_count=len(trades_df))

    if include_benchmark:
        bench_spec = StrategySpec(kind="passive_drift", rebalance_frequency="never", rebalance_band=0.0)
        bench_risk = RiskConfig(max_drawdown_halt=None, daily_loss_halt=None, cooldown_sessions=0)
        bench = run_portfolio_backtest(
            bars,
            name=f"{name} (Buy&Hold)",
            market=market,
            currency=currency,
            symbols=norm_symbols,
            strategy=bench_spec,
            cost=cost,
            risk=bench_risk,
            initial_cash=initial_cash,
            lot_size=lot_size,
            execution_price=execution_price,
            start_date=str(all_dates[sim_indices[0]]),
            end_date=str(all_dates[sim_indices[-1]]),
            include_benchmark=False,
        )
        benchmark_metrics = bench.metrics
        eq_df["benchmark_nav"] = bench.equity_curve["nav"].values
        metrics["excess_total_return"] = round(metrics["total_return"] - benchmark_metrics["total_return"], 6)
        metrics["excess_cagr"] = round(metrics["cagr"] - benchmark_metrics["cagr"], 6)
    else:
        benchmark_metrics = {}

    yearly = _yearly_returns(eq_df)
    return BacktestReport(
        name=name,
        market=market,
        currency=currency,
        symbols=norm_symbols,
        start_date=str(all_dates[sim_indices[0]]),
        end_date=str(all_dates[sim_indices[-1]]),
        metrics=metrics,
        benchmark_metrics=benchmark_metrics,
        yearly_returns=yearly,
        equity_curve=eq_df,
        trades=trades_df,
    )


def _execute_rebalance(
    *,
    cur_date: date,
    cash: float,
    shares: dict[str, float],
    target_weights: dict[str, float],
    exec_prices: pd.Series,
    raw_prices: pd.Series,
    lot_size: int,
    cost: CostConfig,
    reason: str,
) -> tuple[float, list[dict[str, Any]]]:
    """Execute sells first, then buys, respecting exact integer lots and minimum commissions."""
    # Current NAV at execution prices
    nav = cash
    for sym, qty in shares.items():
        px = exec_prices.get(sym)
        if qty > 0 and pd.notna(px) and float(px) > 0:
            nav += qty * float(px)
    if nav <= 0:
        return cash, []

    fills: list[dict[str, Any]] = []
    # Compute desired integer lots in raw share units, converted to adjusted-equivalent share units
    desired_shares: dict[str, float] = {}
    unit_scale: dict[str, float] = {}
    for sym in shares:
        adj_px = exec_prices.get(sym)
        raw_px = raw_prices.get(sym)
        if pd.isna(adj_px) or pd.isna(raw_px) or float(adj_px) <= 0 or float(raw_px) <= 0:
            desired_shares[sym] = shares[sym]
            unit_scale[sym] = 1.0
            continue
        # 1 raw lot costs raw_px * lot_size; in adj coordinates that corresponds to (raw_px / adj_px) * lot_size adj-shares
        scale = float(raw_px) / float(adj_px)
        unit_scale[sym] = scale
        tgt_val = nav * float(target_weights.get(sym, 0.0))
        raw_lots = math.floor(tgt_val / (float(raw_px) * lot_size))
        desired_shares[sym] = raw_lots * lot_size * scale

    # 1) SELLS first
    for sym in sorted(shares):
        cur_q = shares[sym]
        tgt_q = desired_shares[sym]
        if tgt_q >= cur_q - 1e-9:
            continue
        adj_px = float(exec_prices[sym])
        raw_px = float(raw_prices[sym])
        scale = max(unit_scale[sym], 1e-12)
        if tgt_q <= 1e-9:
            sell_q = cur_q
            new_q = 0.0
            raw_qty = max(1, round(sell_q / scale))
        else:
            sell_lots = math.floor(((cur_q - tgt_q) / scale + 1e-9) / lot_size)
            if sell_lots <= 0:
                continue
            raw_qty = int(sell_lots * lot_size)
            sell_q = min(cur_q, raw_qty * scale)
            new_q = max(0.0, cur_q - sell_q)
        gross = sell_q * adj_px
        slip = gross * (cost.slippage_bps / 10000.0)
        comm = max(gross * (cost.commission_bps / 10000.0), cost.minimum_commission)
        duty = gross * (cost.stamp_duty_sell_bps / 10000.0)
        proceeds = gross - slip - comm - duty
        cash += proceeds
        shares[sym] = new_q
        fills.append(
            {
                "date": cur_date.isoformat(),
                "symbol": sym,
                "side": "SELL",
                "quantity": int(raw_qty),
                "raw_price": round(raw_px, 4),
                "notional": round(gross, 2),
                "commission": round(comm + duty, 4),
                "slippage": round(slip, 4),
                "reason": reason,
            }
        )

    # 2) BUYS second (capped by spendable cash)
    for sym in sorted(shares):
        cur_q = shares[sym]
        tgt_q = desired_shares[sym]
        if tgt_q <= cur_q + 1e-9:
            continue
        adj_px = exec_prices.get(sym)
        raw_px = raw_prices.get(sym)
        if pd.isna(adj_px) or pd.isna(raw_px) or float(adj_px) <= 0 or float(raw_px) <= 0:
            continue
        adj_px_f = float(adj_px)
        raw_px_f = float(raw_px)
        scale = unit_scale[sym]
        need_lots = math.floor(((tgt_q - cur_q) / scale + 1e-9) / lot_size)
        if need_lots <= 0:
            continue
        # Reduce lots if cash cannot cover notional + slippage + minimum commission
        while need_lots > 0:
            buy_q = need_lots * lot_size * scale
            gross = buy_q * adj_px_f
            slip = gross * (cost.slippage_bps / 10000.0)
            comm = max(gross * (cost.commission_bps / 10000.0), cost.minimum_commission)
            total_cost = gross + slip + comm
            if total_cost <= cash + 1e-9:
                cash -= total_cost
                shares[sym] = cur_q + buy_q
                fills.append(
                    {
                        "date": cur_date.isoformat(),
                        "symbol": sym,
                        "side": "BUY",
                        "quantity": int(need_lots * lot_size),
                        "raw_price": round(raw_px_f, 4),
                        "notional": round(gross, 2),
                        "commission": round(comm, 4),
                        "slippage": round(slip, 4),
                        "reason": reason,
                    }
                )
                break
            need_lots -= 1

    return cash, fills


def compute_backtest_metrics(
    eq_df: pd.DataFrame,
    *,
    initial_cash: float,
    total_commission: float,
    total_slippage: float,
    trade_count: int,
) -> dict[str, float]:
    if eq_df.empty:
        return {}
    nav = eq_df["nav"].astype(float)
    rets = eq_df["daily_return"].astype(float)
    final_nav = float(nav.iloc[-1])
    total_return = final_nav / initial_cash - 1.0
    n_days = max(len(eq_df), 1)
    years = n_days / 252.0
    cagr = (final_nav / initial_cash) ** (1.0 / years) - 1.0 if years > 0 and final_nav > 0 else -1.0
    vol = float(rets.std(ddof=0) * math.sqrt(252.0))
    downside = rets[rets < 0]
    down_vol = float(downside.std(ddof=0) * math.sqrt(252.0)) if len(downside) > 1 else 0.0
    sharpe = float((rets.mean() * 252.0) / vol) if vol > 1e-12 else 0.0
    sortino = float((rets.mean() * 252.0) / down_vol) if down_vol > 1e-12 else 0.0
    max_dd = float(eq_df["drawdown"].min())
    calmar = float(cagr / abs(max_dd)) if abs(max_dd) > 1e-9 else 0.0
    cost_drag = (total_commission + total_slippage) / initial_cash
    return {
        "initial_cash": round(initial_cash, 2),
        "final_nav": round(final_nav, 2),
        "net_pnl": round(final_nav - initial_cash, 2),
        "total_return": round(total_return, 6),
        "cagr": round(cagr, 6),
        "annualized_volatility": round(vol, 6),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "max_drawdown": round(max_dd, 6),
        "calmar": round(calmar, 4),
        "win_day_rate": round(float((rets > 0).mean()), 4),
        "trade_count": float(trade_count),
        "total_commission": round(total_commission, 2),
        "total_slippage": round(total_slippage, 2),
        "cost_drag_pct": round(cost_drag, 6),
        "trading_days": float(n_days),
    }


def _yearly_returns(eq_df: pd.DataFrame) -> list[dict[str, Any]]:
    if eq_df.empty:
        return []
    df = eq_df.copy()
    df["year"] = pd.to_datetime(df["date"]).dt.year
    rows: list[dict[str, Any]] = []
    for year, grp in df.groupby("year", sort=True):
        strat_ret = float((1.0 + grp["daily_return"]).prod() - 1.0)
        entry: dict[str, Any] = {
            "year": int(year),
            "strategy_return": round(strat_ret, 6),
            "max_drawdown": round(float(grp["drawdown"].min()), 6),
            "trades": int(grp["trades"].sum()),
        }
        if "benchmark_nav" in grp.columns and float(grp["benchmark_nav"].iloc[0]) > 0:
            b_ret = float(grp["benchmark_nav"].iloc[-1] / grp["benchmark_nav"].iloc[0] - 1.0)
            entry["benchmark_return"] = round(b_ret, 6)
        rows.append(entry)
    return rows
