import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.factors.public_technical_tail_guard import compute_public_technical_tail_guard_factors
from quant_robot.factors.public_trend_volume import compute_public_trend_volume_factors
from quant_robot.factors.public_formula_price_volume import compute_public_formula_price_volume_factors
from quant_robot.factors.public_technical_liquidity import compute_public_technical_liquidity_factors
from quant_robot.factors.public_technical import compute_public_technical_factors
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
                min_total_return=0.02,
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
            self.assertAlmostEqual(passed_config.min_total_return, 0.02)
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
        self.assertEqual(result["leaderboard"][0]["decision_status"], "rejected")
        self.assertIn("insufficient_oos_trades", result["leaderboard"][0]["decision_reasons"])

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

    def test_experiment_grid_precomputes_public_technical_factor_matrix(self):
        bars = _synthetic_public_technical_bars(asset_count=3, day_count=45)
        config = ExperimentGridConfig(
            markets=("CN",),
            factor_source="public_technical",
            factor_names=("donchian_position_20",),
            top_n_values=(1,),
            cost_bps_values=(0.0,),
            precompute_factor_matrix=True,
        )
        factors = compute_public_technical_factors(bars, factor_names=("donchian_position_20",))

        with patch("quant_robot.experiments.runner.compute_public_technical_factors", return_value=factors) as factor_builder:
            run_experiment_grid(bars, config)

        self.assertEqual(factor_builder.call_args.kwargs["factor_names"], ("donchian_position_20",))

    def test_experiment_grid_precomputes_public_technical_liquidity_factor_matrix(self):
        bars = _synthetic_public_technical_bars(asset_count=3, day_count=45)
        config = ExperimentGridConfig(
            markets=("CN",),
            factor_source="public_technical_liquidity",
            factor_names=("rsi_reversal_liquid_14_20",),
            top_n_values=(1,),
            cost_bps_values=(0.0,),
            precompute_factor_matrix=True,
        )
        factors = compute_public_technical_liquidity_factors(bars, factor_names=("rsi_reversal_liquid_14_20",))

        with patch(
            "quant_robot.experiments.runner.compute_public_technical_liquidity_factors",
            return_value=factors,
        ) as factor_builder:
            run_experiment_grid(bars, config)

        self.assertEqual(factor_builder.call_args.kwargs["factor_names"], ("rsi_reversal_liquid_14_20",))

    def test_experiment_grid_precomputes_public_technical_tail_guard_factor_matrix(self):
        bars = _synthetic_public_technical_bars(asset_count=3, day_count=45)
        config = ExperimentGridConfig(
            markets=("CN",),
            factor_source="public_technical_tail_guard",
            factor_names=("bollinger_reversal_liquid_low_tail_20",),
            top_n_values=(1,),
            cost_bps_values=(0.0,),
            precompute_factor_matrix=True,
        )
        factors = compute_public_technical_tail_guard_factors(
            bars,
            factor_names=("bollinger_reversal_liquid_low_tail_20",),
        )

        with patch(
            "quant_robot.experiments.runner.compute_public_technical_tail_guard_factors",
            return_value=factors,
        ) as factor_builder:
            run_experiment_grid(bars, config)

        self.assertEqual(factor_builder.call_args.kwargs["factor_names"], ("bollinger_reversal_liquid_low_tail_20",))

    def test_experiment_grid_precomputes_public_trend_volume_factor_matrix(self):
        bars = _synthetic_public_technical_bars(asset_count=3, day_count=70)
        config = ExperimentGridConfig(
            markets=("CN",),
            factor_source="public_trend_volume",
            factor_names=("supertrend_volume_confirmed_10_3_20",),
            top_n_values=(1,),
            cost_bps_values=(0.0,),
            precompute_factor_matrix=True,
        )
        factors = compute_public_trend_volume_factors(
            bars,
            factor_names=("supertrend_volume_confirmed_10_3_20",),
        )

        with patch(
            "quant_robot.experiments.runner.compute_public_trend_volume_factors",
            return_value=factors,
        ) as factor_builder:
            run_experiment_grid(bars, config)

        self.assertEqual(factor_builder.call_args.kwargs["factor_names"], ("supertrend_volume_confirmed_10_3_20",))

    def test_experiment_grid_precomputes_public_formula_price_volume_factor_matrix(self):
        bars = _synthetic_public_technical_bars(asset_count=3, day_count=70)
        config = ExperimentGridConfig(
            markets=("CN",),
            factor_source="public_formula_price_volume",
            factor_names=("formula_pv_corr_reversal_20",),
            top_n_values=(1,),
            cost_bps_values=(0.0,),
            precompute_factor_matrix=True,
        )
        factors = compute_public_formula_price_volume_factors(
            bars,
            factor_names=("formula_pv_corr_reversal_20",),
        )

        with patch(
            "quant_robot.experiments.runner.compute_public_formula_price_volume_factors",
            return_value=factors,
        ) as factor_builder:
            run_experiment_grid(bars, config)

        self.assertEqual(factor_builder.call_args.kwargs["factor_names"], ("formula_pv_corr_reversal_20",))

    def test_experiment_grid_runs_etf_share_size_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = load_demo_market_bars()
            _write_etf_share_size_inputs(root, bars)
            config = ExperimentGridConfig(
                markets=("CN_ETF",),
                factor_source="etf_share_size",
                factor_input_root=root,
                factor_input_required=True,
                factor_names=("share_change_1d",),
                factor_windows=(1,),
                top_n_values=(1,),
                cost_bps_values=(5.0,),
            )

            result = run_experiment_grid(bars, config)

            row = result["leaderboard"][0]
            self.assertEqual(row["status"], "completed")
            self.assertEqual(row["factor_name"], "share_change_1d")
            self.assertEqual(result["config"]["factor_source"], "etf_share_size")
            self.assertEqual(result["config"]["factor_input_root"], str(root))

    def test_experiment_grid_runs_etf_moneyflow_basket_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = load_demo_market_bars()
            _write_moneyflow_inputs(root, bars)
            _write_etf_moneyflow_baskets(root, bars)
            config = ExperimentGridConfig(
                markets=("CN_ETF",),
                factor_source="etf_moneyflow_basket",
                factor_input_root=root,
                factor_input_required=True,
                moneyflow_input_root=root,
                factor_names=("etf_net_mf_amount_ratio",),
                factor_windows=(1,),
                top_n_values=(1,),
                cost_bps_values=(5.0,),
                precompute_factor_matrix=True,
            )

            result = run_experiment_grid(bars, config)

            row = result["leaderboard"][0]
            self.assertEqual(row["status"], "completed")
            self.assertEqual(row["factor_name"], "etf_net_mf_amount_ratio")
            self.assertEqual(result["config"]["factor_source"], "etf_moneyflow_basket")
            self.assertEqual(result["config"]["factor_input_root"], str(root))
            self.assertEqual(result["config"]["moneyflow_input_root"], str(root))

    def test_experiment_grid_runs_etf_theme_breadth_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = _theme_breadth_runner_bars()
            _write_etf_theme_fund_basic(root, bars)
            config = ExperimentGridConfig(
                markets=("CN_ETF",),
                factor_source="etf_theme_breadth",
                factor_input_root=root,
                factor_input_required=True,
                factor_names=("theme_momentum_breadth_2",),
                factor_windows=(2,),
                top_n_values=(1,),
                cost_bps_values=(5.0,),
                precompute_factor_matrix=True,
            )

            result = run_experiment_grid(bars, config)

            row = result["leaderboard"][0]
            self.assertEqual(row["status"], "completed")
            self.assertEqual(row["factor_name"], "theme_momentum_breadth_2")
            self.assertEqual(result["config"]["factor_source"], "etf_theme_breadth")
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

    def test_experiment_grid_can_reuse_research_inputs_across_topn_and_cost_variants(self):
        config = ExperimentGridConfig(
            markets=("CN",),
            factor_names=("momentum_2",),
            factor_windows=(2,),
            top_n_values=(1, 2),
            cost_bps_values=(0.0, 5.0),
            reuse_research_inputs=True,
        )
        prepared = SimpleNamespace(selected=[1], labels=[1], ic=[1])
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
            patch("quant_robot.experiments.runner.prepare_research_pipeline_inputs", return_value=prepared) as prepare,
            patch("quant_robot.experiments.runner.run_research_pipeline", return_value=pipeline_result) as pipeline,
        ):
            result = run_experiment_grid(load_demo_market_bars(), config)

        self.assertEqual(len(result["leaderboard"]), 4)
        prepare.assert_called_once()
        self.assertEqual(len(pipeline.call_args_list), 4)
        self.assertTrue(all(call.kwargs["prepared_inputs"] is prepared for call in pipeline.call_args_list))

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

    def test_experiment_grid_can_precompute_daily_basic_technical_combo_factor_matrix_once(self):
        bars = load_demo_market_bars()
        matrix = pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value", "lookback_window"])
        config = ExperimentGridConfig(
            markets=("CN",),
            factor_source="daily_basic_technical_combo",
            factor_input_root=Path("authority_daily_basic.json"),
            factor_input_required=True,
            factor_names=("turnover_rate_low_liquid_mv_bucket_rank",),
            factor_windows=(20,),
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
            patch("quant_robot.experiments.runner.compute_daily_basic_technical_combo_factors", return_value=matrix) as factor_builder,
            patch("quant_robot.experiments.runner.run_research_pipeline", return_value=pipeline_result) as pipeline,
        ):
            result = run_experiment_grid(bars, config)

        self.assertEqual(len(result["leaderboard"]), 2)
        loader.assert_called_once_with(Path("authority_daily_basic.json"), "CN")
        factor_builder.assert_called_once()
        precompute_bars = factor_builder.call_args.args[0]
        self.assertEqual(set(precompute_bars["market"]), {"CN"})
        self.assertEqual(factor_builder.call_args.kwargs["factor_names"], ("turnover_rate_low_liquid_mv_bucket_rank",))
        self.assertTrue(all(call.kwargs["precomputed_factors"] is matrix for call in pipeline.call_args_list))

    def test_experiment_grid_can_precompute_daily_basic_value_liquidity_tail_factor_matrix_once(self):
        bars = load_demo_market_bars()
        matrix = pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value", "lookback_window"])
        config = ExperimentGridConfig(
            markets=("CN",),
            factor_source="daily_basic_value_liquidity_tail",
            factor_input_root=Path("authority_daily_basic.json"),
            factor_input_required=True,
            factor_names=("value_liquid_low_tail_20",),
            factor_windows=(20,),
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
            patch("quant_robot.experiments.runner.compute_daily_basic_value_liquidity_tail_factors", return_value=matrix) as factor_builder,
            patch("quant_robot.experiments.runner.run_research_pipeline", return_value=pipeline_result) as pipeline,
        ):
            result = run_experiment_grid(bars, config)

        self.assertEqual(len(result["leaderboard"]), 2)
        loader.assert_called_once_with(Path("authority_daily_basic.json"), "CN")
        factor_builder.assert_called_once()
        precompute_bars = factor_builder.call_args.args[0]
        self.assertEqual(set(precompute_bars["market"]), {"CN"})
        self.assertEqual(factor_builder.call_args.kwargs["factor_names"], ("value_liquid_low_tail_20",))
        self.assertTrue(all(call.kwargs["precomputed_factors"] is matrix for call in pipeline.call_args_list))

    def test_experiment_grid_can_precompute_daily_basic_residual_composite_factor_matrix_once(self):
        bars = load_demo_market_bars()
        matrix = pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value", "lookback_window"])
        config = ExperimentGridConfig(
            markets=("CN",),
            factor_source="daily_basic_residual_composite",
            factor_input_root=Path("authority_daily_basic.json"),
            factor_input_required=True,
            factor_names=("resid_value_quality_low_vol_20",),
            factor_windows=(20,),
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
            patch("quant_robot.experiments.runner.compute_daily_basic_residual_composite_factors", return_value=matrix) as factor_builder,
            patch("quant_robot.experiments.runner.run_research_pipeline", return_value=pipeline_result) as pipeline,
        ):
            result = run_experiment_grid(bars, config)

        self.assertEqual(len(result["leaderboard"]), 2)
        loader.assert_called_once_with(Path("authority_daily_basic.json"), "CN")
        factor_builder.assert_called_once()
        precompute_bars = factor_builder.call_args.args[0]
        self.assertEqual(set(precompute_bars["market"]), {"CN"})
        self.assertEqual(factor_builder.call_args.kwargs["factor_names"], ("resid_value_quality_low_vol_20",))
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
                        "min_total_return": 0.02,
                        "min_relative_return": 0.01,
                        "target_gross_exposure": 0.9,
                        "regime_lookback_values": [60, 120],
                        "precompute_factor_matrix": True,
                        "reuse_research_inputs": True,
                        "write_case_artifacts": False,
                        "asset_universe_path": str(Path(tmp) / "universe.json"),
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
            self.assertAlmostEqual(config.min_total_return, 0.02)
            self.assertAlmostEqual(config.min_relative_return, 0.01)
            self.assertAlmostEqual(config.target_gross_exposure, 0.9)
            self.assertEqual(config.regime_lookback_values, (60, 120))
            self.assertTrue(config.precompute_factor_matrix)
            self.assertTrue(config.reuse_research_inputs)
            self.assertFalse(config.write_case_artifacts)
            self.assertEqual(config.asset_universe_path, Path(tmp) / "universe.json")
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


