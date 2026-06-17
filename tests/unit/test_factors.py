import unittest

import pandas as pd

from quant_robot.factors.technical import compute_basic_factors


class FactorTests(unittest.TestCase):
    def test_basic_factors_use_only_current_and_past_rows(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["A"] * 6,
                "market": ["US"] * 6,
                "date": pd.date_range("2024-01-01", periods=6).date,
                "adj_close": [10.0, 11.0, 12.0, 13.0, 14.0, 1000.0],
                "close": [10.0, 11.0, 12.0, 13.0, 14.0, 1000.0],
                "volume": [100, 110, 120, 130, 140, 150],
                "amount": [1000, 1210, 1440, 1690, 1960, 150000],
            }
        )
        baseline = compute_basic_factors(bars.iloc[:5], windows=(3,))
        with_future = compute_basic_factors(bars, windows=(3,))

        before_future = with_future[with_future["date"] <= pd.Timestamp("2024-01-05").date()]
        pd.testing.assert_frame_equal(
            baseline.reset_index(drop=True),
            before_future.reset_index(drop=True),
            check_like=True,
        )

    def test_momentum_factor_value(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["A"] * 4,
                "market": ["US"] * 4,
                "date": pd.date_range("2024-01-01", periods=4).date,
                "adj_close": [100.0, 110.0, 121.0, 133.1],
                "volume": [100.0, 100.0, 100.0, 100.0],
                "amount": [10000.0, 11000.0, 12100.0, 13310.0],
            }
        )

        factors = compute_basic_factors(bars, windows=(2,))
        row = factors[(factors["date"] == pd.Timestamp("2024-01-03").date()) & (factors["factor_name"] == "momentum_2")].iloc[0]

        self.assertAlmostEqual(row["factor_value"], 0.21)

    def test_risk_adjusted_momentum_divides_momentum_by_realized_volatility(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["A"] * 4,
                "market": ["US"] * 4,
                "date": pd.date_range("2024-01-01", periods=4).date,
                "adj_close": [100.0, 110.0, 99.0, 118.8],
                "volume": [100.0, 100.0, 100.0, 100.0],
                "amount": [10000.0, 11000.0, 9900.0, 11880.0],
            }
        )

        factors = compute_basic_factors(bars, windows=(2,))
        matches = factors[
            (factors["date"] == pd.Timestamp("2024-01-03").date())
            & (factors["factor_name"] == "risk_adjusted_momentum_2")
        ]

        self.assertEqual(len(matches), 1)
        row = matches.iloc[0]
        self.assertAlmostEqual(row["factor_value"], -0.1)

    def test_factor_output_is_long_schema(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["A"] * 3,
                "market": ["US"] * 3,
                "date": pd.date_range("2024-01-01", periods=3).date,
                "adj_close": [100.0, 101.0, 102.0],
                "volume": [100.0, 120.0, 140.0],
                "amount": [10000.0, 12120.0, 14280.0],
            }
        )

        factors = compute_basic_factors(bars, windows=(2,))

        self.assertEqual(
            list(factors.columns),
            ["date", "asset_id", "market", "factor_name", "factor_value", "lookback_window"],
        )
        self.assertIn("volatility_2", set(factors["factor_name"]))
        self.assertIn("low_volatility_2", set(factors["factor_name"]))
        self.assertIn("low_downside_volatility_2", set(factors["factor_name"]))
        self.assertIn("drawdown_resilience_2", set(factors["factor_name"]))
        self.assertIn("liquidity_resilience_2", set(factors["factor_name"]))
        self.assertIn("amount_stability_2", set(factors["factor_name"]))

    def test_defensive_and_capacity_factors_have_selection_friendly_direction(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["A"] * 4,
                "market": ["CN_ETF"] * 4,
                "date": pd.date_range("2024-01-01", periods=4).date,
                "adj_close": [100.0, 110.0, 105.0, 115.0],
                "volume": [100.0, 100.0, 100.0, 100.0],
                "amount": [10000.0, 20000.0, 10000.0, 10000.0],
            }
        )

        factors = compute_basic_factors(bars, windows=(2,))
        rows = factors[factors["date"] == pd.Timestamp("2024-01-03").date()]
        values = dict(zip(rows["factor_name"], rows["factor_value"], strict=True))

        self.assertAlmostEqual(values["drawdown_resilience_2"], 105.0 / 110.0 - 1.0)
        self.assertLessEqual(values["low_volatility_2"], 0.0)
        self.assertLessEqual(values["low_downside_volatility_2"], 0.0)
        self.assertLessEqual(values["liquidity_resilience_2"], 0.0)
        self.assertLessEqual(values["amount_stability_2"], 0.0)

    def test_composite_factors_rank_cross_sectional_confirmation_components(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["A", "A", "A", "B", "B", "B"],
                "market": ["CN_ETF"] * 6,
                "date": list(pd.date_range("2024-01-01", periods=3).date) * 2,
                "adj_close": [100.0, 110.0, 120.0, 100.0, 90.0, 80.0],
                "volume": [100.0, 110.0, 120.0, 100.0, 90.0, 80.0],
                "amount": [10000.0, 12100.0, 14400.0, 10000.0, 8100.0, 6400.0],
            }
        )

        factors = compute_basic_factors(bars, windows=(2,))
        latest = factors[factors["date"] == pd.Timestamp("2024-01-03").date()]
        names = set(latest["factor_name"])

        self.assertIn("trend_resilience_2", names)
        self.assertIn("risk_confirmed_momentum_2", names)
        self.assertIn("defensive_reversal_2", names)
        self.assertIn("liquidity_confirmed_breakout_2", names)
        trend = latest[latest["factor_name"] == "trend_resilience_2"].set_index("asset_id")["factor_value"]
        breakout = latest[latest["factor_name"] == "liquidity_confirmed_breakout_2"].set_index("asset_id")[
            "factor_value"
        ]
        self.assertGreater(trend["A"], trend["B"])
        self.assertGreater(breakout["A"], breakout["B"])

    def test_cross_sectional_momentum_dispersion_factors_rank_relative_leadership(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["A", "A", "A", "A", "B", "B", "B", "B"],
                "market": ["CN_ETF"] * 8,
                "date": list(pd.date_range("2024-01-01", periods=4).date) * 2,
                "adj_close": [100.0, 105.0, 110.0, 120.0, 100.0, 96.0, 92.0, 88.0],
                "volume": [100.0, 110.0, 120.0, 130.0, 100.0, 95.0, 90.0, 85.0],
                "amount": [10000.0, 11550.0, 13200.0, 15600.0, 10000.0, 9120.0, 8280.0, 7480.0],
            }
        )

        factors = compute_basic_factors(bars, windows=(3,))
        latest = factors[factors["date"] == pd.Timestamp("2024-01-04").date()]
        relative = latest[latest["factor_name"] == "market_relative_strength_3"].set_index("asset_id")["factor_value"]
        breakout = latest[latest["factor_name"] == "momentum_dispersion_breakout_3"].set_index("asset_id")[
            "factor_value"
        ]

        self.assertGreater(relative["A"], 0.0)
        self.assertLess(relative["B"], 0.0)
        self.assertGreater(breakout["A"], breakout["B"])

    def test_structure_shift_factors_capture_recovery_and_demand_pressure(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["A"] * 5,
                "market": ["CN_ETF"] * 5,
                "date": pd.date_range("2024-01-01", periods=5).date,
                "adj_close": [100.0, 70.0, 77.0, 84.0, 92.0],
                "volume": [100.0, 90.0, 95.0, 150.0, 220.0],
                "amount": [10000.0, 6300.0, 7315.0, 12600.0, 20240.0],
            }
        )

        factors = compute_basic_factors(bars, windows=(4,))
        recovery_rows = factors[factors["date"] == pd.Timestamp("2024-01-04").date()]
        latest_rows = factors[factors["date"] == pd.Timestamp("2024-01-05").date()]
        recovery_values = dict(zip(recovery_rows["factor_name"], recovery_rows["factor_value"], strict=True))
        latest_values = dict(zip(latest_rows["factor_name"], latest_rows["factor_value"], strict=True))

        self.assertGreater(recovery_values["crash_recovery_4"], 0.0)
        self.assertGreater(latest_values["recovery_quality_4"], 0.0)
        self.assertGreater(latest_values["demand_pressure_4"], 0.0)
        self.assertGreater(latest_values["quiet_accumulation_4"], 0.0)

    def test_liquidity_gated_factors_exclude_thin_cross_sectional_assets(self):
        dates = list(pd.date_range("2024-01-01", periods=5).date)
        bars = pd.DataFrame(
            {
                "asset_id": ["A"] * 5 + ["B"] * 5,
                "market": ["CN_ETF"] * 10,
                "date": dates + dates,
                "adj_close": [100.0, 102.0, 104.0, 106.0, 108.0, 100.0, 102.0, 104.0, 106.0, 108.0],
                "volume": [10000.0, 10100.0, 10200.0, 10300.0, 10400.0, 10.0, 11.0, 12.0, 13.0, 14.0],
                "amount": [1000000.0, 1030200.0, 1060800.0, 1091800.0, 1123200.0, 1000.0, 1122.0, 1248.0, 1378.0, 1512.0],
            }
        )

        factors = compute_basic_factors(bars, windows=(4,))
        latest = factors[factors["date"] == pd.Timestamp("2024-01-05").date()]
        liquid_demand = latest[latest["factor_name"] == "liquid_demand_pressure_4"]
        liquid_relative = latest[latest["factor_name"] == "liquid_market_relative_strength_4"]

        self.assertIn("average_amount_4", set(latest["factor_name"]))
        self.assertEqual(set(liquid_demand["asset_id"]), {"A"})
        self.assertEqual(set(liquid_relative["asset_id"]), {"A"})


if __name__ == "__main__":
    unittest.main()
