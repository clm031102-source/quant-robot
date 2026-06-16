import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.factors.technical import compute_basic_factors
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

    def test_build_experiment_cases_expands_regime_lookback_values(self):
        config = ExperimentGridConfig(
            markets=("CN_ETF",),
            factor_names=("momentum_2",),
            factor_windows=(2,),
            top_n_values=(1,),
            cost_bps_values=(5.0,),
            rebalance_intervals=(1,),
            regime_filter=True,
            regime_lookback_values=(60, 120),
        )

        cases = build_experiment_cases(config)

        self.assertEqual([case.case_id for case in cases], [
            "CN_ETF_momentum_2_top1_cost5_reb1_regime60",
            "CN_ETF_momentum_2_top1_cost5_reb1_regime120",
        ])
        self.assertEqual([case.regime_lookback for case in cases], [60, 120])

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
            self.assertIn("ic_observations", leaderboard[0])
            self.assertIn("positive_ic_rate", leaderboard[0])
            self.assertIn("ic_t_stat", leaderboard[0])
            self.assertIn("ic_p_value", leaderboard[0])
            self.assertIn("significance_status", leaderboard[0])
            self.assertIn("tail_mean_ic", leaderboard[0])
            self.assertIn("tail_ic_p_value", leaderboard[0])
            self.assertIn("tail_ic_observations", leaderboard[0])
            self.assertIn("tail_significance_status", leaderboard[0])
            self.assertIn("long_short_mean_return", leaderboard[0])
            self.assertIn("long_short_positive_rate", leaderboard[0])
            self.assertIn("long_short_observations", leaderboard[0])
            self.assertIn("quantile_bottom_mean_return", leaderboard[0])
            self.assertIn("quantile_top_mean_return", leaderboard[0])
            self.assertIn("quantile_spread_mean_return", leaderboard[0])
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

    def test_experiment_grid_runs_tushare_daily_basic_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = load_demo_market_bars()
            _write_daily_basic_factor_inputs(root, bars)
            config = ExperimentGridConfig(
                markets=("CN",),
                factor_source="tushare_daily_basic",
                factor_input_root=root,
                factor_input_required=True,
                factor_names=("pb_inverse",),
                factor_windows=(1,),
                top_n_values=(1,),
                cost_bps_values=(5.0,),
            )

            result = run_experiment_grid(bars, config)

            row = result["leaderboard"][0]
            self.assertEqual(row["status"], "completed")
            self.assertEqual(row["factor_name"], "pb_inverse")
            self.assertEqual(result["config"]["factor_source"], "tushare_daily_basic")
            self.assertEqual(result["config"]["factor_input_root"], str(root))

    def test_experiment_grid_coerces_none_metrics_without_failing_case(self):
        config = ExperimentGridConfig(
            markets=("CN",),
            factor_names=("momentum_2",),
            factor_windows=(2,),
            top_n_values=(1,),
            cost_bps_values=(0.0,),
        )
        pipeline_result = {
            "data_mode": "research",
            "metrics": {
                "total_return": 0.01,
                "annualized_return": None,
                "annualized_volatility": None,
                "sharpe": None,
                "max_drawdown": None,
            },
            "benchmark_metrics": {"benchmark_total_return": None, "relative_return": None, "excess_over_cash": None},
            "decision": {"decision_status": "approved", "rejection_reasons": []},
            "factor_summary": {"mean_ic": None, "ic_p_value": None, "significance_status": "unknown"},
            "artifact_rows": {"trades": 1, "holdings": 1},
        }

        with patch("quant_robot.experiments.runner.run_research_pipeline", return_value=pipeline_result):
            result = run_experiment_grid(load_demo_market_bars(), config)

        row = result["leaderboard"][0]
        self.assertEqual(row["status"], "completed")
        self.assertEqual(row["annualized_return"], 0.0)
        self.assertEqual(row["sharpe"], 0.0)
        self.assertEqual(row["ic_p_value"], 1.0)

    def test_experiment_grid_passes_case_regime_lookback_to_pipeline(self):
        config = ExperimentGridConfig(
            markets=("CN_ETF",),
            factor_names=("momentum_2",),
            factor_windows=(2,),
            top_n_values=(1,),
            cost_bps_values=(0.0,),
            regime_filter=True,
            regime_lookback_values=(60, 120),
        )
        pipeline_result = {
            "data_mode": "research",
            "metrics": {
                "total_return": 0.01,
                "annualized_return": 0.01,
                "annualized_volatility": 0.05,
                "sharpe": 0.2,
                "max_drawdown": -0.01,
            },
            "benchmark_metrics": {"benchmark_total_return": 0.0, "relative_return": 0.01, "excess_over_cash": 0.01},
            "decision": {"decision_status": "approved", "rejection_reasons": []},
            "factor_summary": {"mean_ic": 0.01, "ic_p_value": 0.5, "significance_status": "unknown"},
            "artifact_rows": {"trades": 1, "holdings": 1},
        }

        with patch("quant_robot.experiments.runner.run_research_pipeline", return_value=pipeline_result) as pipeline:
            result = run_experiment_grid(load_demo_market_bars(), config)

        self.assertEqual([row["regime_lookback"] for row in result["leaderboard"]], [120, 60])
        passed_configs = [call.args[1] for call in pipeline.call_args_list]
        self.assertEqual([item.regime_lookback for item in passed_configs], [60, 120])

    def test_experiment_grid_can_precompute_factor_matrix_once_for_cases(self):
        bars = load_demo_market_bars()
        matrix = compute_basic_factors(bars, windows=(2,))
        config = ExperimentGridConfig(
            markets=("CN",),
            factor_names=("momentum_2",),
            factor_windows=(2,),
            top_n_values=(1, 2),
            cost_bps_values=(0.0, 5.0),
            precompute_factor_matrix=True,
        )
        pipeline_result = {
            "data_mode": "research",
            "metrics": {
                "total_return": 0.01,
                "annualized_return": 0.01,
                "annualized_volatility": 0.05,
                "sharpe": 0.2,
                "max_drawdown": -0.01,
            },
            "benchmark_metrics": {"benchmark_total_return": 0.0, "relative_return": 0.01, "excess_over_cash": 0.01},
            "decision": {"decision_status": "approved", "rejection_reasons": []},
            "factor_summary": {"mean_ic": 0.01, "ic_p_value": 0.5, "significance_status": "unknown"},
            "artifact_rows": {"trades": 1, "holdings": 1},
        }

        with (
            patch("quant_robot.experiments.runner.compute_basic_factors", return_value=matrix) as factor_builder,
            patch("quant_robot.experiments.runner.run_research_pipeline", return_value=pipeline_result) as pipeline,
        ):
            result = run_experiment_grid(bars, config)

        self.assertEqual(len(result["leaderboard"]), 4)
        factor_builder.assert_called_once()
        self.assertEqual(len(pipeline.call_args_list), 4)
        self.assertTrue(all(call.kwargs["precomputed_factors"] is matrix for call in pipeline.call_args_list))

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
                        "regime_lookback_values": [60, 120],
                        "precompute_factor_matrix": True,
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
            self.assertEqual(config.regime_lookback_values, (60, 120))
            self.assertTrue(config.precompute_factor_matrix)
            self.assertEqual(config.output_dir, Path(tmp) / "reports")

    def test_load_experiment_grid_config_accepts_utf8_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "grid.json"
            config_path.write_text(
                "\ufeff" + json.dumps({"markets": ["CN"], "factor_names": ["momentum_2"]}),
                encoding="utf-8",
            )

            config = load_experiment_grid_config(config_path)

            self.assertEqual(config.markets, ("CN",))
            self.assertEqual(config.factor_names, ("momentum_2",))

    def test_load_experiment_grid_config_reads_factor_input_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "grid.json"
            factor_input_root = root / "factor_inputs"
            config_path.write_text(
                json.dumps(
                    {
                        "markets": ["CN"],
                        "factor_source": "tushare_daily_basic",
                        "factor_input_root": str(factor_input_root),
                        "factor_input_required": True,
                        "factor_names": ["pb_inverse"],
                        "factor_windows": [1],
                    }
                ),
                encoding="utf-8",
            )

            config = load_experiment_grid_config(config_path)

            self.assertEqual(config.factor_source, "tushare_daily_basic")
            self.assertEqual(config.factor_input_root, factor_input_root)
            self.assertTrue(config.factor_input_required)


def _write_daily_basic_factor_inputs(root: Path, bars: pd.DataFrame) -> None:
    from quant_robot.storage.dataset_store import DatasetStore

    rows = []
    for index, row in bars[bars["market"] == "CN"].reset_index(drop=True).iterrows():
        rows.append(
            {
                "date": row["date"],
                "asset_id": row["asset_id"],
                "symbol": row["symbol"],
                "market": "CN",
                "source": "tushare",
                "turnover_rate": 1.0 + index * 0.01,
                "turnover_rate_f": 1.1 + index * 0.01,
                "volume_ratio": 0.9 + index * 0.01,
                "pe_ttm": 8.0 + index * 0.1,
                "pb": 1.5 + index * 0.1,
                "ps_ttm": 2.0 + index * 0.1,
                "dv_ttm": 3.0,
                "total_mv": 120000.0 + index * 100.0,
                "circ_mv": 90000.0 + index * 100.0,
            }
        )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/factor_inputs",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


if __name__ == "__main__":
    unittest.main()
