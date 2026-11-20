from __future__ import annotations

from datetime import date, timedelta
import unittest

import numpy as np
import pandas as pd

from quant_robot.backtest.simulator import run_portfolio_backtest
from quant_robot.config.settings import CostConfig, RiskConfig, StrategySpec
from quant_robot.validation.walk_forward import run_walk_forward


def _synthetic_universe(n_days: int = 420) -> pd.DataFrame:
    """Create a realistic 4-ETF universe with distinct trends, volatility, and a mid-period drawdown."""
    dates = pd.bdate_range("2023-01-03", periods=n_days)
    rng = np.random.default_rng(42)
    specs = {
        "ETF_A": (0.0007, 0.011, 4.0),   # Uptrend equity
        "ETF_B": (-0.0002, 0.015, 3.0),  # Choppy weak equity
        "ETF_G": (0.0005, 0.008, 6.0),   # Gold-like steady trend
        "ETF_D": (0.00015, 0.002, 2.5),  # Low-vol defensive
    }
    rows = []
    for sym, (mu, sigma, start_px) in specs.items():
        rets = rng.normal(mu, sigma, size=n_days)
        if sym == "ETF_A":
            rets[180:205] -= 0.018  # Sharp drawdown patch to exercise risk guard & trend filter
        prices = start_px * np.cumprod(1.0 + rets)
        for i, dt in enumerate(dates):
            c = float(prices[i])
            o = float(prices[i - 1] * (1.0 + 0.001)) if i > 0 else c
            rows.append(
                {
                    "date": dt.date(),
                    "symbol": sym,
                    "market": "CN_ETF",
                    "open": round(o, 4),
                    "high": round(max(o, c) * 1.008, 4),
                    "low": round(min(o, c) * 0.992, 4),
                    "close": round(c, 4),
                    "adj_close": round(c, 4),
                    "volume": 500000.0,
                    "amount": c * 500000.0,
                    "source": "synthetic",
                }
            )
    return pd.DataFrame(rows)


class BacktestAndWalkForwardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bars = _synthetic_universe(420)
        self.symbols = ["ETF_A", "ETF_B", "ETF_G", "ETF_D"]
        self.cost = CostConfig(commission_bps=1.0, minimum_commission=5.0, slippage_bps=5.0)
        self.risk = RiskConfig(max_drawdown_halt=0.25, cooldown_sessions=5)

    def test_cn_lot_rounding_and_minimum_commission_floor(self) -> None:
        spec = StrategySpec(kind="fixed_allocation", rebalance_frequency="quarterly", rebalance_band=0.05)
        rep = run_portfolio_backtest(
            self.bars,
            name="Fixed CN Test",
            market="CN_ETF",
            currency="CNY",
            symbols=self.symbols,
            strategy=spec,
            cost=self.cost,
            risk=self.risk,
            initial_cash=10000.0,
            lot_size=100,
        )
        self.assertFalse(rep.equity_curve.empty)
        self.assertFalse(rep.trades.empty)
        # Every trade must be an exact multiple of 100 shares and pay at least 5 CNY commission
        self.assertTrue((rep.trades["quantity"] % 100 == 0).all())
        self.assertTrue((rep.trades["commission"] >= 5.0).all())
        self.assertIn("benchmark_nav", rep.equity_curve.columns)

    def test_dual_momentum_and_risk_parity_run_cleanly(self) -> None:
        for kind in ("dual_momentum", "risk_parity_trend", "passive_drift"):
            spec = StrategySpec(
                kind=kind,
                rebalance_frequency="never" if kind == "passive_drift" else "monthly",
                rebalance_band=0.05,
                lookback_days=40,
                trend_ma_days=80,
                top_n=2,
                defensive_symbol="ETF_D",
            )
            rep = run_portfolio_backtest(
                self.bars,
                name=f"Test {kind}",
                market="CN_ETF",
                currency="CNY",
                symbols=self.symbols,
                strategy=spec,
                cost=self.cost,
                risk=self.risk,
                initial_cash=10000.0,
                lot_size=100,
            )
            self.assertGreater(rep.metrics["final_nav"], 0.0)
            self.assertGreater(len(rep.yearly_returns), 0)

    def test_drawdown_halt_recovers_after_cooldown_without_deadlock(self) -> None:
        # Force a tight drawdown halt (5%) on ETF_A which crashes mid-series, then verify re-entry happens!
        tight_risk = RiskConfig(max_drawdown_halt=0.05, cooldown_sessions=3)
        spec = StrategySpec(kind="fixed_allocation", target_weights={"ETF_A": 1.0}, rebalance_frequency="weekly", rebalance_band=0.0)
        rep = run_portfolio_backtest(
            self.bars,
            name="DD Recovery Test",
            market="CN_ETF",
            currency="CNY",
            symbols=["ETF_A"],
            strategy=spec,
            cost=self.cost,
            risk=tight_risk,
            initial_cash=10000.0,
            lot_size=100,
        )
        reasons = list(rep.trades["reason"])
        self.assertTrue(any(r.startswith("drawdown_halt") for r in reasons))
        halt_idx = next(i for i, r in enumerate(reasons) if r.startswith("drawdown_halt"))
        # Must have subsequent BUY re-entry after cooldown!
        later_buys = rep.trades.iloc[halt_idx + 1 :]
        self.assertTrue((later_buys["side"] == "BUY").any())

    def test_walk_forward_produces_out_of_sample_folds(self) -> None:
        candidates = {
            "dm": StrategySpec(kind="dual_momentum", rebalance_frequency="monthly", lookback_days=40, trend_ma_days=60, top_n=2, defensive_symbol="ETF_D"),
            "drift": StrategySpec(kind="passive_drift", rebalance_frequency="never", rebalance_band=0.0),
        }
        wf = run_walk_forward(
            self.bars,
            market="CN_ETF",
            currency="CNY",
            symbols=self.symbols,
            candidates=candidates,
            cost=self.cost,
            risk=self.risk,
            train_sessions=160,
            test_sessions=80,
            step_sessions=80,
        )
        self.assertGreaterEqual(wf.summary["fold_count"], 2)
        self.assertIn("mean_oos_sharpe", wf.summary)


if __name__ == "__main__":
    unittest.main()
