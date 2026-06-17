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
            self.assertIn("test_tail_ic_p_value", leaderboard[0])
            self.assertIn("test_tail_ic_observations", leaderboard[0])
            self.assertIn("test_tail_significance_status", leaderboard[0])
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

    def test_walk_forward_bar_start_date_limits_rolling_fold_dates(self):
        config = WalkForwardConfig(
            split_date="2024-01-08",
            bar_start_date="2024-01-04",
            experiment_grid=ExperimentGridConfig(
                markets=("CN_ETF",),
                factor_names=("momentum_2",),
                factor_windows=(2,),
                top_n_values=(1,),
                cost_bps_values=(0.0,),
            ),
            min_test_sharpe=-999.0,
            rolling_train_days=4,
            rolling_test_days=3,
            rolling_step_days=2,
        )

        result = run_walk_forward_validation(load_demo_market_bars(), config)

        fold_starts = {pd.to_datetime(row["train_start_date"]).date() for row in result["folds"]}
        self.assertGreaterEqual(min(fold_starts), pd.Timestamp("2024-01-04").date())
        self.assertEqual(result["config"]["bar_start_date"], "2024-01-04")

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
                            "moneyflow_input_root": str(Path(tmp) / "moneyflow_inputs"),
                            "top_n_values": [1],
                            "cost_bps_values": [5],
                            "rebalance_intervals": [5],
                            "benchmark_asset_id": "CN_ETF_XSHG_510300",
                            "regime_lookback_values": [60, 120],
                            "min_rotation_history_rows": 252,
                            "min_rotation_live_members": 50,
                            "min_signal_average_amount": 10000000,
                            "signal_amount_window": 20,
                            "precompute_factor_matrix": True,
                        },
                        "bar_start_date": "2024-01-01",
                        "bar_end_date": "2024-12-31",
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
            self.assertEqual(config.bar_start_date, "2024-01-01")
            self.assertEqual(config.bar_end_date, "2024-12-31")
            self.assertEqual(config.min_test_sharpe, 0.5)
            self.assertAlmostEqual(config.min_test_relative_return, 0.02)
            self.assertAlmostEqual(config.max_test_drawdown, 0.20)
            self.assertEqual(config.experiment_grid.markets, ("CN",))
            self.assertEqual(config.experiment_grid.factor_source, "tushare_daily_basic")
            self.assertEqual(config.experiment_grid.moneyflow_input_root, Path(tmp) / "moneyflow_inputs")
            self.assertEqual(config.experiment_grid.cost_bps_values, (5.0,))
            self.assertEqual(config.experiment_grid.rebalance_intervals, (5,))
            self.assertEqual(config.experiment_grid.benchmark_asset_id, "CN_ETF_XSHG_510300")
            self.assertEqual(config.experiment_grid.regime_lookback_values, (60, 120))
            self.assertEqual(config.experiment_grid.min_rotation_history_rows, 252)
            self.assertEqual(config.experiment_grid.min_rotation_live_members, 50)
            self.assertEqual(config.experiment_grid.min_signal_average_amount, 10000000.0)
            self.assertEqual(config.experiment_grid.signal_amount_window, 20)
            self.assertTrue(config.experiment_grid.precompute_factor_matrix)
            self.assertEqual(config.rolling_train_days, 252)
            self.assertEqual(config.rolling_test_days, 63)
            self.assertEqual(config.rolling_step_days, 21)
            self.assertEqual(config.min_accepted_folds, 3)
            self.assertAlmostEqual(config.multiple_testing_alpha, 0.01)

    def test_load_walk_forward_config_accepts_utf8_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "walk_forward.json"
            config_path.write_text(
                json.dumps(
                    {
                        "split_date": "2024-01-08",
                        "experiment_grid": {
                            "markets": ["CN_ETF"],
                            "factor_names": ["momentum_2"],
                            "factor_windows": [2],
                        },
                    }
                ),
                encoding="utf-8-sig",
            )

            config = load_walk_forward_config(config_path)

            self.assertEqual(config.split_date, "2024-01-08")
            self.assertEqual(config.experiment_grid.markets, ("CN_ETF",))

    def test_tushare_cn_etf_rotation_config_covers_core_hypothesis_families_and_cost_controls(self):
        config = load_walk_forward_config("configs/walk_forward_tushare_cn_etf_rotation.json")

        self.assertEqual(config.experiment_grid.markets, ("CN_ETF",))
        self.assertTrue(config.experiment_grid.rotation_membership_required)
        self.assertEqual(config.experiment_grid.benchmark_asset_id, "CN_ETF_XSHG_510050")
        self.assertEqual(config.experiment_grid.execution_lag, 1)
        self.assertGreater(config.experiment_grid.market_impact_bps, 0)
        self.assertIsNotNone(config.experiment_grid.max_participation_rate)
        self.assertGreaterEqual(config.rolling_train_days or 0, 252)
        self.assertGreater(config.rolling_test_days or 0, 0)
        self.assertIn("momentum_20", config.experiment_grid.factor_names)
        self.assertIn("reversal_20", config.experiment_grid.factor_names)
        self.assertIn("liquidity_20", config.experiment_grid.factor_names)
        self.assertIn("volatility_20", config.experiment_grid.factor_names)
        self.assertIn("risk_adjusted_momentum_60", config.experiment_grid.factor_names)

    def test_tushare_cn_etf_rotation_seed_config_covers_three_active_primary_families(self):
        config = load_walk_forward_config("configs/walk_forward_tushare_cn_etf_rotation_seed_20260617.json")

        self.assertEqual(config.experiment_grid.markets, ("CN_ETF",))
        self.assertTrue(config.experiment_grid.rotation_membership_required)
        self.assertEqual(config.experiment_grid.benchmark_asset_id, "CN_ETF_XSHG_510050")
        self.assertEqual(config.experiment_grid.execution_lag, 1)
        self.assertEqual(config.experiment_grid.top_n_values, (2,))
        self.assertEqual(config.experiment_grid.cost_bps_values, (10.0,))
        self.assertEqual(config.experiment_grid.rebalance_intervals, (10,))
        self.assertGreater(config.experiment_grid.market_impact_bps, 0)
        self.assertEqual(config.experiment_grid.max_participation_rate, 0.05)
        self.assertGreaterEqual(config.min_accepted_folds, 3)
        self.assertIn("momentum_60", config.experiment_grid.factor_names)
        self.assertIn("reversal_20", config.experiment_grid.factor_names)
        self.assertIn("liquidity_60", config.experiment_grid.factor_names)
        self.assertIn("volatility_60", config.experiment_grid.factor_names)

    def test_tushare_cn_etf_defensive_seed_config_covers_drawdown_volatility_and_capacity(self):
        config = load_walk_forward_config("configs/walk_forward_tushare_cn_etf_defensive_seed_20260617.json")

        self.assertEqual(config.experiment_grid.markets, ("CN_ETF",))
        self.assertTrue(config.experiment_grid.rotation_membership_required)
        self.assertEqual(config.experiment_grid.benchmark_asset_id, "CN_ETF_XSHG_510050")
        self.assertEqual(config.experiment_grid.factor_windows, (60,))
        self.assertEqual(config.experiment_grid.execution_lag, 1)
        self.assertEqual(config.experiment_grid.top_n_values, (2,))
        self.assertEqual(config.experiment_grid.cost_bps_values, (10.0,))
        self.assertGreater(config.experiment_grid.market_impact_bps, 0)
        self.assertEqual(config.experiment_grid.max_participation_rate, 0.05)
        self.assertIn("low_volatility_60", config.experiment_grid.factor_names)
        self.assertIn("low_downside_volatility_60", config.experiment_grid.factor_names)
        self.assertIn("drawdown_resilience_60", config.experiment_grid.factor_names)
        self.assertIn("liquidity_resilience_60", config.experiment_grid.factor_names)
        self.assertIn("amount_stability_60", config.experiment_grid.factor_names)

    def test_tushare_cn_etf_composite_seed_config_covers_price_defense_and_capacity_mix(self):
        config = load_walk_forward_config("configs/walk_forward_tushare_cn_etf_composite_seed_20260617.json")

        self.assertEqual(config.experiment_grid.markets, ("CN_ETF",))
        self.assertTrue(config.experiment_grid.rotation_membership_required)
        self.assertEqual(config.experiment_grid.benchmark_asset_id, "CN_ETF_XSHG_510050")
        self.assertEqual(config.experiment_grid.factor_windows, (60,))
        self.assertEqual(config.experiment_grid.execution_lag, 1)
        self.assertEqual(config.experiment_grid.top_n_values, (2,))
        self.assertEqual(config.experiment_grid.cost_bps_values, (10.0,))
        self.assertGreater(config.experiment_grid.market_impact_bps, 0)
        self.assertEqual(config.experiment_grid.max_participation_rate, 0.05)
        self.assertIn("trend_resilience_60", config.experiment_grid.factor_names)
        self.assertIn("risk_confirmed_momentum_60", config.experiment_grid.factor_names)
        self.assertIn("defensive_reversal_60", config.experiment_grid.factor_names)
        self.assertIn("liquidity_confirmed_breakout_60", config.experiment_grid.factor_names)

    def test_tushare_cn_etf_composite_mature_diagnostic_has_explicit_bar_window(self):
        config = load_walk_forward_config("configs/walk_forward_tushare_cn_etf_composite_mature_diagnostic_20260617.json")

        self.assertEqual(config.bar_start_date, "2015-01-01")
        self.assertEqual(config.experiment_grid.markets, ("CN_ETF",))
        self.assertTrue(config.experiment_grid.rotation_membership_required)
        self.assertEqual(config.experiment_grid.benchmark_asset_id, "CN_ETF_XSHG_510050")
        self.assertEqual(config.experiment_grid.factor_windows, (60,))
        self.assertEqual(config.experiment_grid.execution_lag, 1)
        self.assertGreaterEqual(config.min_accepted_folds, 3)
        self.assertIn("trend_resilience_60", config.experiment_grid.factor_names)
        self.assertIn("liquidity_confirmed_breakout_60", config.experiment_grid.factor_names)

    def test_tushare_cn_etf_structure_shift_config_covers_dispersion_recovery_and_demand(self):
        config = load_walk_forward_config("configs/walk_forward_tushare_cn_etf_structure_shift_20260617.json")

        self.assertEqual(config.experiment_grid.markets, ("CN_ETF",))
        self.assertTrue(config.experiment_grid.rotation_membership_required)
        self.assertEqual(config.experiment_grid.benchmark_asset_id, "CN_ETF_XSHG_510050")
        self.assertEqual(config.experiment_grid.factor_windows, (60,))
        self.assertEqual(config.experiment_grid.execution_lag, 1)
        self.assertEqual(config.experiment_grid.top_n_values, (2,))
        self.assertEqual(config.experiment_grid.cost_bps_values, (10.0,))
        self.assertGreater(config.experiment_grid.market_impact_bps, 0)
        self.assertEqual(config.experiment_grid.max_participation_rate, 0.05)
        self.assertIn("market_relative_strength_60", config.experiment_grid.factor_names)
        self.assertIn("momentum_dispersion_breakout_60", config.experiment_grid.factor_names)
        self.assertIn("crash_recovery_60", config.experiment_grid.factor_names)
        self.assertIn("recovery_quality_60", config.experiment_grid.factor_names)
        self.assertIn("demand_pressure_60", config.experiment_grid.factor_names)
        self.assertIn("quiet_accumulation_60", config.experiment_grid.factor_names)

    def test_tushare_cn_etf_liquidity_gated_structure_config_keeps_capacity_gate_explicit(self):
        config = load_walk_forward_config("configs/walk_forward_tushare_cn_etf_liquidity_gated_structure_20260617.json")

        self.assertEqual(config.experiment_grid.markets, ("CN_ETF",))
        self.assertTrue(config.experiment_grid.rotation_membership_required)
        self.assertEqual(config.experiment_grid.benchmark_asset_id, "CN_ETF_XSHG_510050")
        self.assertEqual(config.experiment_grid.factor_windows, (60,))
        self.assertEqual(config.experiment_grid.execution_lag, 1)
        self.assertEqual(config.experiment_grid.top_n_values, (2,))
        self.assertEqual(config.experiment_grid.cost_bps_values, (10.0,))
        self.assertGreater(config.experiment_grid.market_impact_bps, 0)
        self.assertEqual(config.experiment_grid.max_participation_rate, 0.05)
        self.assertIn("average_amount_60", config.experiment_grid.factor_names)
        self.assertIn("liquid_market_relative_strength_60", config.experiment_grid.factor_names)
        self.assertIn("liquid_crash_recovery_60", config.experiment_grid.factor_names)
        self.assertIn("liquid_recovery_quality_60", config.experiment_grid.factor_names)
        self.assertIn("liquid_demand_pressure_60", config.experiment_grid.factor_names)
        self.assertIn("liquid_quiet_accumulation_60", config.experiment_grid.factor_names)

    def test_tushare_cn_etf_notional_filtered_structure_config_uses_absolute_amount_gate(self):
        config = load_walk_forward_config("configs/walk_forward_tushare_cn_etf_notional_filtered_structure_20260617.json")

        self.assertEqual(config.experiment_grid.markets, ("CN_ETF",))
        self.assertTrue(config.experiment_grid.rotation_membership_required)
        self.assertEqual(config.experiment_grid.benchmark_asset_id, "CN_ETF_XSHG_510050")
        self.assertEqual(config.experiment_grid.factor_windows, (60,))
        self.assertEqual(config.experiment_grid.execution_lag, 1)
        self.assertEqual(config.experiment_grid.max_participation_rate, 0.05)
        self.assertEqual(config.experiment_grid.min_signal_average_amount, 8000000.0)
        self.assertEqual(config.experiment_grid.signal_amount_window, 60)
        self.assertIn("market_relative_strength_60", config.experiment_grid.factor_names)
        self.assertIn("crash_recovery_60", config.experiment_grid.factor_names)
        self.assertIn("average_amount_60", config.experiment_grid.factor_names)

    def test_tushare_cn_etf_maturity_filtered_structure_config_uses_age_and_universe_controls(self):
        config = load_walk_forward_config("configs/walk_forward_tushare_cn_etf_maturity_filtered_structure_20260617.json")

        self.assertEqual(config.experiment_grid.markets, ("CN_ETF",))
        self.assertTrue(config.experiment_grid.rotation_membership_required)
        self.assertEqual(config.experiment_grid.min_rotation_history_rows, 252)
        self.assertEqual(config.experiment_grid.min_rotation_live_members, 50)
        self.assertEqual(config.experiment_grid.min_signal_average_amount, 8000000.0)
        self.assertEqual(config.experiment_grid.signal_amount_window, 60)
        self.assertEqual(config.experiment_grid.execution_lag, 1)
        self.assertEqual(config.experiment_grid.max_participation_rate, 0.05)
        self.assertIn("market_relative_strength_60", config.experiment_grid.factor_names)
        self.assertIn("crash_recovery_60", config.experiment_grid.factor_names)
        self.assertIn("recovery_quality_60", config.experiment_grid.factor_names)
        self.assertIn("average_amount_60", config.experiment_grid.factor_names)

    def test_tushare_cn_etf_share_size_config_covers_structure_hypothesis_family(self):
        config = load_walk_forward_config("configs/walk_forward_tushare_cn_etf_share_size.json")

        self.assertEqual(config.experiment_grid.markets, ("CN_ETF",))
        self.assertEqual(config.experiment_grid.factor_source, "etf_share_size")
        self.assertEqual(config.experiment_grid.factor_input_root, Path("data/processed/tushare_etf_full"))
        self.assertTrue(config.experiment_grid.factor_input_required)
        self.assertTrue(config.experiment_grid.rotation_membership_required)
        self.assertEqual(config.experiment_grid.execution_lag, 1)
        self.assertIn("share_change_1d", config.experiment_grid.factor_names)
        self.assertIn("size_change_1d_low", config.experiment_grid.factor_names)
        self.assertIn("nav_premium_discount", config.experiment_grid.factor_names)
        self.assertIn("total_size_log", config.experiment_grid.factor_names)
        self.assertGreater(config.experiment_grid.market_impact_bps, 0)
        self.assertIsNotNone(config.experiment_grid.max_participation_rate)

    def test_tushare_cn_etf_moneyflow_basket_config_keeps_moneyflow_auxiliary(self):
        config = load_walk_forward_config("configs/walk_forward_tushare_cn_etf_moneyflow_basket.json")

        self.assertEqual(config.experiment_grid.markets, ("CN_ETF",))
        self.assertEqual(config.experiment_grid.factor_source, "etf_moneyflow_basket")
        self.assertEqual(config.experiment_grid.factor_input_root, Path("data/processed/tushare_etf_full"))
        self.assertEqual(config.experiment_grid.moneyflow_input_root, Path("data/processed/tushare_moneyflow_inputs"))
        self.assertTrue(config.experiment_grid.factor_input_required)
        self.assertTrue(config.experiment_grid.rotation_membership_required)
        self.assertEqual(config.experiment_grid.execution_lag, 1)
        self.assertIn("etf_net_mf_amount_ratio", config.experiment_grid.factor_names)
        self.assertIn("etf_large_order_net_amount_ratio", config.experiment_grid.factor_names)
        self.assertIn("etf_net_mf_positive_weight_low", config.experiment_grid.factor_names)
        self.assertGreater(config.experiment_grid.market_impact_bps, 0)
        self.assertIsNotNone(config.experiment_grid.max_participation_rate)


if __name__ == "__main__":
    unittest.main()
