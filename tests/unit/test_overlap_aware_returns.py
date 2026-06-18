import unittest

import pandas as pd

from quant_robot.research.overlap import overlap_aware_return_stats


class OverlapAwareReturnStatsTests(unittest.TestCase):
    def test_independent_returns_match_naive_sharpe_when_holding_period_is_one(self) -> None:
        returns = pd.Series([0.01, -0.005, 0.002, 0.004, -0.001, 0.003])

        stats = overlap_aware_return_stats(returns, periods_per_year=252, holding_period=1)

        self.assertEqual(stats["observations"], 6)
        self.assertEqual(stats["max_lag"], 0)
        self.assertFalse(stats["overlap_risk_flag"])
        self.assertAlmostEqual(stats["autocorr_adjusted_sharpe"], stats["naive_sharpe"])
        self.assertAlmostEqual(stats["effective_sample_size"], 6.0)

    def test_positive_autocorrelation_reduces_effective_sample_and_sharpe(self) -> None:
        values = []
        level = 0.01
        for shock in [0.004, 0.003, -0.002, 0.005, -0.001, 0.002, 0.003, -0.002, 0.004, 0.001]:
            level = 0.75 * level + shock
            values.append(level)

        stats = overlap_aware_return_stats(pd.Series(values), periods_per_year=252, holding_period=5)

        self.assertEqual(stats["max_lag"], 4)
        self.assertTrue(stats["overlap_risk_flag"])
        self.assertLess(stats["effective_sample_size"], stats["observations"])
        self.assertLess(stats["autocorr_adjusted_sharpe"], stats["naive_sharpe"])
        self.assertGreater(stats["variance_inflation"], 1.0)

    def test_hold20_defaults_to_nineteen_lags_and_keeps_raw_autocorrelations(self) -> None:
        returns = pd.Series([0.001 * ((idx % 7) - 2) for idx in range(40)])

        stats = overlap_aware_return_stats(returns, periods_per_year=252, holding_period=20)

        self.assertEqual(stats["max_lag"], 19)
        self.assertEqual(len(stats["autocorrelations"]), 19)
        self.assertTrue(stats["overlap_risk_flag"])
        self.assertIn("newey_west_standard_error_mean", stats)

    def test_empty_or_constant_returns_are_reported_as_unusable(self) -> None:
        empty = overlap_aware_return_stats(pd.Series([], dtype=float), holding_period=20)
        constant = overlap_aware_return_stats(pd.Series([0.001, 0.001, 0.001]), holding_period=20)

        self.assertEqual(empty["observations"], 0)
        self.assertFalse(empty["usable"])
        self.assertFalse(constant["usable"])
        self.assertEqual(constant["naive_sharpe"], 0.0)


if __name__ == "__main__":
    unittest.main()

