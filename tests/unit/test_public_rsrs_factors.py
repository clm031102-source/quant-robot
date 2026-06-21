import unittest

import pandas as pd

from quant_robot.factors.public_rsrs import PUBLIC_RSRS_FACTOR_NAMES, compute_public_rsrs_factors
from quant_robot.schema.factors import FACTOR_COLUMNS


class PublicRsrsFactorTests(unittest.TestCase):
    def test_public_rsrs_factors_export_long_schema_and_names(self):
        factors = compute_public_rsrs_factors(_bars(90))

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(PUBLIC_RSRS_FACTOR_NAMES))
        self.assertEqual(
            PUBLIC_RSRS_FACTOR_NAMES,
            (
                "rsrs_slope_18",
                "rsrs_zscore_18_60",
                "rsrs_right_skew_18_60",
                "rsrs_reversal_18_60",
            ),
        )

    def test_public_rsrs_factors_use_only_current_and_past_rows(self):
        baseline = compute_public_rsrs_factors(_bars(90))
        with_future = pd.concat([_bars(90), _future_outlier()], ignore_index=True)
        factors_with_future = compute_public_rsrs_factors(with_future)

        before_future = factors_with_future[factors_with_future["date"] <= pd.Timestamp("2024-05-03").date()]
        pd.testing.assert_frame_equal(
            baseline.reset_index(drop=True),
            before_future.reset_index(drop=True),
            check_like=True,
        )

    def test_rsrs_slope_reflects_high_low_regression_slope(self):
        factors = compute_public_rsrs_factors(_bars(40), factor_names=("rsrs_slope_18",))

        last = factors.dropna(subset=["factor_value"]).iloc[-1]["factor_value"]
        self.assertGreater(last, 1.0)

    def test_public_rsrs_rejects_unknown_factor_names(self):
        with self.assertRaisesRegex(ValueError, "Unsupported public RSRS factor_names"):
            compute_public_rsrs_factors(_bars(40), factor_names=("missing",))


def _bars(days: int) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=days, freq="B")
    lows = [10.0 + index * 0.1 for index in range(days)]
    highs = [low * 1.15 + 1.0 for low in lows]
    close = [(high + low) / 2.0 for high, low in zip(highs, lows)]
    return pd.DataFrame(
        {
            "asset_id": ["CN_XSHG_000001"] * days,
            "market": ["CN"] * days,
            "date": dates.date,
            "adj_close": close,
            "high": highs,
            "low": lows,
            "volume": [1_000_000 + index * 1000 for index in range(days)],
            "amount": [price * (1_000_000 + index * 1000) for index, price in enumerate(close)],
        }
    )


def _future_outlier() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "asset_id": ["CN_XSHG_000001"],
            "market": ["CN"],
            "date": [pd.Timestamp("2024-05-06").date()],
            "adj_close": [1000.0],
            "high": [5000.0],
            "low": [1.0],
            "volume": [1_000_000],
            "amount": [1_000_000_000.0],
        }
    )


if __name__ == "__main__":
    unittest.main()