def _write_etf_share_size_inputs(root: Path, bars: pd.DataFrame) -> None:
    from quant_robot.storage.dataset_store import DatasetStore

    rows = []
    for asset_index, (asset_id, group) in enumerate(bars[bars["market"] == "CN_ETF"].groupby("asset_id", sort=True), start=1):
        symbol = group["symbol"].iloc[0]
        for index, row in group.reset_index(drop=True).iterrows():
            rows.append(
                {
                    "date": row["date"],
                    "asset_id": asset_id,
                    "symbol": symbol,
                    "market": "CN_ETF",
                    "source": "tushare_etf_share_size",
                    "total_share": 10_000_000.0 + index * 100_000.0 * asset_index,
                    "total_size": 40_000_000.0 + index * 800_000.0 * asset_index,
                    "nav": row["close"],
                    "close": row["close"] * (1.0 + 0.001 * asset_index),
                    "share_change_1d": pd.NA if index == 0 else 0.01 * asset_index,
                    "size_change_1d": pd.NA if index == 0 else 0.02 * asset_index,
                    "nav_premium_discount": 0.001 * asset_index,
                }
            )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/etf_share_size",
        {"frequency": "1d", "market": "CN_ETF", "year": "2024"},
    )


def _write_moneyflow_inputs(root: Path, bars: pd.DataFrame) -> None:
    from quant_robot.storage.dataset_store import DatasetStore

    rows = []
    for _, row in bars[bars["market"] == "CN"].reset_index(drop=True).iterrows():
        rows.append(
            {
                "date": row["date"],
                "asset_id": row["asset_id"],
                "symbol": row["symbol"],
                "market": "CN",
                "source": "tushare_moneyflow",
                "buy_sm_amount": 100.0,
                "sell_sm_amount": 80.0,
                "buy_md_amount": 300.0,
                "sell_md_amount": 250.0,
                "buy_lg_amount": 500.0,
                "sell_lg_amount": 450.0,
                "buy_elg_amount": 700.0,
                "sell_elg_amount": 650.0,
                "net_mf_amount": 120.0,
            }
        )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/moneyflow_inputs",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


