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
        )

        cases = build_experiment_cases(config)

        self.assertEqual(len(cases), 8)
        self.assertEqual(cases[0].case_id, "CN_momentum_2_top1_cost0")
        self.assertEqual(cases[-1].case_id, "US_reversal_2_top2_cost0")

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
                        "output_dir": str(Path(tmp) / "reports"),
                    }
                ),
                encoding="utf-8",
            )

            config = load_experiment_grid_config(config_path)

            self.assertEqual(config.markets, ("CN",))
            self.assertEqual(config.factor_names, ("momentum_2",))
            self.assertEqual(config.output_dir, Path(tmp) / "reports")


if __name__ == "__main__":
    unittest.main()
