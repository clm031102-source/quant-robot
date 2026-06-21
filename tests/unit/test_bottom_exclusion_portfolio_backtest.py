import unittest

import pandas as pd

from quant_robot.ops.bottom_exclusion_portfolio_backtest import run_bottom_exclusion_portfolio_backtest


class BottomExclusionPortfolioBacktestTests(unittest.TestCase):
    def test_bottom_exclusion_improves_relative_return_when_bottom_bucket_loses(self):
        factors, labels, bars = _inputs(bottom_return=-0.05, kept_return=0.02, amount=1_000_000_000.0)

        result = run_bottom_exclusion_portfolio_backtest(
            factors,
            labels,
            bars,
            bottom_quantile=0.2,
            rebalance_interval=1,
            holding_period=1,
            cost_bps=0.0,
            market_impact_bps=0.0,
            portfolio_value=1_000_000.0,
            min_positive_relative_fold_rate=0.5,
        )

        row = result["leaderboard"][0]
        self.assertEqual(row["factor_name"], "tail_filter")
        self.assertEqual(row["classification"], "costed_risk_filter_candidate")
        self.assertGreater(row["total_return"], row["benchmark_total_return"])
        self.assertGreater(row["relative_return"], 0.0)
        self.assertEqual(row["capacity_limited_trades"], 0)

    def test_costs_reduce_net_return(self):
        factors, labels, bars = _inputs(bottom_return=-0.05, kept_return=0.02, amount=1_000_000_000.0)

        result = run_bottom_exclusion_portfolio_backtest(
            factors,
            labels,
            bars,
            bottom_quantile=0.2,
            rebalance_interval=1,
            holding_period=1,
            cost_bps=10.0,
            market_impact_bps=0.0,
            portfolio_value=1_000_000.0,
            min_positive_relative_fold_rate=0.5,
        )

        row = result["leaderboard"][0]
        self.assertLess(row["total_return"], row["gross_total_return"])
        self.assertGreater(row["avg_cost_rate"], 0.0)

    def test_capacity_limited_rows_are_reported(self):
        factors, labels, bars = _inputs(bottom_return=-0.05, kept_return=0.02, amount=1_000.0)

        result = run_bottom_exclusion_portfolio_backtest(
            factors,
            labels,
            bars,
            bottom_quantile=0.2,
            rebalance_interval=1,
            holding_period=1,
            cost_bps=0.0,
            market_impact_bps=20.0,
            max_participation_rate=0.01,
            portfolio_value=1_000_000.0,
            min_positive_relative_fold_rate=0.5,
        )

        row = result["leaderboard"][0]
        self.assertGreater(row["capacity_limited_trades"], 0)
        self.assertEqual(row["classification"], "capacity_limited_risk_filter_candidate")

    def test_min_entry_amount_filter_removes_illiquid_capacity_outliers_before_selection(self):
        factors, labels, bars = _inputs(bottom_return=-0.05, kept_return=0.02, amount=1_000_000_000.0)
        bars.loc[bars["asset_id"] == "asset_1", "amount"] = 1_000.0

        result = run_bottom_exclusion_portfolio_backtest(
            factors,
            labels,
            bars,
            bottom_quantile=0.2,
            rebalance_interval=1,
            holding_period=1,
            cost_bps=0.0,
            market_impact_bps=20.0,
            max_participation_rate=0.01,
            min_entry_amount=10_000_000.0,
            portfolio_value=1_000_000.0,
            min_positive_relative_fold_rate=0.5,
        )

        row = result["leaderboard"][0]
        self.assertEqual(row["capacity_limited_trades"], 0)
        self.assertEqual(row["classification"], "costed_risk_filter_candidate")
        self.assertLess(row["average_holdings"], 4.0)

    def test_positive_relative_return_without_required_sharpe_is_only_a_research_lead(self):
        factors, labels, bars = _inputs(bottom_return=-0.05, kept_return=0.02, amount=1_000_000_000.0)

        result = run_bottom_exclusion_portfolio_backtest(
            factors,
            labels,
            bars,
            bottom_quantile=0.2,
            rebalance_interval=1,
            holding_period=1,
            cost_bps=0.0,
            market_impact_bps=0.0,
            portfolio_value=1_000_000.0,
            min_positive_relative_fold_rate=0.5,
            min_overlap_adjusted_sharpe=1_000_000_000.0,
        )

        row = result["leaderboard"][0]
        self.assertGreater(row["relative_return"], 0.0)
        self.assertEqual(row["classification"], "research_lead_risk_filter")


def _inputs(*, bottom_return: float, kept_return: float, amount: float):
    factor_rows = []
    label_rows = []
    bar_rows = []
    dates = pd.date_range("2024-01-02", periods=8, freq="D")
    for day_index, day in enumerate(dates):
        for asset_index in range(5):
            asset_id = f"asset_{asset_index}"
            factor_rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "tail_filter",
                    "factor_value": float(asset_index + 1),
                }
            )
            label_rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "horizon": 1,
                    "execution_lag": 1,
                    "forward_return": (bottom_return - 0.001 * (day_index % 3))
                    if asset_index == 0
                    else (kept_return + 0.001 * (day_index % 2)),
                    "entry_date": day.date(),
                    "exit_date": day.date(),
                }
            )
            bar_rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": 10.0,
                    "amount": amount,
                }
            )
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), pd.DataFrame(bar_rows)


if __name__ == "__main__":
    unittest.main()