def _write_etf_moneyflow_baskets(root: Path, bars: pd.DataFrame) -> None:
    from quant_robot.storage.dataset_store import DatasetStore

    cn_assets = bars[bars["market"] == "CN"].drop_duplicates("asset_id").sort_values("asset_id")
    etf_assets = bars[bars["market"] == "CN_ETF"].drop_duplicates("asset_id").sort_values("asset_id")
    rows = []
    for etf in etf_assets.itertuples(index=False):
        for stock in cn_assets.itertuples(index=False):
            rows.append(
                {
                    "etf_asset_id": etf.asset_id,
                    "etf_symbol": etf.symbol,
                    "stock_asset_id": stock.asset_id,
                    "stock_symbol": stock.symbol,
                    "weight": 1.0,
                    "known_date": pd.Timestamp("2024-01-01").date(),
                    "end_date": pd.NaT,
                    "source": "fixture_basket",
                }
            )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "metadata/etf_moneyflow_baskets",
        {"market": "CN_ETF"},
    )


def _write_etf_theme_fund_basic(root: Path, bars: pd.DataFrame) -> None:
    from quant_robot.storage.dataset_store import DatasetStore

    etf_assets = bars[bars["market"] == "CN_ETF"].drop_duplicates("asset_id").sort_values("asset_id")
    names = ["华泰柏瑞沪深300ETF", "南方中证500ETF", "华夏中证全指证券公司ETF", "国泰中证全指证券公司ETF"]
    rows = []
    for index, row in enumerate(etf_assets.itertuples(index=False)):
        rows.append(
            {
                "symbol": row.symbol,
                "name": names[index % len(names)],
                "market": "E",
                "status": "L",
                "fund_type": "equity",
                "type": "equity",
                "is_etf": True,
                "list_date": "2024-01-01",
                "delist_date": None,
            }
        )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "metadata/tushare_fund_basic",
        {"market": "E", "snapshot": "2024-01-01"},
    )


