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
    _resume_fingerprint,
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
            forward_horizon=2,
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
        self.assertIn("overlap_autocorr_adjusted_sharpe", row)
        self.assertIn("overlap_effective_sample_size", row)
        self.assertIn("overlap_risk_flag", row)
        self.assertEqual(row["decision_status"], "approved")

    def test_experiment_grid_can_skip_per_case_artifacts_while_writing_leaderboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = ExperimentGridConfig(
                markets=("CN",),
                factor_names=("momentum_2",),
                factor_windows=(2,),
                top_n_values=(1,),
                cost_bps_values=(0.0,),
                output_dir=Path(tmp),
                write_case_artifacts=False,
            )
            pipeline_result = {
                "data_mode": "research",
                "metrics": {"total_return": 0.01, "annualized_return": 0.01, "annualized_volatility": 0.05, "sharpe": 0.2, "max_drawdown": -0.01},
                "benchmark_metrics": {"benchmark_total_return": 0.0, "relative_return": 0.01, "excess_over_cash": 0.01},
                "decision": {"decision_status": "approved", "rejection_reasons": []},
                "factor_summary": {"mean_ic": 0.01, "ic_p_value": 0.5, "significance_status": "unknown"},
                "artifact_rows": {"trades": 1, "holdings": 1},
            }

            with patch("quant_robot.experiments.runner.run_research_pipeline", return_value=pipeline_result) as pipeline:
                run_experiment_grid(load_demo_market_bars(), config)

            passed_config = pipeline.call_args.args[1]
            self.assertIsNone(passed_config.output_dir)
            self.assertTrue((Path(tmp) / "leaderboard.csv").exists())
            self.assertFalse((Path(tmp) / "CN_momentum_2_top1_cost0_reb1").exists())

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
        self.assertEqual(factor_builder.call_args.kwargs["factor_names"], ("momentum_2",))
        self.assertEqual(len(pipeline.call_args_list), 4)
        self.assertTrue(all(call.kwargs["precomputed_factors"] is matrix for call in pipeline.call_args_list))

    def test_experiment_grid_reports_precompute_and_case_progress(self):
        bars = load_demo_market_bars()
        matrix = compute_basic_factors(bars, windows=(2,))
        events = []
        config = ExperimentGridConfig(
            markets=("CN",),
            factor_names=("momentum_2",),
            factor_windows=(2,),
            top_n_values=(1, 2),
            cost_bps_values=(0.0,),
            precompute_factor_matrix=True,
        )
        pipeline_result = {
            "data_mode": "research",
            "metrics": {"total_return": 0.01, "annualized_return": 0.01, "annualized_volatility": 0.05, "sharpe": 0.2, "max_drawdown": -0.01},
            "benchmark_metrics": {"benchmark_total_return": 0.0, "relative_return": 0.01, "excess_over_cash": 0.01},
            "decision": {"decision_status": "approved", "rejection_reasons": []},
            "factor_summary": {"mean_ic": 0.01, "ic_p_value": 0.5, "significance_status": "unknown"},
            "artifact_rows": {"trades": 1, "holdings": 1},
        }

        with (
            patch("quant_robot.experiments.runner.compute_basic_factors", return_value=matrix),
            patch("quant_robot.experiments.runner.run_research_pipeline", return_value=pipeline_result),
        ):
            result = run_experiment_grid(bars, config, progress=events.append)

        self.assertEqual(result["summary"]["completed"], 2)
        self.assertEqual([event["event"] for event in events], [
            "precompute_start",
            "precompute_done",
            "case_start",
            "case_done",
            "case_start",
            "case_done",
            "grid_done",
        ])
        self.assertEqual(events[0]["factor_source"], "technical")
        self.assertEqual(events[0]["factor_count"], 1)
        self.assertEqual(events[2]["case_id"], "CN_momentum_2_top1_cost0_reb1")
        self.assertEqual(events[3]["status"], "completed")
        self.assertEqual(events[-1]["completed"], 2)
        self.assertEqual(events[-1]["cases"], 2)

    def test_experiment_grid_checkpoints_each_completed_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = ExperimentGridConfig(
                markets=("CN",),
                factor_names=("momentum_2",),
                factor_windows=(2,),
                top_n_values=(1, 2),
                cost_bps_values=(0.0,),
                output_dir=Path(tmp),
                write_case_artifacts=False,
            )
            pipeline_result = {
                "data_mode": "research",
                "metrics": {"total_return": 0.01, "annualized_return": 0.01, "annualized_volatility": 0.05, "sharpe": 0.2, "max_drawdown": -0.01},
                "benchmark_metrics": {"benchmark_total_return": 0.0, "relative_return": 0.01, "excess_over_cash": 0.01},
                "decision": {"decision_status": "approved", "rejection_reasons": []},
                "factor_summary": {"mean_ic": 0.01, "ic_p_value": 0.5, "significance_status": "unknown"},
                "artifact_rows": {"trades": 1, "holdings": 1},
            }

            with patch("quant_robot.experiments.runner.run_research_pipeline", return_value=pipeline_result):
                result = run_experiment_grid(load_demo_market_bars(), config)

            checkpoint_path = Path(tmp) / "partial_leaderboard.jsonl"
            self.assertTrue(checkpoint_path.exists())
            rows = [json.loads(line) for line in checkpoint_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["case_id"] for row in rows], [
                "CN_momentum_2_top1_cost0_reb1",
                "CN_momentum_2_top2_cost0_reb1",
            ])
            self.assertEqual([row["status"] for row in rows], ["completed", "completed"])
            self.assertEqual([row["trades"] for row in rows], [1, 1])
            self.assertEqual(len(result["leaderboard"]), 2)

    def test_experiment_grid_resume_skips_completed_partial_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            config = ExperimentGridConfig(
                markets=("CN",),
                factor_names=("momentum_2",),
                factor_windows=(2,),
                top_n_values=(1, 2),
                cost_bps_values=(0.0,),
                output_dir=output_dir,
                write_case_artifacts=False,
                resume_completed_cases=True,
            )
            completed_row = {
                "case_id": "CN_momentum_2_top1_cost0_reb1",
                "_grid_fingerprint": _resume_fingerprint(config),
                "market": "CN",
                "factor_source": "technical",
                "factor_name": "momentum_2",
                "factor_windows": [2],
                "top_n": 1,
                "cost_bps": 0.0,
                "rebalance_interval": 1,
                "regime_lookback": 20,
                "status": "completed",
                "error": None,
                "data_mode": "research",
                "trades": 1,
                "sharpe": 0.9,
            }
            (output_dir / "partial_leaderboard.jsonl").write_text(json.dumps(completed_row) + "\n", encoding="utf-8")

            pipeline_result = {
                "data_mode": "research",
                "metrics": {"total_return": 0.01, "annualized_return": 0.01, "annualized_volatility": 0.05, "sharpe": 0.2, "max_drawdown": -0.01},
                "benchmark_metrics": {"benchmark_total_return": 0.0, "relative_return": 0.01, "excess_over_cash": 0.01},
                "decision": {"decision_status": "approved", "rejection_reasons": []},
                "factor_summary": {"mean_ic": 0.01, "ic_p_value": 0.5, "significance_status": "unknown"},
                "artifact_rows": {"trades": 1, "holdings": 1},
            }
            events = []

            with patch("quant_robot.experiments.runner.run_research_pipeline", return_value=pipeline_result) as pipeline:
                result = run_experiment_grid(load_demo_market_bars(), config, progress=events.append)

            pipeline.assert_called_once()
            self.assertEqual(pipeline.call_args.args[1].top_n, 2)
            self.assertEqual(result["summary"]["completed"], 2)
            self.assertEqual({row["case_id"] for row in result["leaderboard"]}, {
                "CN_momentum_2_top1_cost0_reb1",
                "CN_momentum_2_top2_cost0_reb1",
            })
            self.assertIn("case_skipped", [event["event"] for event in events])
            rows = [json.loads(line) for line in (output_dir / "partial_leaderboard.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["case_id"] for row in rows], [
                "CN_momentum_2_top1_cost0_reb1",
                "CN_momentum_2_top2_cost0_reb1",
            ])

    def test_experiment_grid_resume_ignores_partial_rows_from_different_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            completed_row = {
                "case_id": "CN_momentum_2_top1_cost0_reb1",
                "_grid_fingerprint": "stale-config",
                "status": "completed",
                "trades": 1,
                "sharpe": 0.9,
            }
            (output_dir / "partial_leaderboard.jsonl").write_text(json.dumps(completed_row) + "\n", encoding="utf-8")
            config = ExperimentGridConfig(
                markets=("CN",),
                factor_names=("momentum_2",),
                factor_windows=(2,),
                top_n_values=(1, 2),
                cost_bps_values=(0.0,),
                output_dir=output_dir,
                write_case_artifacts=False,
                resume_completed_cases=True,
            )
            pipeline_result = {
                "data_mode": "research",
                "metrics": {"total_return": 0.01, "annualized_return": 0.01, "annualized_volatility": 0.05, "sharpe": 0.2, "max_drawdown": -0.01},
                "benchmark_metrics": {"benchmark_total_return": 0.0, "relative_return": 0.01, "excess_over_cash": 0.01},
                "decision": {"decision_status": "approved", "rejection_reasons": []},
                "factor_summary": {"mean_ic": 0.01, "ic_p_value": 0.5, "significance_status": "unknown"},
                "artifact_rows": {"trades": 1, "holdings": 1},
            }
            events = []

            with patch("quant_robot.experiments.runner.run_research_pipeline", return_value=pipeline_result) as pipeline:
                result = run_experiment_grid(load_demo_market_bars(), config, progress=events.append)

            self.assertEqual(pipeline.call_count, 2)
            self.assertEqual(result["summary"]["completed"], 2)
            self.assertNotIn("case_skipped", [event["event"] for event in events])
            rows = [json.loads(line) for line in (output_dir / "partial_leaderboard.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["case_id"] for row in rows], [
                "CN_momentum_2_top1_cost0_reb1",
                "CN_momentum_2_top2_cost0_reb1",
            ])

    def test_experiment_grid_can_precompute_tushare_daily_basic_factor_matrix_once(self):
        bars = load_demo_market_bars()
        matrix = pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value", "lookback_window"])
        config = ExperimentGridConfig(
            markets=("CN",),
            factor_source="tushare_daily_basic",
            factor_input_root=Path("authority_daily_basic.json"),
            factor_names=("pb_inverse", "dv_ttm"),
            factor_windows=(1,),
            top_n_values=(1, 2),
            cost_bps_values=(5.0,),
            precompute_factor_matrix=True,
        )
        pipeline_result = {
            "data_mode": "research",
            "metrics": {"total_return": 0.01, "annualized_return": 0.01, "annualized_volatility": 0.05, "sharpe": 0.2, "max_drawdown": -0.01},
            "benchmark_metrics": {"benchmark_total_return": 0.0, "relative_return": 0.01, "excess_over_cash": 0.01},
            "decision": {"decision_status": "approved", "rejection_reasons": []},
            "factor_summary": {"mean_ic": 0.01, "ic_p_value": 0.5, "significance_status": "unknown"},
            "artifact_rows": {"trades": 1, "holdings": 1},
        }

        with (
            patch("quant_robot.experiments.runner.load_factor_inputs", return_value=pd.DataFrame({"date": [], "asset_id": []})) as loader,
            patch("quant_robot.experiments.runner.compute_daily_basic_factors", return_value=matrix) as factor_builder,
            patch("quant_robot.experiments.runner.run_research_pipeline", return_value=pipeline_result) as pipeline,
        ):
            result = run_experiment_grid(bars, config)

        self.assertEqual(len(result["leaderboard"]), 4)
        loader.assert_called_once_with(Path("authority_daily_basic.json"), "CN")
        factor_builder.assert_called_once()
        self.assertEqual(factor_builder.call_args.kwargs["factor_names"], ("pb_inverse", "dv_ttm"))
        self.assertTrue(all(call.kwargs["precomputed_factors"] is matrix for call in pipeline.call_args_list))

    def test_experiment_grid_can_precompute_tushare_moneyflow_factor_matrix_once(self):
        bars = load_demo_market_bars()
        matrix = pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value", "lookback_window"])
        config = ExperimentGridConfig(
            markets=("CN",),
            factor_source="tushare_moneyflow",
            moneyflow_input_root=Path("authority_moneyflow.json"),
            factor_names=("net_mf_amount_ratio", "small_order_sell_pressure"),
            factor_windows=(1,),
            top_n_values=(1, 2),
            cost_bps_values=(5.0,),
            precompute_factor_matrix=True,
        )
        pipeline_result = {
            "data_mode": "research",
            "metrics": {"total_return": 0.01, "annualized_return": 0.01, "annualized_volatility": 0.05, "sharpe": 0.2, "max_drawdown": -0.01},
            "benchmark_metrics": {"benchmark_total_return": 0.0, "relative_return": 0.01, "excess_over_cash": 0.01},
            "decision": {"decision_status": "approved", "rejection_reasons": []},
            "factor_summary": {"mean_ic": 0.01, "ic_p_value": 0.5, "significance_status": "unknown"},
            "artifact_rows": {"trades": 1, "holdings": 1},
        }

        with (
            patch("quant_robot.experiments.runner.load_moneyflow_inputs", return_value=pd.DataFrame({"date": [], "asset_id": []})) as loader,
            patch("quant_robot.experiments.runner.compute_moneyflow_factors", return_value=matrix) as factor_builder,
            patch("quant_robot.experiments.runner.run_research_pipeline", return_value=pipeline_result) as pipeline,
        ):
            result = run_experiment_grid(bars, config)

        self.assertEqual(len(result["leaderboard"]), 4)
        loader.assert_called_once_with(Path("authority_moneyflow.json"), "CN")
        factor_builder.assert_called_once()
        self.assertEqual(factor_builder.call_args.kwargs["factor_names"], ("net_mf_amount_ratio", "small_order_sell_pressure"))
        self.assertTrue(all(call.kwargs["precomputed_factors"] is matrix for call in pipeline.call_args_list))

    def test_experiment_grid_filters_bars_before_precomputing_factor_matrix(self):
        bars = pd.DataFrame(
            {
                "date": ["2023-12-29", "2024-01-02", "2025-01-02"],
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000001", "CN_XSHE_000001"],
                "symbol": ["000001.SZ", "000001.SZ", "000001.SZ"],
                "market": ["CN", "CN", "CN"],
                "source": ["fixture", "fixture", "fixture"],
                "adj_close": [10.0, 10.1, 10.2],
                "volume": [1000, 1000, 1000],
                "amount": [10000.0, 10100.0, 10200.0],
            }
        )
        matrix = pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value", "lookback_window"])
        config = ExperimentGridConfig(
            markets=("CN",),
            factor_names=("momentum_2",),
            factor_windows=(2,),
            top_n_values=(1,),
            cost_bps_values=(0.0,),
            start_date="2024-01-01",
            end_date="2024-12-31",
            precompute_factor_matrix=True,
        )
        pipeline_result = {
            "data_mode": "research",
            "metrics": {"total_return": 0.0, "annualized_return": 0.0, "annualized_volatility": 0.0, "sharpe": 0.0, "max_drawdown": 0.0},
            "benchmark_metrics": {"benchmark_total_return": 0.0, "relative_return": 0.0, "excess_over_cash": 0.0},
            "decision": {"decision_status": "approved", "rejection_reasons": []},
            "factor_summary": {"mean_ic": 0.0, "ic_p_value": 1.0, "significance_status": "unknown"},
            "artifact_rows": {"trades": 1, "holdings": 1},
        }

        with (
            patch("quant_robot.experiments.runner.compute_basic_factors", return_value=matrix) as factor_builder,
            patch("quant_robot.experiments.runner.run_research_pipeline", return_value=pipeline_result),
        ):
            run_experiment_grid(bars, config)

        precompute_bars = factor_builder.call_args.args[0]
        self.assertEqual(precompute_bars["date"].astype(str).tolist(), ["2024-01-02"])

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
                        "write_case_artifacts": False,
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
            self.assertFalse(config.write_case_artifacts)
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
