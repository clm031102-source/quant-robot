import unittest

import pandas as pd

from quant_robot.backtest.engine import run_factor_backtest
from quant_robot.backtest.metrics import max_drawdown, summarize_returns


class BacktestTests(unittest.TestCase):
    def test_backtest_executes_after_signal_date(self):
        factors = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=3).date,
                "asset_id": ["A", "A", "A"],
                "market": ["US", "US", "US"],
                "factor_name": ["momentum_1", "momentum_1", "momentum_1"],
                "factor_value": [1.0, 1.0, 1.0],
            }
        )
        bars = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=4).date,
                "asset_id": ["A", "A", "A", "A"],
                "market": ["US", "US", "US", "US"],
                "adj_close": [100.0, 200.0, 220.0, 242.0],
            }
        )

        result = run_factor_backtest(factors, bars, top_n=1, cost_bps=0.0)

        self.assertEqual(result.trades.iloc[0]["signal_date"], pd.Timestamp("2024-01-01").date())
        self.assertEqual(result.trades.iloc[0]["entry_date"], pd.Timestamp("2024-01-02").date())
        self.assertGreater(result.metrics["total_return"], 0.0)

    def test_costs_reduce_returns(self):
        factors = pd.DataFrame(
            {
                "date": [pd.Timestamp("2024-01-01").date()],
                "asset_id": ["A"],
                "market": ["US"],
                "factor_name": ["momentum_1"],
                "factor_value": [1.0],
            }
        )
        bars = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=3).date,
                "asset_id": ["A", "A", "A"],
                "market": ["US", "US", "US"],
                "adj_close": [100.0, 100.0, 110.0],
            }
        )

        no_cost = run_factor_backtest(factors, bars, top_n=1, cost_bps=0.0)
        with_cost = run_factor_backtest(factors, bars, top_n=1, cost_bps=10.0)

        self.assertLess(with_cost.metrics["total_return"], no_cost.metrics["total_return"])

    def test_metrics_include_drawdown_and_sharpe(self):
        returns = pd.Series([0.1, -0.05, 0.02])

        metrics = summarize_returns(returns)

        self.assertIn("sharpe", metrics)
        self.assertIn("max_drawdown", metrics)
        self.assertLessEqual(max_drawdown(pd.Series([1.0, 1.1, 1.0])), 0.0)

    def test_backtest_selects_top_n_within_each_market(self):
        factors = pd.DataFrame(
            {
                "date": [pd.Timestamp("2024-01-01").date()] * 4,
                "asset_id": ["US_A", "US_B", "CN_A", "CN_B"],
                "market": ["US", "US", "CN", "CN"],
                "factor_name": ["momentum_1"] * 4,
                "factor_value": [1.0, 2.0, 1.0, 2.0],
            }
        )
        bars = pd.DataFrame(
            {
                "date": list(pd.date_range("2024-01-01", periods=3).date) * 4,
                "asset_id": ["US_A"] * 3 + ["US_B"] * 3 + ["CN_A"] * 3 + ["CN_B"] * 3,
                "market": ["US"] * 6 + ["CN"] * 6,
                "adj_close": [10.0, 10.0, 11.0, 10.0, 10.0, 12.0, 10.0, 10.0, 13.0, 10.0, 10.0, 14.0],
            }
        )

        result = run_factor_backtest(factors, bars, top_n=1, cost_bps=0.0)

        self.assertEqual(set(result.trades["asset_id"]), {"US_B", "CN_B"})


if __name__ == "__main__":
    unittest.main()
