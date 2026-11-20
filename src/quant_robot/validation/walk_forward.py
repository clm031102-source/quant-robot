"""Clean rolling out-of-sample walk-forward validation for portfolio strategies."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from quant_robot.backtest.simulator import run_portfolio_backtest
from quant_robot.config.settings import CostConfig, RiskConfig, StrategySpec


@dataclass
class WalkForwardFold:
    fold_index: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    selected_candidate: str
    train_sharpe: float
    test_return: float
    test_sharpe: float
    test_max_drawdown: float
    benchmark_test_return: float


@dataclass
class WalkForwardResult:
    market: str
    symbols: list[str]
    folds: list[WalkForwardFold]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "market": self.market,
            "symbols": self.symbols,
            "summary": self.summary,
            "folds": [vars(f) for f in self.folds],
        }


def run_walk_forward(
    bars: pd.DataFrame,
    *,
    market: str,
    currency: str,
    symbols: list[str],
    candidates: dict[str, StrategySpec],
    cost: CostConfig,
    risk: RiskConfig,
    initial_cash: float = 10000.0,
    lot_size: float = 100.0,
    min_trade_notional: float = 0.0,
    train_sessions: int = 252,
    test_sessions: int = 126,
    step_sessions: int = 126,
) -> WalkForwardResult:
    """Evaluate candidates on rolling train windows and score the train winner out-of-sample."""
    if not candidates:
        raise ValueError("At least one candidate strategy is required")
    dates = sorted(pd.to_datetime(bars["date"]).dt.date.unique())
    if len(dates) < train_sessions + test_sessions:
        raise ValueError(
            f"Need at least {train_sessions + test_sessions} sessions for walk-forward; found {len(dates)}"
        )

    folds: list[WalkForwardFold] = []
    cursor = 0
    fold_idx = 1
    while cursor + train_sessions + test_sessions <= len(dates):
        tr_start = dates[cursor].isoformat()
        tr_end = dates[cursor + train_sessions - 1].isoformat()
        te_start = dates[cursor + train_sessions].isoformat()
        te_end = dates[cursor + train_sessions + test_sessions - 1].isoformat()

        best_name = ""
        best_sharpe = -1e9
        for cand_name, cand_spec in candidates.items():
            tr_rep = run_portfolio_backtest(
                bars,
                name=cand_name,
                market=market,
                currency=currency,
                symbols=symbols,
                strategy=cand_spec,
                cost=cost,
                risk=risk,
                initial_cash=initial_cash,
                lot_size=lot_size,
                min_trade_notional=min_trade_notional,
                start_date=tr_start,
                end_date=tr_end,
                include_benchmark=False,
            )
            sh = float(tr_rep.metrics.get("sharpe", 0.0))
            if sh > best_sharpe:
                best_sharpe = sh
                best_name = cand_name

        te_rep = run_portfolio_backtest(
            bars,
            name=best_name,
            market=market,
            currency=currency,
            symbols=symbols,
            strategy=candidates[best_name],
            cost=cost,
            risk=risk,
            initial_cash=initial_cash,
            lot_size=lot_size,
            min_trade_notional=min_trade_notional,
            start_date=te_start,
            end_date=te_end,
            include_benchmark=True,
        )
        folds.append(
            WalkForwardFold(
                fold_index=fold_idx,
                train_start=tr_start,
                train_end=tr_end,
                test_start=te_start,
                test_end=te_end,
                selected_candidate=best_name,
                train_sharpe=round(best_sharpe, 4),
                test_return=float(te_rep.metrics["total_return"]),
                test_sharpe=float(te_rep.metrics["sharpe"]),
                test_max_drawdown=float(te_rep.metrics["max_drawdown"]),
                benchmark_test_return=float(te_rep.benchmark_metrics.get("total_return", 0.0)),
            )
        )
        cursor += step_sessions
        fold_idx += 1

    mean_oos_ret = sum(f.test_return for f in folds) / len(folds)
    mean_oos_sharpe = sum(f.test_sharpe for f in folds) / len(folds)
    mean_bench_ret = sum(f.benchmark_test_return for f in folds) / len(folds)
    pos_rate = sum(1 for f in folds if f.test_return > 0) / len(folds)
    beat_bench_rate = sum(1 for f in folds if f.test_return > f.benchmark_test_return) / len(folds)

    summary = {
        "fold_count": len(folds),
        "mean_oos_return": round(mean_oos_ret, 6),
        "mean_oos_sharpe": round(mean_oos_sharpe, 4),
        "mean_benchmark_return": round(mean_bench_ret, 6),
        "oos_positive_fold_rate": round(pos_rate, 4),
        "oos_beat_benchmark_rate": round(beat_bench_rate, 4),
        "worst_oos_drawdown": round(min(f.test_max_drawdown for f in folds), 6),
    }
    return WalkForwardResult(market=market, symbols=symbols, folds=folds, summary=summary)
