import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.experiments.runner import (
    ExperimentGridConfig,
    build_experiment_cases,
    load_experiment_grid_config,
    run_experiment_grid,
)


class ExperimentRunnerTests(unittest.TestCase):
    def test_build_experiment_cases_creates_stable_cross_product(self):
        config = ExperimentGridConfig(
            markets=("CN", "US"),
            factor_names=("momentum_2", "reversal_2"),
            factor_windows=(2,),
            top_n_values=(1, 2),
            cost_bps_values=(0.0,),
            rebalance_intervals=(1, 5),
        )

        cases = build_experiment_cases(config)

        self.assertEqual(len(cases), 16)
        self.assertEqual(cases[0].case_id, "CN_momentum_2_top1_cost0_reb1")
        self.assertEqual(cases[-1].case_id, "US_reversal_2_top2_cost0_reb5")

    def test_experiment_grid_runs_sweep_and_writes_leaderboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = ExperimentGridConfig(
                markets=("CN", "US"),
                factor_names=("momentum_2", "reversal_2"),
                factor_windows=(2,),
                top_n_values=(1,),
                cost_bps_values=(0.0, 5.0),
                output_dir=Path(tmp),
                rank_by="sharpe",
            )

            result = run_experiment_grid(load_demo_market_bars(), config)

            leaderboard = result["leaderboard"]
            self.assertEqual(len(leaderboard), 8)
            self.assertEqual({row["status"] for row in leaderboard}, {"completed"})
            self.assertEqual({row["data_mode"] for row in leaderboard}, {"fixture"})
            self.assertEqual([row["rank"] for row in leaderboard], list(range(1, 9)))
            self.assertGreaterEqual(leaderboard[0]["sharpe"], leaderboard[-1]["sharpe"])
            self.assertTrue((Path(tmp) / "leaderboard.csv").exists())
            self.assertTrue((Path(tmp) / "leaderboard.json").exists())
            self.assertTrue((Path(tmp) / "manifest.json").exists())
            self.assertTrue((Path(tmp) / leaderboard[0]["case_id"] / "metrics.json").exists())
            saved = pd.read_csv(Path(tmp) / "leaderboard.csv")
            self.assertEqual(len(saved), 8)

    def test_experiment_grid_surfaces_decision_metrics(self):
        config = ExperimentGridConfig(
            markets=("CN_ETF",),
            factor_names=("momentum_2",),
            factor_windows=(2,),
            top_n_values=(1,),
            cost_bps_values=(0.0,),
            benchmark_asset_id="CN_ETF_XSHG_510300",
            min_relative_return=-1.0,
            rank_by="relative_return",
        )

        result = run_experiment_grid(load_demo_market_bars(), config)
        row = result["leaderboard"][0]

        self.assertEqual(row["status"], "completed")
        self.assertIn("benchmark_total_return", row)
        self.assertIn("relative_return", row)
        self.assertIn("excess_over_cash", row)
        self.assertEqual(row["decision_status"], "approved")

    def test_experiment_grid_marks_no_trade_cases_without_crashing(self):
        config = ExperimentGridConfig(
            markets=("CN",),
            factor_names=("missing_factor_2",),
            factor_windows=(2,),
            top_n_values=(1,),
            cost_bps_values=(0.0,),
        )

        result = run_experiment_grid(load_demo_market_bars(), config)

        self.assertEqual(result["leaderboard"][0]["status"], "no_trades")
        self.assertEqual(result["leaderboard"][0]["trades"], 0)

    def test_experiment_grid_rejects_factor_window_mismatch(self):
        config = ExperimentGridConfig(
            markets=("CN",),
            factor_names=("momentum_5",),
            factor_windows=(2,),
            top_n_values=(1,),
            cost_bps_values=(0.0,),
        )

        with self.assertRaisesRegex(ValueError, "factor_names reference windows"):
            run_experiment_grid(load_demo_market_bars(), config)

    def test_experiment_grid_rejects_risk_adjusted_momentum_window_mismatch(self):
        config = ExperimentGridConfig(
            markets=("CN",),
            factor_names=("risk_adjusted_momentum_5",),
            factor_windows=(2,),
            top_n_values=(1,),
            cost_bps_values=(0.0,),
        )

        with self.assertRaisesRegex(ValueError, "risk_adjusted_momentum_5"):
            run_experiment_grid(load_demo_market_bars(), config)

    def test_load_experiment_grid_config_reads_json_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "grid.json"
            config_path.write_text(
                json.dumps(
                    {
                        "markets": ["CN"],
                        "factor_names": ["momentum_2"],
                        "factor_windows": [2],
                        "top_n_values": [1],
                        "cost_bps_values": [5],
                        "rebalance_intervals": [5],
                        "benchmark_asset_id": "CN_ETF_XSHG_510300",
                        "min_relative_return": 0.01,
                        "target_gross_exposure": 0.9,
                        "output_dir": str(Path(tmp) / "reports"),
                    }
                ),
                encoding="utf-8",
            )

            config = load_experiment_grid_config(config_path)

            self.assertEqual(config.markets, ("CN",))
            self.assertEqual(config.factor_names, ("momentum_2",))
            self.assertEqual(config.rebalance_intervals, (5,))
            self.assertEqual(config.benchmark_asset_id, "CN_ETF_XSHG_510300")
            self.assertAlmostEqual(config.min_relative_return, 0.01)
            self.assertAlmostEqual(config.target_gross_exposure, 0.9)
            self.assertEqual(config.output_dir, Path(tmp) / "reports")


if __name__ == "__main__":
    unittest.main()
