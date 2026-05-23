import unittest

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.paper.simulator import PaperSimulationConfig, run_paper_simulation


class PaperSimulationTests(unittest.TestCase):
    def test_paper_simulation_creates_research_only_intents_and_next_bar_fills(self):
        config = PaperSimulationConfig(
            market="CN",
            factor_name="momentum_2",
            factor_windows=(2,),
            top_n=1,
            start_date="2024-01-04",
            end_date="2024-01-10",
            initial_cash=100000.0,
            commission_bps=5.0,
            slippage_bps=10.0,
        )

        result = run_paper_simulation(load_demo_market_bars(), config)

        self.assertGreater(len(result["intents"]), 0)
        self.assertGreater(len(result["fills"]), 0)
        self.assertTrue(all(row["executable"] is False for row in result["intents"]))
        self.assertTrue(all(row["fill_type"] == "simulated" for row in result["fills"]))
        first_intent = result["intents"][0]
        first_fill = result["fills"][0]
        self.assertGreater(pd.to_datetime(first_fill["execution_date"]), pd.to_datetime(first_intent["signal_date"]))
        self.assertIsNone(first_intent["broker_order_id"])

    def test_paper_simulation_tracks_cash_positions_and_equity(self):
        config = PaperSimulationConfig(
            market="ALL",
            factor_name="momentum_2",
            factor_windows=(2,),
            top_n=2,
            start_date="2024-01-04",
            end_date="2024-01-12",
            initial_cash=50000.0,
            max_asset_weight=0.35,
            min_cash_weight=0.10,
        )

        result = run_paper_simulation(load_demo_market_bars(), config)

        self.assertEqual(result["data_mode"], "fixture")
        self.assertGreater(len(result["equity_curve"]), 0)
        self.assertGreater(len(result["positions"]), 0)
        self.assertGreater(result["metrics"]["ending_equity"], 0.0)
        self.assertGreaterEqual(result["metrics"]["ending_cash"], 0.0)
        self.assertLessEqual(max(row["target_weight"] for row in result["snapshots"]), 0.70)

    def test_paper_simulation_rejects_real_account_like_position_columns(self):
        config = PaperSimulationConfig(market="CN", factor_name="momentum_2", factor_windows=(2,), top_n=1)
        positions = pd.DataFrame({"asset_id": ["CN_XSHG_600519"], "quantity": [1.0], "account_id": ["real"]})

        with self.assertRaisesRegex(ValueError, "real account or broker columns"):
            run_paper_simulation(load_demo_market_bars(), config, initial_positions=positions)


if __name__ == "__main__":
    unittest.main()
