import unittest
from unittest.mock import patch

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.paper.simulator import PaperSimulationConfig, run_paper_simulation


class PaperDailyValuationTests(unittest.TestCase):
    def simulate(self, prices, *, rebalance_interval=3, start_date=None, end_date=None, initial_positions=None, minimum_commission=0):
        bars = load_demo_market_bars()
        bars = bars[bars.asset_id.eq("CN_ETF_XSHG_510300")].head(len(prices)).copy()
        for column in ("open", "high", "low", "close", "adj_close"):
            bars[column] = prices
        factors = bars[["date", "asset_id", "market"]].copy()
        factors["factor_name"] = "synthetic_constant"
        factors["factor_value"] = 1.0
        with patch("quant_robot.paper.simulator._compute_factors", return_value=factors):
            result = run_paper_simulation(bars, PaperSimulationConfig(
                market="CN_ETF", factor_name="synthetic_constant", top_n=1,
                rebalance_interval=rebalance_interval, initial_cash=3000,
                commission_bps=0, slippage_bps=0, max_drawdown_guard=0.08,
                guard_cooldown_periods=2, start_date=start_date, end_date=end_date,
                minimum_commission=minimum_commission,
            ), initial_positions=initial_positions)
        return result, [str(date) for date in bars.date]

    def test_between_rebalances_drawdown_is_observed_and_triggers_guard(self):
        result, dates = self.simulate([10, 10, 5, 10, 10, 10, 10, 10, 10])
        self.assertEqual([row["date"] for row in result["equity_curve"]], dates)
        self.assertAlmostEqual(result["metrics"]["max_equity_drawdown"], -0.5)
        self.assertEqual(result["guard_events"][0]["date"], dates[2])
        self.assertAlmostEqual(result["guard_events"][0]["drawdown"], -0.5)
        self.assertEqual([row["signal_date"] for row in result["snapshots"]], dates[:-1:3])
        self.assertEqual(result["request"]["periods_per_year"], 252)

    def test_last_day_is_valued_without_forcing_an_extra_rebalance(self):
        result, dates = self.simulate([10, 10, 10, 10, 10, 10, 10, 10, 8])
        self.assertEqual(result["equity_curve"][-1]["date"], dates[-1])
        self.assertAlmostEqual(result["metrics"]["ending_equity"], 2400)
        self.assertAlmostEqual(result["metrics"]["total_return"], -0.2)
        self.assertEqual(len(result["snapshots"]), 3)
        self.assertEqual(len(result["fills"]), 1)

    def test_intraperiod_guard_blocks_the_next_scheduled_buy_and_allows_selling(self):
        bars = load_demo_market_bars()
        assets = list(bars[bars.market.eq("CN_ETF")].asset_id.unique())[:2]
        bars = bars[bars.asset_id.isin(assets)].groupby("asset_id").head(9).copy()
        dates = sorted(bars.date.unique())
        for column in ("open", "high", "low", "close", "adj_close"):
            bars[column] = 10.0
            bars.loc[bars.asset_id.eq(assets[0]) & bars.date.eq(dates[2]), column] = 5.0
        factors = pd.DataFrame([
            {"date": date, "asset_id": assets[0 if index < 3 else 1], "market": "CN_ETF",
             "factor_name": "synthetic_rotation", "factor_value": 1.0}
            for index, date in enumerate(dates)
        ])
        with patch("quant_robot.paper.simulator._compute_factors", return_value=factors):
            result = run_paper_simulation(bars, PaperSimulationConfig(
                market="CN_ETF", factor_name="synthetic_rotation", top_n=1,
                rebalance_interval=3, initial_cash=3000, commission_bps=0, slippage_bps=0,
                max_drawdown_guard=0.08, guard_cooldown_periods=2,
            ))
        self.assertEqual([(fill["asset_id"], fill["side"]) for fill in result["fills"]],
                         [(assets[0], "buy"), (assets[0], "sell")])
        blocked = [event for event in result["guard_events"] if event.get("blocked_buy_intents", 0)]
        self.assertEqual([event["date"] for event in blocked], [str(dates[3]), str(dates[6])])
        self.assertEqual(result["metrics"]["ending_cash"], 3000)

    def test_daily_return_statistics_do_not_count_the_baseline_as_a_holding_day(self):
        result, _ = self.simulate([10, 10, 11], rebalance_interval=1)
        self.assertAlmostEqual(result["metrics"]["annualized_return"], 1.1 ** (252 / 2) - 1)

    def test_first_fill_cost_is_included_in_both_drawdown_metrics(self):
        result, _ = self.simulate([10, 10, 10, 10], minimum_commission=5)
        self.assertAlmostEqual(result["metrics"]["max_drawdown"], -5 / 3000)
        self.assertAlmostEqual(result["metrics"]["max_equity_drawdown"], -5 / 3000)

    def test_single_date_window_values_initial_holdings_without_trading(self):
        result, _ = self.simulate([10, 10, 12], start_date="2024-01-04", end_date="2024-01-04",
                                 initial_positions=pd.DataFrame([{"asset_id": "CN_ETF_XSHG_510300", "quantity": 100}]))
        self.assertEqual(len(result["equity_curve"]), 1)
        self.assertEqual(result["metrics"]["starting_equity"], 4200)
        self.assertEqual(result["metrics"]["ending_equity"], 4200)
        self.assertEqual(result["fills"], [])
