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

    def test_experiment_grid_passes_rotation_membership_options_to_pipeline(self):
        root = Path("data/processed/tushare_etf_full")
        config = ExperimentGridConfig(
            markets=("CN_ETF",),
            factor_names=("momentum_2",),
            factor_windows=(2,),
            top_n_values=(1,),
            cost_bps_values=(0.0,),
            rotation_membership_root=root,
            rotation_membership_required=True,
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
            run_experiment_grid(load_demo_market_bars(), config)

        passed_config = pipeline.call_args.args[1]
        self.assertEqual(passed_config.rotation_membership_root, root)
        self.assertTrue(passed_config.rotation_membership_required)

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
                        "rotation_membership_root": str(Path(tmp) / "membership"),
                        "rotation_membership_required": True,
                        "min_rotation_history_rows": 252,
                        "min_rotation_live_members": 50,
                        "min_signal_average_amount": 10000000,
                        "signal_amount_window": 20,
                        "output_dir": str(Path(tmp) / "reports"),
                    }
                ),
                encoding="utf-8",
            )

            config = load_experiment_grid_config(config_path)

            self.assertEqual(config.markets, ("CN",))
            self.assertEqual(config.factor_names, ("momentum_2",))
            self.assertEqual(config.rotation_membership_root, Path(tmp) / "membership")
            self.assertTrue(config.rotation_membership_required)
            self.assertEqual(config.min_rotation_history_rows, 252)
            self.assertEqual(config.min_rotation_live_members, 50)
            self.assertEqual(config.rebalance_intervals, (5,))
            self.assertEqual(config.benchmark_asset_id, "CN_ETF_XSHG_510300")
            self.assertAlmostEqual(config.min_relative_return, 0.01)
            self.assertAlmostEqual(config.target_gross_exposure, 0.9)
            self.assertEqual(config.regime_lookback_values, (60, 120))
            self.assertTrue(config.precompute_factor_matrix)
            self.assertEqual(config.output_dir, Path(tmp) / "reports")
            self.assertEqual(config.min_signal_average_amount, 10000000.0)
            self.assertEqual(config.signal_amount_window, 20)

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

    def test_load_experiment_grid_config_reads_etf_share_size_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "grid.json"
            factor_input_root = root / "tushare_etf_full"
            config_path.write_text(
                json.dumps(
                    {
                        "markets": ["CN_ETF"],
                        "factor_source": "etf_share_size",
                        "factor_input_root": str(factor_input_root),
                        "factor_input_required": True,
                        "factor_names": ["share_change_1d"],
                        "factor_windows": [1],
                    }
                ),
                encoding="utf-8",
            )

            config = load_experiment_grid_config(config_path)

            self.assertEqual(config.factor_source, "etf_share_size")
            self.assertEqual(config.factor_input_root, factor_input_root)
            self.assertEqual(config.factor_names, ("share_change_1d",))

    def test_load_experiment_grid_config_reads_etf_moneyflow_basket_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "grid.json"
            basket_root = root / "baskets"
            moneyflow_root = root / "moneyflow"
            config_path.write_text(
                json.dumps(
                    {
                        "markets": ["CN_ETF"],
                        "factor_source": "etf_moneyflow_basket",
                        "factor_input_root": str(basket_root),
                        "moneyflow_input_root": str(moneyflow_root),
                        "factor_input_required": True,
                        "factor_names": ["etf_net_mf_amount_ratio"],
                        "factor_windows": [1],
                    }
                ),
                encoding="utf-8",
            )

            config = load_experiment_grid_config(config_path)

            self.assertEqual(config.factor_source, "etf_moneyflow_basket")
            self.assertEqual(config.factor_input_root, basket_root)
            self.assertEqual(config.moneyflow_input_root, moneyflow_root)
            self.assertEqual(config.factor_names, ("etf_net_mf_amount_ratio",))

    def test_load_experiment_grid_config_reads_etf_theme_breadth_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "grid.json"
            factor_input_root = root / "tushare_etf_full"
            config_path.write_text(
                json.dumps(
                    {
                        "markets": ["CN_ETF"],
                        "factor_source": "etf_theme_breadth",
                        "factor_input_root": str(factor_input_root),
                        "factor_input_required": True,
                        "factor_names": ["theme_momentum_breadth_60"],
                        "factor_windows": [60],
                    }
                ),
                encoding="utf-8",
            )

            config = load_experiment_grid_config(config_path)

            self.assertEqual(config.factor_source, "etf_theme_breadth")
            self.assertEqual(config.factor_input_root, factor_input_root)
            self.assertEqual(config.factor_names, ("theme_momentum_breadth_60",))


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
        for index, row in group.sort_values("date").reset_index(drop=True).iterrows():
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
    for index, row in bars[bars["market"] == "CN"].reset_index(drop=True).iterrows():
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
                "net_mf_amount": 50.0 + index,
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
    names = ["华泰柏瑞沪深300ETF", "南方中证500ETF", "华宝中证银行ETF", "国泰中证全指证券公司ETF"]
    rows = []
    for index, row in enumerate(etf_assets.itertuples(index=False)):
        rows.append(
            {
                "symbol": row.symbol,
                "name": names[index % len(names)],
                "market": "E",
                "status": "L",
                "fund_type": "股票型",
                "type": "股票型",
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
        "CN_ETF_XSHG_512800": [6.0, 5.9, 5.8, 5.7, 5.6, 5.5, 5.4, 5.3],
        "CN_ETF_XSHG_512880": [7.0, 7.1, 7.0, 7.2, 7.1, 7.3, 7.2, 7.4],
    }
    symbols = {
        "CN_ETF_XSHG_510300": "510300.SH",
        "CN_ETF_XSHG_510500": "510500.SH",
        "CN_ETF_XSHG_512800": "512800.SH",
        "CN_ETF_XSHG_512880": "512880.SH",
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
                    "open": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "close": price,
                    "adj_close": price,
                    "volume": 1000.0,
                    "amount": price * 1000.0,
                    "vwap": price,
                    "currency": "CNY",
                    "source": "fixture",
                    "adjusted": True,
                    "ingested_at": pd.Timestamp("2024-01-01", tz="UTC"),
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
