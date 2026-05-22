import unittest

import pandas as pd

from quant_robot.research.groups import quantile_group_returns
from quant_robot.research.ic import compute_ic
from quant_robot.research.long_short import long_short_returns


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.factors = pd.DataFrame(
            {
                "date": [pd.Timestamp("2024-01-01").date()] * 4,
                "asset_id": ["A", "B", "C", "D"],
                "market": ["US"] * 4,
                "factor_name": ["momentum_2"] * 4,
                "factor_value": [1.0, 2.0, 3.0, 4.0],
                "lookback_window": [2] * 4,
            }
        )
        self.labels = pd.DataFrame(
            {
                "date": [pd.Timestamp("2024-01-01").date()] * 4,
                "asset_id": ["A", "B", "C", "D"],
                "market": ["US"] * 4,
                "horizon": [1] * 4,
                "execution_lag": [1] * 4,
                "forward_return": [0.01, 0.02, 0.03, 0.04],
            }
        )

    def test_compute_ic_and_rank_ic(self):
        result = compute_ic(self.factors, self.labels)

        self.assertAlmostEqual(result.loc[0, "ic"], 1.0)
        self.assertAlmostEqual(result.loc[0, "rank_ic"], 1.0)

    def test_quantile_group_returns(self):
        result = quantile_group_returns(self.factors, self.labels, quantiles=2)
        group_returns = dict(zip(result["quantile"], result["mean_forward_return"], strict=True))

        self.assertAlmostEqual(group_returns[1], 0.015)
        self.assertAlmostEqual(group_returns[2], 0.035)

    def test_long_short_returns(self):
        result = long_short_returns(self.factors, self.labels, quantiles=2)

        self.assertAlmostEqual(result.loc[0, "long_short_return"], 0.02)

    def test_ic_is_computed_within_each_market(self):
        factors = pd.DataFrame(
            {
                "date": [pd.Timestamp("2024-01-01").date()] * 4,
                "asset_id": ["US_A", "US_B", "CN_A", "CN_B"],
                "market": ["US", "US", "CN", "CN"],
                "factor_name": ["momentum_2"] * 4,
                "factor_value": [1.0, 2.0, 1.0, 2.0],
                "lookback_window": [2] * 4,
            }
        )
        labels = pd.DataFrame(
            {
                "date": [pd.Timestamp("2024-01-01").date()] * 4,
                "asset_id": ["US_A", "US_B", "CN_A", "CN_B"],
                "market": ["US", "US", "CN", "CN"],
                "horizon": [1] * 4,
                "execution_lag": [1] * 4,
                "forward_return": [0.01, 0.02, 0.20, 0.10],
            }
        )

        result = compute_ic(factors, labels).sort_values("market").reset_index(drop=True)

        self.assertEqual(result["market"].tolist(), ["CN", "US"])
        self.assertAlmostEqual(result.loc[0, "ic"], -1.0)
        self.assertAlmostEqual(result.loc[1, "ic"], 1.0)

    def test_group_returns_are_computed_within_each_market(self):
        result = quantile_group_returns(self.factors, self.labels, quantiles=2)

        self.assertIn("market", result.columns)


if __name__ == "__main__":
    unittest.main()
