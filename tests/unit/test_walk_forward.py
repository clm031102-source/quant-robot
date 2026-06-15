import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.experiments.runner import ExperimentGridConfig
from quant_robot.validation.walk_forward import (
    WalkForwardConfig,
    _with_multiple_testing_evidence,
    load_walk_forward_config,
    run_walk_forward_validation,
)


class WalkForwardTests(unittest.TestCase):
    def test_walk_forward_runs_train_and_test_splits_and_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = WalkForwardConfig(
                split_date="2024-01-08",
                experiment_grid=ExperimentGridConfig(
                    markets=("CN", "US"),
                    factor_names=("momentum_2", "reversal_2"),
                    factor_windows=(2,),
                    top_n_values=(1,),
                    cost_bps_values=(0.0,),
                ),
                output_dir=Path(tmp),
                min_test_sharpe=0.0,
            )

            result = run_walk_forward_validation(load_demo_market_bars(), config)

            leaderboard = result["leaderboard"]
            self.assertEqual(len(leaderboard), 4)
            self.assertEqual(result["summary"]["cases"], 4)
            self.assertEqual({row["data_mode"] for row in leaderboard}, {"fixture"})
            self.assertEqual({row["factor_source"] for row in leaderboard}, {"technical"})
            self.assertEqual({row["hypothesis_count"] for row in leaderboard}, {4})
            self.assertTrue(all("adjusted_ic_p_value" in row for row in leaderboard))
            self.assertTrue(all("passes_adjusted_ic_p_value" in row for row in leaderboard))
            self.assertTrue(all(row["train_trades"] > 0 for row in leaderboard))
            self.assertTrue(all(row["test_trades"] > 0 for row in leaderboard))
            self.assertEqual([row["rank"] for row in leaderboard], list(range(1, 5)))
            self.assertIn("stability_score", leaderboard[0])
            self.assertTrue((Path(tmp) / "walk_forward_leaderboard.csv").exists())
            self.assertTrue((Path(tmp) / "walk_forward_leaderboard.json").exists())
            self.assertTrue((Path(tmp) / "manifest.json").exists())
            saved = pd.read_csv(Path(tmp) / "walk_forward_leaderboard.csv")
            self.assertEqual(len(saved), 4)

    def test_walk_forward_flags_overfit_candidates_when_test_metric_is_below_threshold(self):
        config = WalkForwardConfig(
            split_date="2024-01-08",
            experiment_grid=ExperimentGridConfig(
                markets=("CN_ETF",),
                factor_names=("momentum_2",),
                factor_windows=(2,),
                top_n_values=(1,),
                cost_bps_values=(0.0,),
            ),
            min_test_sharpe=999.0,
        )

        result = run_walk_forward_validation(load_demo_market_bars(), config)

        self.assertEqual(result["leaderboard"][0]["validation_status"], "rejected")
        self.assertIn("oos_sharpe_below_threshold", result["leaderboard"][0]["rejection_reasons"])

    def test_multiple_testing_failure_rejects_previously_accepted_candidate(self):
        rows = [
            {
                "case_id": "weak_ic",
                "validation_status": "accepted",
                "rejection_reasons": [],
                "test_ic_p_value": 1.0,
            }
        ]
        config = WalkForwardConfig(split_date="2024-01-08", experiment_grid=ExperimentGridConfig())

        result = _with_multiple_testing_evidence(rows, config)

        self.assertFalse(result[0]["passes_adjusted_ic_p_value"])
        self.assertEqual(result[0]["validation_status"], "rejected")
        self.assertIn("adjusted_ic_significance_not_passed", result[0]["rejection_reasons"])

    def test_walk_forward_rejects_candidates_below_relative_return_threshold(self):
        config = WalkForwardConfig(
            split_date="2024-01-08",
            experiment_grid=ExperimentGridConfig(
                markets=("CN",),
                factor_names=("momentum_2",),
                factor_windows=(2,),
                top_n_values=(1,),
                cost_bps_values=(0.0,),
                benchmark_asset_id="CN_ETF_XSHG_510300",
            ),
            min_test_trades=1,
            min_test_relative_return=999.0,
        )

        result = run_walk_forward_validation(load_demo_market_bars(), config)
        row = result["leaderboard"][0]

        self.assertEqual(row["validation_status"], "rejected")
        self.assertIn("relative_return_below_threshold", row["rejection_reasons"])
        self.assertIn("test_relative_return", row)

    def test_walk_forward_rejects_candidates_above_drawdown_limit(self):
        config = WalkForwardConfig(
            split_date="2024-01-08",
            experiment_grid=ExperimentGridConfig(
                markets=("CN",),
                factor_names=("momentum_2",),
                factor_windows=(2,),
                top_n_values=(1,),
                cost_bps_values=(0.0,),
            ),
            min_test_trades=1,
            max_test_drawdown=0.0,
        )

        result = run_walk_forward_validation(load_demo_market_bars(), config)
        row = result["leaderboard"][0]

        self.assertEqual(row["validation_status"], "rejected")
        self.assertIn("drawdown_above_limit", row["rejection_reasons"])

    def test_walk_forward_test_split_uses_warmup_history_for_rolling_factors(self):
        bars = load_demo_market_bars()
        bars = bars[(bars["market"] == "CN") & (pd.to_datetime(bars["date"]).dt.date <= pd.Timestamp("2024-01-06").date())]
        config = WalkForwardConfig(
            split_date="2024-01-03",
            experiment_grid=ExperimentGridConfig(
                markets=("CN",),
                factor_names=("momentum_2",),
                factor_windows=(2,),
                top_n_values=(1,),
                cost_bps_values=(0.0,),
            ),
            min_test_trades=1,
        )

        result = run_walk_forward_validation(bars, config)

        self.assertEqual(result["leaderboard"][0]["test_status"], "completed")
        self.assertGreaterEqual(result["leaderboard"][0]["test_trades"], 1)

    def test_walk_forward_supports_rolling_multi_fold_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = WalkForwardConfig(
                split_date="2024-01-08",
                experiment_grid=ExperimentGridConfig(
                    markets=("CN_ETF",),
                    factor_names=("momentum_2",),
                    factor_windows=(2,),
                    top_n_values=(1,),
                    cost_bps_values=(0.0,),
                ),
                output_dir=Path(tmp),
                min_test_sharpe=-999.0,
                rolling_train_days=5,
                rolling_test_days=4,
                rolling_step_days=3,
                min_accepted_folds=2,
            )

            result = run_walk_forward_validation(load_demo_market_bars(), config)

            row = result["leaderboard"][0]
            self.assertGreaterEqual(result["summary"]["folds"], 2)
            self.assertGreaterEqual(row["folds"], 2)
            self.assertGreaterEqual(row["accepted_folds"], 2)
            self.assertIn("mean_test_sharpe", row)
            self.assertIn("worst_test_max_drawdown", row)
            self.assertIn("fold_rejection_reasons", row)
            self.assertEqual(row["test_trades"], row["total_test_trades"])
            self.assertTrue((Path(tmp) / "walk_forward_folds.csv").exists())

    def test_load_walk_forward_config_reads_nested_experiment_grid(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "walk_forward.json"
            config_path.write_text(
                json.dumps(
                    {
                        "split_date": "2024-01-08",
                        "output_dir": str(Path(tmp) / "wf"),
                        "min_test_sharpe": 0.5,
                        "experiment_grid": {
                            "markets": ["CN"],
                            "factor_source": "tushare_daily_basic",
                            "factor_names": ["momentum_2"],
                            "factor_windows": [2],
                            "top_n_values": [1],
                            "cost_bps_values": [5],
                            "rebalance_intervals": [5],
                            "benchmark_asset_id": "CN_ETF_XSHG_510300",
                        },
                        "min_test_relative_return": 0.02,
                        "max_test_drawdown": 0.20,
                        "rolling_train_days": 252,
                        "rolling_test_days": 63,
                        "rolling_step_days": 21,
                        "min_accepted_folds": 3,
                        "multiple_testing_alpha": 0.01,
                    }
                ),
                encoding="utf-8",
            )

            config = load_walk_forward_config(config_path)

            self.assertEqual(config.split_date, "2024-01-08")
            self.assertEqual(config.output_dir, Path(tmp) / "wf")
            self.assertEqual(config.min_test_sharpe, 0.5)
            self.assertAlmostEqual(config.min_test_relative_return, 0.02)
            self.assertAlmostEqual(config.max_test_drawdown, 0.20)
            self.assertEqual(config.experiment_grid.markets, ("CN",))
            self.assertEqual(config.experiment_grid.factor_source, "tushare_daily_basic")
            self.assertEqual(config.experiment_grid.cost_bps_values, (5.0,))
            self.assertEqual(config.experiment_grid.rebalance_intervals, (5,))
            self.assertEqual(config.experiment_grid.benchmark_asset_id, "CN_ETF_XSHG_510300")
            self.assertEqual(config.rolling_train_days, 252)
            self.assertEqual(config.rolling_test_days, 63)
            self.assertEqual(config.rolling_step_days, 21)
            self.assertEqual(config.min_accepted_folds, 3)
            self.assertAlmostEqual(config.multiple_testing_alpha, 0.01)


if __name__ == "__main__":
    unittest.main()