def _theme_breadth_runner_bars() -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2024-01-01", periods=8).date
    paths = {
        "CN_ETF_XSHG_510300": [10.0, 10.2, 10.5, 10.8, 11.2, 11.5, 11.8, 12.0],
        "CN_ETF_XSHG_510500": [8.0, 8.1, 8.2, 8.4, 8.5, 8.7, 8.8, 9.0],
        "CN_ETF_XSHG_512880": [5.0, 5.1, 5.3, 5.6, 5.8, 6.1, 6.2, 6.4],
        "CN_ETF_XSHG_512000": [4.0, 4.0, 4.1, 4.1, 4.2, 4.2, 4.3, 4.3],
    }
    symbols = {
        "CN_ETF_XSHG_510300": "510300.SH",
        "CN_ETF_XSHG_510500": "510500.SH",
        "CN_ETF_XSHG_512880": "512880.SH",
        "CN_ETF_XSHG_512000": "512000.SH",
    }
    for asset_id, prices in paths.items():
        for date, price in zip(dates, prices, strict=True):
            rows.append(
                {
                    "asset_id": asset_id,
                    "symbol": symbols[asset_id],
                    "market": "CN_ETF",
                    "exchange": "XSHG",
                    "asset_type": "etf",
                    "timestamp": pd.Timestamp(date).tz_localize("UTC"),
                    "date": date,
                    "timezone": "Asia/Shanghai",
                    "calendar": "XSHG",
                    "frequency": "1d",
                    "source": "fixture",
                    "open": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "close": price,
                    "vwap": price,
                    "adj_close": price,
                    "volume": 1000.0,
                    "amount": price * 1000.0,
                    "currency": "CNY",
                    "adjusted": True,
                    "ingested_at": pd.Timestamp("2024-01-01T00:00:00Z"),
                }
            )
    return pd.DataFrame(rows)


def _synthetic_public_technical_bars(*, asset_count: int, day_count: int) -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2024-01-01", periods=day_count, freq="B")
    ingested_at = pd.Timestamp("2026-06-21", tz="UTC")
    for asset_index in range(asset_count):
        for day_index, date in enumerate(dates):
            price = 10.0 + asset_index + day_index * (0.05 + asset_index * 0.01)
            rows.append(
                {
                    "asset_id": f"CN_XSHG_{asset_index:06d}",
                    "symbol": f"{asset_index:06d}.SH",
                    "market": "CN",
                    "exchange": "XSHG",
                    "asset_type": "stock",
                    "timestamp": date.tz_localize("Asia/Shanghai"),
                    "date": date.date(),
                    "timezone": "Asia/Shanghai",
                    "calendar": "XSHG",
                    "frequency": "1d",
                    "source": "fixture",
                    "open": price * 0.995,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "close": price,
                    "vwap": price,
                    "adj_close": price,
                    "volume": 1_000_000 + asset_index * 10_000 + day_index * 1000,
                    "amount": price * (1_000_000 + asset_index * 10_000 + day_index * 1000),
                    "currency": "CNY",
                    "adjusted": True,
                    "ingested_at": ingested_at,
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
