import unittest
import tempfile
from pathlib import Path

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.experiments.runner import ExperimentGridConfig
from quant_robot.ops.same_parameter_replay import (
    build_same_parameter_replay_config,
    replay_leaderboard_row,
    run_same_parameter_full_sample_replay,
)


class SameParameterReplayTests(unittest.TestCase):
    def test_build_replay_config_freezes_candidate_parameters_for_full_sample(self):
        base = ExperimentGridConfig(
            markets=("CN",),
            factor_source="technical",
            factor_names=("baseline",),
            factor_windows=(20, 60),
            top_n_values=(10,),
            cost_bps_values=(5.0,),
            start_date="2023-01-01",
            end_date="2024-12-31",
            forward_horizon=5,
            execution_lag=1,
            rebalance_intervals=(1,),
            regime_filter=True,
            regime_lookback_values=(120, 180),
            output_dir=Path("old-output"),
            write_case_artifacts=True,
            precompute_factor_matrix=True,
            resume_completed_cases=True,
            reuse_research_inputs=True,
        )
        candidate = {
            "case_id": "CN_factor_x_top50_cost10_reb5_regime180",
            "market": "CN",
            "factor_source": "daily_basic_technical_combo",
            "factor_name": "factor_x",
            "top_n": 50,
            "cost_bps": 10,
            "forward_horizon": 20,
            "execution_lag": 1,
            "rebalance_interval": 5,
            "regime_lookback": 180,
        }

        config = build_same_parameter_replay_config(
            candidate,
            base,
            output_root=Path("data/reports/replay"),
            start_date="2015-01-01",
            end_date="2025-12-31",
        )

        self.assertEqual(config.markets, ("CN",))
        self.assertEqual(config.factor_source, "daily_basic_technical_combo")
        self.assertEqual(config.factor_names, ("factor_x",))
        self.assertEqual(config.factor_windows, (20, 60))
        self.assertEqual(config.top_n_values, (50,))
        self.assertEqual(config.cost_bps_values, (10.0,))
        self.assertEqual(config.start_date, "2015-01-01")
        self.assertEqual(config.end_date, "2025-12-31")
        self.assertEqual(config.signal_start_date, "2015-01-01")
        self.assertEqual(config.signal_end_date, "2025-12-31")
        self.assertEqual(config.forward_horizon, 20)
        self.assertEqual(config.execution_lag, 1)
        self.assertEqual(config.rebalance_intervals, (5,))
        self.assertEqual(config.regime_lookback_values, (180,))
        self.assertEqual(config.output_dir, Path("data/reports/replay/CN_factor_x_top50_cost10_reb5_regime180"))
        self.assertFalse(config.write_case_artifacts)
        self.assertTrue(config.precompute_factor_matrix)
        self.assertTrue(config.resume_completed_cases)
        self.assertTrue(config.reuse_research_inputs)

    def test_replay_leaderboard_row_marks_actual_full_sample_status(self):
        candidate = {
            "case_id": "original_case",
            "factor_name": "factor_x",
            "strict_split_status": "pass",
            "strict_split_violations": 0,
            "strict_split_folds": 38,
        }
        grid_row = {
            "case_id": "CN_factor_x_top50_cost10_reb5",
            "status": "completed",
            "mean_rank_ic": 0.031,
            "long_short_mean_return": 0.007,
            "long_short_positive_rate": 0.63,
            "total_return": 0.31,
            "relative_return": 0.08,
            "sharpe": 1.55,
            "max_drawdown": -0.10,
            "turnover": 1.4,
            "trades": 80,
            "cost_bps": 10.0,
            "execution_lag": 1,
            "max_participation_rate": 0.006,
            "overlap_autocorr_adjusted_sharpe": 0.92,
        }

        row = replay_leaderboard_row(candidate, grid_row, source_report="replay/leaderboard.csv")

        self.assertEqual(row["case_id"], "original_case")
        self.assertEqual(row["replay_case_id"], "CN_factor_x_top50_cost10_reb5")
        self.assertEqual(row["source_kind"], "same_parameter_full_sample_replay")
        self.assertEqual(row["source_report"], "replay/leaderboard.csv")
        self.assertEqual(row["same_parameter_full_sample_status"], "pass")
        self.assertEqual(row["replay_status"], "pass")
        self.assertEqual(row["strict_split_status"], "pass")
        self.assertAlmostEqual(row["sharpe"], 1.55)
        self.assertAlmostEqual(row["long_short_positive_rate"], 0.63)

    def test_replay_leaderboard_row_blocks_incomplete_grid_case(self):
        row = replay_leaderboard_row(
            {"case_id": "original_case"},
            {"case_id": "grid_case", "status": "no_trades", "trades": 0},
            source_report="replay/leaderboard.csv",
        )

        self.assertEqual(row["same_parameter_full_sample_status"], "block")
        self.assertEqual(row["replay_status"], "block")

    def test_run_same_parameter_full_sample_replay_writes_consolidated_outputs(self):
        base = ExperimentGridConfig(
            markets=("CN",),
            factor_source="technical",
            factor_names=("momentum_2",),
            factor_windows=(2,),
            top_n_values=(1,),
            cost_bps_values=(0.0,),
            forward_horizon=1,
            execution_lag=1,
            rebalance_intervals=(1,),
            min_trades=1,
            write_case_artifacts=False,
        )
        candidates = [
            {
                "case_id": "CN_momentum_2_top1_cost0_reb1",
                "market": "CN",
                "factor_source": "technical",
                "factor_name": "momentum_2",
                "top_n": 1,
                "cost_bps": 0.0,
                "forward_horizon": 1,
                "execution_lag": 1,
                "rebalance_interval": 1,
                "strict_split_status": "pass",
                "strict_split_violations": 0,
                "strict_split_folds": 1,
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            pack = run_same_parameter_full_sample_replay(
                candidates,
                load_demo_market_bars(),
                base,
                output_dir=Path(tmp),
                start_date="2024-01-02",
                end_date="2024-01-14",
            )

            self.assertEqual(pack["summary"]["candidates"], 1)
            self.assertEqual(len(pack["replay_rows"]), 1)
            self.assertIn(pack["replay_rows"][0]["same_parameter_full_sample_status"], {"pass", "block"})
            self.assertTrue((Path(tmp) / "same_parameter_full_sample_replay.csv").exists())
            self.assertTrue((Path(tmp) / "same_parameter_full_sample_replay.json").exists())


if __name__ == "__main__":
    unittest.main()
