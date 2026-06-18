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

    def test_basic_factors_can_compute_only_requested_factor_names(self):
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

        factors = compute_basic_factors(bars, windows=(2, 3), factor_names=("momentum_2",))

        self.assertEqual(set(factors["factor_name"]), {"momentum_2"})
        self.assertEqual(set(factors["lookback_window"]), {2})

    def test_basic_factors_reject_unknown_requested_factor_names(self):
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

        with self.assertRaisesRegex(ValueError, "Unsupported technical factor_names"):
            compute_basic_factors(bars, windows=(2,), factor_names=("momentum_5", "not_a_factor"))

    def test_liquidity_factor_uses_rolling_amihud_window(self):
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

        factors = compute_basic_factors(bars, windows=(2, 3))
        last_date = pd.Timestamp("2024-01-04").date()
        liquidity_2 = factors[
            (factors["date"] == last_date)
            & (factors["factor_name"] == "liquidity_2")
        ].iloc[0]["factor_value"]
        liquidity_3 = factors[
            (factors["date"] == last_date)
            & (factors["factor_name"] == "liquidity_3")
        ].iloc[0]["factor_value"]
        daily_amihud = [
            abs(0.10) / 11000.0,
            abs(-0.10) / 9900.0,
            abs(0.20) / 11880.0,
        ]

        self.assertAlmostEqual(liquidity_2, sum(daily_amihud[-2:]) / 2)
        self.assertAlmostEqual(liquidity_3, sum(daily_amihud) / 3)
        self.assertNotEqual(liquidity_2, liquidity_3)


if __name__ == "__main__":
    unittest.main()
