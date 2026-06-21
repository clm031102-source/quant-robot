import unittest

import pandas as pd

from quant_robot.backtest.costs import round_trip_cost
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

        result = run_factor_backtest(factors, bars, top_n=1, cost_bps=0.0, portfolio_scope="market")

        self.assertEqual(set(result.trades["asset_id"]), {"US_B", "CN_B"})

    def test_backtest_global_scope_allocates_one_portfolio_across_markets(self):
        factors = pd.DataFrame(
            {
                "date": [pd.Timestamp("2024-01-01").date()] * 4,
                "asset_id": ["US_A", "US_B", "CN_A", "CN_B"],
                "market": ["US", "US", "CN", "CN"],
                "factor_name": ["momentum_1"] * 4,
                "factor_value": [1.0, 4.0, 2.0, 3.0],
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

        result = run_factor_backtest(factors, bars, top_n=2, cost_bps=0.0, portfolio_scope="global")

        self.assertEqual(set(result.trades["asset_id"]), {"US_B", "CN_B"})
        self.assertAlmostEqual(float(result.trades["target_weight"].sum()), 1.0)
        self.assertAlmostEqual(result.metrics["turnover"], 1.0)

    def test_backtest_can_select_industry_neutral_top_n(self):
        factors = pd.DataFrame(
            {
                "date": [pd.Timestamp("2024-01-01").date()] * 4,
                "asset_id": ["TECH_A", "TECH_B", "BANK_A", "BANK_B"],
                "market": ["CN"] * 4,
                "factor_name": ["formula"] * 4,
                "factor_value": [100.0, 99.0, 2.0, 1.0],
                "industry": ["Tech", "Tech", "Bank", "Bank"],
            }
        )
        bars = pd.DataFrame(
            {
                "date": list(pd.date_range("2024-01-01", periods=3).date) * 4,
                "asset_id": ["TECH_A"] * 3 + ["TECH_B"] * 3 + ["BANK_A"] * 3 + ["BANK_B"] * 3,
                "market": ["CN"] * 12,
                "adj_close": [10.0, 10.0, 11.0, 10.0, 10.0, 12.0, 10.0, 10.0, 13.0, 10.0, 10.0, 14.0],
            }
        )

        raw = run_factor_backtest(factors, bars, top_n=2, cost_bps=0.0)
        neutral = run_factor_backtest(
            factors,
            bars,
            top_n=2,
            cost_bps=0.0,
            selection_method="industry_neutral_top_n",
        )

        self.assertEqual(set(raw.trades["asset_id"]), {"TECH_A", "TECH_B"})
        self.assertEqual(set(neutral.trades["asset_id"]), {"TECH_A", "BANK_A"})
        self.assertEqual(set(neutral.positions["industry"]), {"Tech", "Bank"})
        self.assertAlmostEqual(float(neutral.trades["target_weight"].sum()), 1.0)

    def test_backtest_holding_period_controls_exit_date(self):
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
                "date": pd.date_range("2024-01-01", periods=5).date,
                "asset_id": ["A"] * 5,
                "market": ["US"] * 5,
                "adj_close": [100.0, 101.0, 103.0, 107.0, 111.0],
            }
        )

        result = run_factor_backtest(factors, bars, top_n=1, cost_bps=0.0, holding_period=2)

        self.assertEqual(result.trades.iloc[0]["entry_date"], pd.Timestamp("2024-01-02").date())
        self.assertEqual(result.trades.iloc[0]["exit_date"], pd.Timestamp("2024-01-04").date())
        self.assertAlmostEqual(result.trades.iloc[0]["gross_return"], 107.0 / 101.0 - 1.0)

    def test_backtest_scales_daily_signal_sleeves_for_multi_day_holding_period(self):
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
                "date": pd.date_range("2024-01-01", periods=6).date,
                "asset_id": ["A"] * 6,
                "market": ["US"] * 6,
                "adj_close": [100.0, 101.0, 103.0, 107.0, 111.0, 113.0],
            }
        )

        result = run_factor_backtest(factors, bars, top_n=1, cost_bps=0.0, holding_period=2)

        self.assertTrue(all(abs(weight - 0.5) < 1e-9 for weight in result.trades["target_weight"]))
        self.assertAlmostEqual(result.metrics["turnover"], 0.5)

    def test_backtest_metrics_include_overlap_aware_statistics_for_multi_day_holds(self):
        factors = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=5).date,
                "asset_id": ["A"] * 5,
                "market": ["US"] * 5,
                "factor_name": ["momentum_1"] * 5,
                "factor_value": [1.0] * 5,
            }
        )
        bars = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=9).date,
                "asset_id": ["A"] * 9,
                "market": ["US"] * 9,
                "adj_close": [100.0, 101.0, 103.0, 102.0, 106.0, 109.0, 108.0, 112.0, 115.0],
            }
        )

        result = run_factor_backtest(factors, bars, top_n=1, cost_bps=0.0, holding_period=3)

        self.assertIn("overlap_naive_sharpe", result.metrics)
        self.assertIn("overlap_autocorr_adjusted_sharpe", result.metrics)
        self.assertIn("overlap_newey_west_t_stat_mean", result.metrics)
        self.assertIn("overlap_effective_sample_size", result.metrics)
        self.assertIn("overlap_risk_flag", result.metrics)
        self.assertTrue(result.metrics["overlap_risk_flag"])
        self.assertLessEqual(result.metrics["overlap_effective_sample_size"], result.metrics["overlap_observations"])

    def test_backtest_does_not_scale_non_overlapping_sparse_rebalance_sleeves(self):
        factors = pd.DataFrame(
            {
                "date": [pd.Timestamp("2024-01-01").date(), pd.Timestamp("2024-01-03").date()],
                "asset_id": ["A", "A"],
                "market": ["US", "US"],
                "factor_name": ["momentum_1", "momentum_1"],
                "factor_value": [1.0, 1.0],
            }
        )
        bars = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=7).date,
                "asset_id": ["A"] * 7,
                "market": ["US"] * 7,
                "adj_close": [100.0, 101.0, 103.0, 107.0, 111.0, 113.0, 117.0],
            }
        )

        result = run_factor_backtest(
            factors,
            bars,
            top_n=1,
            cost_bps=0.0,
            holding_period=2,
            rebalance_interval=2,
        )

        self.assertTrue(all(abs(weight - 1.0) < 1e-9 for weight in result.trades["target_weight"]))
        self.assertAlmostEqual(result.metrics["turnover"], 1.0)

    def test_backtest_scales_target_gross_exposure(self):
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
                "asset_id": ["A"] * 3,
                "market": ["US"] * 3,
                "adj_close": [100.0, 101.0, 103.0],
            }
        )

        result = run_factor_backtest(factors, bars, top_n=1, cost_bps=0.0, target_gross_exposure=0.8)

        self.assertAlmostEqual(float(result.trades.iloc[0]["target_weight"]), 0.8)
        self.assertAlmostEqual(result.metrics["turnover"], 0.8)

    def test_backtest_records_capacity_and_market_impact_cost_evidence(self):
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
                "asset_id": ["A"] * 3,
                "market": ["US"] * 3,
                "adj_close": [100.0, 100.0, 110.0],
                "amount": [500.0, 500.0, 500.0],
            }
        )

        result = run_factor_backtest(
            factors,
            bars,
            top_n=1,
            cost_bps=5.0,
            market_impact_bps=10.0,
            portfolio_value=1000.0,
            max_participation_rate=0.10,
        )

        trade = result.trades.iloc[0]
        self.assertGreater(trade["participation_rate"], 0.10)
        self.assertTrue(bool(trade["capacity_limited"]))
        self.assertGreater(trade["cost_rate"], round_trip_cost(5.0))
        self.assertEqual(result.metrics["capacity_limited_trades"], 1)
        self.assertGreater(result.metrics["max_participation_rate"], 0.10)

    def test_backtest_flags_extreme_single_trade_returns(self):
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
                "asset_id": ["A"] * 3,
                "market": ["US"] * 3,
                "adj_close": [100.0, 100.0, 700.0],
            }
        )

        result = run_factor_backtest(factors, bars, top_n=1, cost_bps=0.0)

        self.assertAlmostEqual(result.metrics["max_trade_gross_return"], 6.0)
        self.assertAlmostEqual(result.metrics["max_abs_trade_gross_return"], 6.0)
        self.assertAlmostEqual(result.metrics["p99_abs_trade_gross_return"], 6.0)
        self.assertTrue(result.metrics["extreme_trade_return_flag"])


if __name__ == "__main__":
    unittest.main()
