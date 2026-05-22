import unittest

import pandas as pd

from quant_robot.portfolio.rebalance import build_rebalance_plan


class RebalancePlanTests(unittest.TestCase):
    def test_rebalance_plan_is_research_only_and_includes_reduce_rows(self):
        targets = pd.DataFrame(
            {
                "asset_id": ["A", "B"],
                "market": ["US", "US"],
                "target_weight": [0.60, 0.20],
                "latest_price": [10.0, 20.0],
            }
        )
        current_positions = pd.DataFrame(
            {
                "asset_id": ["A", "C"],
                "quantity": [100.0, 50.0],
            }
        )
        latest_prices = pd.DataFrame(
            {
                "asset_id": ["A", "B", "C"],
                "latest_price": [10.0, 20.0, 5.0],
            }
        )

        plan = build_rebalance_plan(targets, current_positions, latest_prices, portfolio_value=2000.0)

        self.assertEqual(set(plan["asset_id"]), {"A", "B", "C"})
        self.assertTrue((plan["executable"] == False).all())  # noqa: E712
        self.assertEqual(set(plan["intent_type"]), {"research_rebalance_plan"})
        reduce_row = plan[plan["asset_id"] == "C"].iloc[0]
        self.assertEqual(reduce_row["action"], "decrease")
        self.assertEqual(reduce_row["target_weight"], 0.0)
        self.assertLess(reduce_row["delta_value"], 0.0)

    def test_rebalance_plan_rejects_real_account_like_columns(self):
        targets = pd.DataFrame({"asset_id": ["A"], "market": ["US"], "target_weight": [1.0], "latest_price": [10.0]})
        current_positions = pd.DataFrame({"asset_id": ["A"], "quantity": [1.0], "account_id": ["real-account"]})
        latest_prices = pd.DataFrame({"asset_id": ["A"], "latest_price": [10.0]})

        with self.assertRaisesRegex(ValueError, "real account or broker columns"):
            build_rebalance_plan(targets, current_positions, latest_prices, portfolio_value=1000.0)


if __name__ == "__main__":
    unittest.main()
