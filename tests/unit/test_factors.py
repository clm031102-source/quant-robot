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


if __name__ == "__main__":
    unittest.main()
