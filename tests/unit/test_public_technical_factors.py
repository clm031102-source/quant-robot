import unittest

import pandas as pd

from quant_robot.factors.public_technical import (
    PUBLIC_TECHNICAL_FACTOR_NAMES,
    compute_public_technical_factors,
)
from quant_robot.schema.factors import FACTOR_COLUMNS


class PublicTechnicalFactorTests(unittest.TestCase):
    def test_public_technical_factors_export_long_schema_and_known_public_names(self):
        factors = compute_public_technical_factors(_bars([10 + index for index in range(35)]))

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(PUBLIC_TECHNICAL_FACTOR_NAMES))
        self.assertEqual(
            PUBLIC_TECHNICAL_FACTOR_NAMES,
            (
                "rsi_reversal_14",
                "bollinger_reversal_20",
                "donchian_position_20",
                "macd_histogram_12_26_9",
            ),
        )

    def test_public_technical_factors_use_only_current_and_past_rows(self):
        prices = [10 + index * 0.2 for index in range(30)] + [2000.0]
        baseline = compute_public_technical_factors(_bars(prices[:30]))
        with_future = compute_public_technical_factors(_bars(prices))

        before_future = with_future[with_future["date"] <= pd.Timestamp("2024-02-09").date()]
        pd.testing.assert_frame_equal(
            baseline.reset_index(drop=True),
            before_future.reset_index(drop=True),
            check_like=True,
        )

    def test_public_technical_factors_can_compute_only_requested_factor_names(self):
        factors = compute_public_technical_factors(
            _bars([10 + index for index in range(25)]),
            factor_names=("donchian_position_20",),
        )

        self.assertEqual(set(factors["factor_name"]), {"donchian_position_20"})
        self.assertEqual(set(factors["lookback_window"]), {20})

    def test_public_technical_factors_reject_unknown_requested_factor_names(self):
        with self.assertRaisesRegex(ValueError, "Unsupported public technical factor_names"):
            compute_public_technical_factors(_bars([10 + index for index in range(25)]), factor_names=("missing",))

    def test_rsi_reversal_is_higher_for_recent_losses_than_recent_gains(self):
        falling = compute_public_technical_factors(
            _bars([30 - index for index in range(18)]),
            factor_names=("rsi_reversal_14",),
        )
        rising = compute_public_technical_factors(
            _bars([10 + index for index in range(18)]),
            factor_names=("rsi_reversal_14",),
        )

        falling_last = falling.dropna(subset=["factor_value"]).iloc[-1]["factor_value"]
        rising_last = rising.dropna(subset=["factor_value"]).iloc[-1]["factor_value"]
        self.assertGreater(falling_last, rising_last)

    def test_bollinger_reversal_rewards_prices_below_their_rolling_band_center(self):
        prices = [100.0] * 19 + [90.0]
        factors = compute_public_technical_factors(_bars(prices), factor_names=("bollinger_reversal_20",))

        last = factors.dropna(subset=["factor_value"]).iloc[-1]["factor_value"]
        self.assertGreater(last, 0.0)

    def test_donchian_position_is_one_at_rolling_breakout_high(self):
        factors = compute_public_technical_factors(
            _bars([10 + index for index in range(22)]),
            factor_names=("donchian_position_20",),
        )

        last = factors.dropna(subset=["factor_value"]).iloc[-1]["factor_value"]
        self.assertAlmostEqual(last, 1.0)

    def test_macd_histogram_is_positive_during_persistent_uptrend(self):
        prices = [10 * (1.02**index) for index in range(45)]
        factors = compute_public_technical_factors(_bars(prices), factor_names=("macd_histogram_12_26_9",))

        last = factors.dropna(subset=["factor_value"]).iloc[-1]["factor_value"]
        self.assertGreater(last, 0.0)


def _bars(prices: list[float]) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=len(prices), freq="B")
    return pd.DataFrame(
        {
            "asset_id": ["CN_XSHG_000001"] * len(prices),
            "market": ["CN"] * len(prices),
            "date": dates.date,
            "adj_close": prices,
            "high": prices,
            "low": prices,
            "volume": [1_000_000 + index * 1000 for index in range(len(prices))],
            "amount": [price * (1_000_000 + index * 1000) for index, price in enumerate(prices)],
        }
    )


if __name__ == "__main__":
    unittest.main()
