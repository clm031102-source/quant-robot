import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.factors.technical import compute_basic_factors
from quant_robot.research.pipeline import ResearchPipelineConfig, _factor_summary, run_research_pipeline
from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.storage.processed_bars import load_processed_bars
from scripts.run_research_pipeline import build_research_config, load_research_bars


class ResearchPipelineTests(unittest.TestCase):
    def test_pipeline_runs_configurable_factor_backtest_and_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = ResearchPipelineConfig(
                factor_name="momentum_2",
                factor_windows=(2, 3),
                market="ALL",
                top_n=2,
                cost_bps=5.0,
                output_dir=Path(tmp),
            )

            result = run_research_pipeline(load_demo_market_bars(), config)

            self.assertEqual(result["request"]["factor_name"], "momentum_2")
            self.assertEqual(result["request"]["market"], "ALL")
            self.assertIn("annualized_return", result["metrics"])
            self.assertIn("icir", result["factor_summary"])
            self.assertIn("ic_observations", result["factor_summary"])
            self.assertIn("positive_ic_rate", result["factor_summary"])
            self.assertIn("ic_t_stat", result["factor_summary"])
            self.assertIn("ic_p_value", result["factor_summary"])
            self.assertIn("significance_status", result["factor_summary"])
            self.assertIn("tail_mean_ic", result["factor_summary"])
            self.assertIn("tail_ic_p_value", result["factor_summary"])
            self.assertIn("tail_ic_observations", result["factor_summary"])
            self.assertIn("tail_significance_status", result["factor_summary"])
            self.assertGreater(result["artifact_rows"]["trades"], 0)
            self.assertGreater(result["artifact_rows"]["tail_ic"], 0)
            self.assertTrue((Path(tmp) / "metrics.json").exists())
            self.assertTrue((Path(tmp) / "factor_summary.json").exists())
            self.assertTrue((Path(tmp) / "tail_ic.csv").exists())
            self.assertTrue((Path(tmp) / "equity_curve.csv").exists())
            self.assertTrue((Path(tmp) / "drawdown_curve.csv").exists())
            self.assertTrue((Path(tmp) / "trades.csv").exists())
            saved = json.loads((Path(tmp) / "metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["data_mode"], "fixture")

    def test_pipeline_filters_market_without_cross_market_selection(self):
        config = ResearchPipelineConfig(factor_name="momentum_2", factor_windows=(2,), market="CN", top_n=1)

        result = run_research_pipeline(load_demo_market_bars(), config)

        self.assertEqual({row["market"] for row in result["trades"]}, {"CN"})
        self.assertEqual({row["market"] for row in result["holdings"]}, {"CN"})

    def test_pipeline_uses_forward_horizon_for_backtest_exit(self):
        config = ResearchPipelineConfig(factor_name="momentum_2", factor_windows=(2,), market="CN", top_n=1, forward_horizon=2)

        result = run_research_pipeline(load_demo_market_bars(), config)

        trade = result["trades"][0]
        self.assertEqual((pd.to_datetime(trade["exit_date"]) - pd.to_datetime(trade["entry_date"])).days, 2)

    def test_all_market_pipeline_uses_global_portfolio_scope(self):
        config = ResearchPipelineConfig(factor_name="momentum_2", factor_windows=(2,), market="ALL", top_n=2, cost_bps=0.0)

        result = run_research_pipeline(load_demo_market_bars(), config)

        weights_by_signal = {}
        for trade in result["trades"]:
            weights_by_signal.setdefault(trade["signal_date"], 0.0)
            weights_by_signal[trade["signal_date"]] += trade["target_weight"]
        self.assertTrue(weights_by_signal)
        self.assertTrue(all(abs(weight - 1.0) < 1e-9 for weight in weights_by_signal.values()))

    def test_crypto_pipeline_uses_crypto_annualization_period(self):
        config = ResearchPipelineConfig(factor_name="momentum_2", factor_windows=(2,), market="CRYPTO", top_n=1)

        result = run_research_pipeline(load_demo_market_bars(), config)

        self.assertEqual(result["request"]["periods_per_year"], 365)

    def test_cn_etf_pipeline_runs_on_dedicated_etf_market(self):
        config = ResearchPipelineConfig(factor_name="momentum_2", factor_windows=(2,), market="CN_ETF", top_n=2)

        result = run_research_pipeline(load_demo_market_bars(), config)

        self.assertEqual(result["request"]["market"], "CN_ETF")
        self.assertGreater(result["artifact_rows"]["trades"], 0)
        self.assertEqual(result["request"]["periods_per_year"], 252)

    def test_cn_etf_pipeline_filters_signals_to_rotation_membership(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = load_demo_market_bars()
            cn_etf = bars[bars["market"] == "CN_ETF"].copy()
            membership = cn_etf[["date", "asset_id", "market"]].copy()
            membership["symbol"] = membership["asset_id"].astype(str)
            membership["is_rotation_member"] = membership["asset_id"].eq("CN_ETF_XSHG_510300")
            membership["exclusion_reasons"] = membership["is_rotation_member"].map({True: "", False: "test_excluded"})
            DatasetStore(root).write_frame(
                membership,
                "metadata/cn_etf_rotation_membership",
                {"market": "CN_ETF"},
            )
            config = ResearchPipelineConfig(
                factor_name="momentum_2",
                factor_windows=(2,),
                market="CN_ETF",
                top_n=4,
                rotation_membership_root=root,
                rotation_membership_required=True,
            )

            result = run_research_pipeline(bars, config)

            self.assertGreater(result["artifact_rows"]["trades"], 0)
            self.assertEqual({row["asset_id"] for row in result["trades"]}, {"CN_ETF_XSHG_510300"})
            self.assertEqual(result["request"]["rotation_membership_root"], str(root))
            self.assertTrue(result["request"]["rotation_membership_required"])

    def test_cn_etf_pipeline_filters_signals_to_rotation_maturity_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = _falling_regime_bars()
            mature_asset = "CN_ETF_XSHG_510300"
            immature_asset = "CN_ETF_XSHG_510500"
            membership = bars[["date", "asset_id", "market"]].copy()
            membership["symbol"] = membership["asset_id"]
            membership["is_rotation_member"] = True
            membership["exclusion_reasons"] = ""
            membership["history_rows_to_date"] = membership.groupby("asset_id").cumcount() + 1
            membership.loc[membership["asset_id"].eq(immature_asset), "history_rows_to_date"] = 1
            DatasetStore(root).write_frame(
                membership,
                "metadata/cn_etf_rotation_membership",
                {"market": "CN_ETF"},
            )
            factors = bars[["date", "asset_id", "market"]].copy()
            factors["factor_name"] = "momentum_2"
            factors["factor_value"] = factors["asset_id"].map({mature_asset: 1.0, immature_asset: 2.0})
            factors["lookback_window"] = 2

            result = run_research_pipeline(
                bars,
                ResearchPipelineConfig(
                    factor_name="momentum_2",
                    factor_windows=(2,),
                    market="CN_ETF",
                    top_n=1,
                    rotation_membership_root=root,
                    rotation_membership_required=True,
                    min_rotation_history_rows=3,
                    min_rotation_live_members=1,
                ),
                precomputed_factors=factors,
            )

            self.assertGreater(result["artifact_rows"]["trades"], 0)
            self.assertEqual({row["asset_id"] for row in result["trades"]}, {mature_asset})
            self.assertEqual(result["request"]["min_rotation_history_rows"], 3)
            self.assertEqual(result["request"]["min_rotation_live_members"], 1)

    def test_pipeline_can_sample_signals_by_rebalance_interval(self):
        daily = run_research_pipeline(
            load_demo_market_bars(),
            ResearchPipelineConfig(factor_name="momentum_2", factor_windows=(2,), market="CN_ETF", top_n=1, rebalance_interval=1),
        )
        sampled = run_research_pipeline(
            load_demo_market_bars(),
            ResearchPipelineConfig(factor_name="momentum_2", factor_windows=(2,), market="CN_ETF", top_n=1, rebalance_interval=3),
        )

        self.assertEqual(sampled["request"]["rebalance_interval"], 3)
        self.assertLess(sampled["artifact_rows"]["trades"], daily["artifact_rows"]["trades"])
        self.assertLess(sampled["artifact_rows"]["factors"], daily["artifact_rows"]["factors"])

    def test_pipeline_filters_signals_by_absolute_rolling_amount(self):
        bars = _falling_regime_bars()
        liquid_asset = "CN_ETF_XSHG_510300"
        thin_asset = "CN_ETF_XSHG_510500"
        bars.loc[bars["asset_id"].eq(liquid_asset), "amount"] = 1_000_000.0
        bars.loc[bars["asset_id"].eq(thin_asset), "amount"] = 100.0
        factors = bars[["date", "asset_id", "market"]].copy()
        factors["factor_name"] = "momentum_2"
        factors["factor_value"] = factors["asset_id"].map({liquid_asset: 1.0, thin_asset: 2.0})
        factors["lookback_window"] = 2

        result = run_research_pipeline(
            bars,
            ResearchPipelineConfig(
                factor_name="momentum_2",
                factor_windows=(2,),
                market="CN_ETF",
                top_n=1,
                min_signal_average_amount=10_000.0,
                signal_amount_window=2,
            ),
            precomputed_factors=factors,
        )

        self.assertGreater(result["artifact_rows"]["trades"], 0)
        self.assertEqual({row["asset_id"] for row in result["trades"]}, {liquid_asset})
        self.assertEqual(result["request"]["min_signal_average_amount"], 10_000.0)
        self.assertEqual(result["request"]["signal_amount_window"], 2)

    def test_pipeline_auto_scales_annualization_for_sparse_rebalance_interval(self):
        result = run_research_pipeline(
            load_demo_market_bars(),
            ResearchPipelineConfig(factor_name="momentum_2", factor_windows=(2,), market="CN_ETF", top_n=1, rebalance_interval=5),
        )

        self.assertAlmostEqual(result["request"]["periods_per_year"], 252 / 5)

    def test_pipeline_attaches_benchmark_and_decision_metrics(self):
        result = run_research_pipeline(
            load_demo_market_bars(),
            ResearchPipelineConfig(
                factor_name="momentum_2",
                factor_windows=(2,),
                market="CN_ETF",
                top_n=1,
                benchmark_asset_id="CN_ETF_XSHG_510300",
                cash_annual_return=0.02,
                min_relative_return=-1.0,
            ),
        )

        self.assertIn("benchmark_metrics", result)
        self.assertIn("decision", result)
        self.assertIn("benchmark_curve", result)
        self.assertEqual(result["decision"]["decision_status"], "approved")
        self.assertIn("relative_return", result["benchmark_metrics"])
        self.assertEqual(result["request"]["benchmark_asset_id"], "CN_ETF_XSHG_510300")

    def test_factor_summary_marks_two_observations_as_insufficient_for_significance(self):
        summary = _factor_summary(pd.DataFrame({"ic": [0.10, 0.20], "rank_ic": [0.10, 0.20]}))

        self.assertEqual(summary["ic_observations"], 2)
        self.assertEqual(summary["significance_status"], "insufficient_data")
        self.assertEqual(summary["ic_p_value"], 1.0)
        self.assertEqual(summary["ic_t_stat"], 0.0)

    def test_factor_summary_marks_zero_variance_ic_as_insufficient_for_significance(self):
        summary = _factor_summary(pd.DataFrame({"ic": [0.10] * 20, "rank_ic": [0.10] * 20}))

        self.assertEqual(summary["ic_observations"], 20)
        self.assertEqual(summary["significance_status"], "insufficient_data")
        self.assertEqual(summary["ic_p_value"], 1.0)
        self.assertEqual(summary["ic_t_stat"], 0.0)

    def test_benchmark_curve_respects_signal_start_date(self):
        result = run_research_pipeline(
            _falling_regime_bars(),
            ResearchPipelineConfig(
                factor_name="momentum_2",
                factor_windows=(2,),
                market="CN_ETF",
                top_n=1,
                benchmark_asset_id="CN_ETF_XSHG_510300",
                signal_start_date="2024-01-04",
            ),
        )

        benchmark_dates = [pd.to_datetime(row["date"]).date() for row in result["benchmark_curve"]]
        self.assertTrue(benchmark_dates)
        self.assertGreaterEqual(min(benchmark_dates), pd.Timestamp("2024-01-04").date())

    def test_pipeline_regime_filter_reduces_trades_when_benchmark_is_falling(self):
        bars = _falling_regime_bars()
        baseline = run_research_pipeline(
            bars,
            ResearchPipelineConfig(factor_name="momentum_2", factor_windows=(2,), market="CN_ETF", top_n=1),
        )
        filtered = run_research_pipeline(
            bars,
            ResearchPipelineConfig(
                factor_name="momentum_2",
                factor_windows=(2,),
                market="CN_ETF",
                top_n=1,
                benchmark_asset_id="CN_ETF_XSHG_510300",
                regime_filter=True,
                regime_lookback=2,
            ),
        )

        self.assertGreater(baseline["artifact_rows"]["trades"], 0)
        self.assertLess(filtered["artifact_rows"]["trades"], baseline["artifact_rows"]["trades"])
        self.assertGreater(filtered["regime"]["blocked_signal_dates"], 0)

    def test_processed_bar_loader_accepts_store_root_or_processed_subdirectory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = load_demo_market_bars()
            cn_bars = bars[bars["market"] == "CN"].reset_index(drop=True)
            DatasetStore(root).write_frame(cn_bars, "processed/bars", {"frequency": "1d", "market": "CN", "year": "2024"})

            from_store_root = load_processed_bars(root, "CN")
            from_processed_root = load_processed_bars(root / "processed", "CN")
            from_bars_root = load_processed_bars(root / "processed" / "bars", "CN")

            self.assertEqual(len(from_store_root), len(cn_bars))
            self.assertEqual(len(from_processed_root), len(cn_bars))
            self.assertEqual(len(from_bars_root), len(cn_bars))

    def test_processed_bar_loader_discovers_nested_ingest_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            search_root = Path(tmp)
            store_root = search_root / "tushare_fixture"
            bars = load_demo_market_bars()
            cn_bars = bars[bars["market"] == "CN"].reset_index(drop=True)
            DatasetStore(store_root).write_frame(cn_bars, "processed/bars", {"frequency": "1d", "market": "CN", "year": "2024"})

            result = load_processed_bars(search_root, "CN")

            self.assertEqual(len(result), len(cn_bars))

    def test_research_cli_loader_supports_all_processed_markets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "store"
            bars = load_demo_market_bars()
            for market, group in bars.groupby("market"):
                DatasetStore(root).write_frame(
                    group.reset_index(drop=True),
                    "processed/bars",
                    {"frequency": "1d", "market": market, "year": "2024"},
                )

            result = load_research_bars("processed-bars", root, "ALL")

            self.assertEqual(set(result["market"]), {"CN", "CN_ETF", "HK", "US", "CRYPTO"})

    def test_research_cli_config_builder_passes_factor_input_options(self):
        args = SimpleNamespace(
            factor="pb_inverse",
            factor_source="tushare_daily_basic",
            factor_windows="2,3",
            market="CN",
            start_date=None,
            end_date=None,
            forward_horizon=1,
            execution_lag=1,
            rebalance_interval=1,
            top_n=1,
            cost_bps=5.0,
            portfolio_scope=None,
            periods_per_year=None,
            benchmark_asset_id=None,
            cash_annual_return=0.0,
            regime_filter=False,
            regime_lookback=20,
            min_relative_return=None,
            max_drawdown_limit=None,
            signal_start_date=None,
            signal_end_date=None,
            factor_input_root="data/processed/tushare_factor_inputs",
            factor_input_required=True,
            moneyflow_input_root=None,
            output_dir="data/reports/research_pipeline",
        )

        config = build_research_config(args)

        self.assertEqual(config.factor_name, "pb_inverse")
        self.assertEqual(config.factor_source, "tushare_daily_basic")
        self.assertEqual(config.factor_input_root, Path("data/processed/tushare_factor_inputs"))
        self.assertTrue(config.factor_input_required)

    def test_research_cli_config_builder_passes_moneyflow_input_root(self):
        args = SimpleNamespace(
            factor="net_mf_amount_ratio",
            factor_source="tushare_moneyflow",
            factor_windows="2,3",
            market="CN",
            start_date=None,
            end_date=None,
            forward_horizon=1,
            execution_lag=1,
            rebalance_interval=1,
            top_n=1,
            cost_bps=5.0,
            portfolio_scope=None,
            periods_per_year=None,
            benchmark_asset_id=None,
            cash_annual_return=0.0,
            regime_filter=False,
            regime_lookback=20,
            min_relative_return=None,
            max_drawdown_limit=None,
            signal_start_date=None,
            signal_end_date=None,
            factor_input_root=None,
            factor_input_required=False,
            moneyflow_input_root="data/processed/tushare_moneyflow_inputs",
            output_dir="data/reports/research_pipeline",
        )

        config = build_research_config(args)

        self.assertEqual(config.factor_name, "net_mf_amount_ratio")
        self.assertEqual(config.factor_source, "tushare_moneyflow")
        self.assertEqual(config.moneyflow_input_root, Path("data/processed/tushare_moneyflow_inputs"))

    def test_research_cli_config_builder_passes_etf_share_size_factor_source(self):
        args = SimpleNamespace(
            factor="share_change_1d",
            factor_source="etf_share_size",
            factor_windows="1",
            market="CN_ETF",
            start_date=None,
            end_date=None,
            forward_horizon=1,
            execution_lag=1,
            rebalance_interval=1,
            top_n=1,
            cost_bps=5.0,
            portfolio_scope=None,
            periods_per_year=None,
            benchmark_asset_id=None,
            cash_annual_return=0.0,
            regime_filter=False,
            regime_lookback=20,
            min_relative_return=None,
            max_drawdown_limit=None,
            signal_start_date=None,
            signal_end_date=None,
            factor_input_root="data/processed/tushare_etf_full",
            factor_input_required=True,
            moneyflow_input_root=None,
            output_dir="data/reports/research_pipeline",
        )

        config = build_research_config(args)

        self.assertEqual(config.factor_name, "share_change_1d")
        self.assertEqual(config.factor_source, "etf_share_size")
        self.assertEqual(config.factor_input_root, Path("data/processed/tushare_etf_full"))

    def test_research_cli_config_builder_passes_etf_moneyflow_basket_factor_source(self):
        args = SimpleNamespace(
            factor="etf_net_mf_amount_ratio",
            factor_source="etf_moneyflow_basket",
            factor_windows="1",
            market="CN_ETF",
            start_date=None,
            end_date=None,
            forward_horizon=1,
            execution_lag=1,
            rebalance_interval=1,
            top_n=1,
            cost_bps=5.0,
            portfolio_scope=None,
            periods_per_year=None,
            benchmark_asset_id=None,
            cash_annual_return=0.0,
            regime_filter=False,
            regime_lookback=20,
            min_relative_return=None,
            max_drawdown_limit=None,
            signal_start_date=None,
            signal_end_date=None,
            factor_input_root="data/processed/tushare_etf_baskets",
            factor_input_required=True,
            moneyflow_input_root="data/processed/tushare_moneyflow_inputs",
            output_dir="data/reports/research_pipeline",
        )

        config = build_research_config(args)

        self.assertEqual(config.factor_name, "etf_net_mf_amount_ratio")
        self.assertEqual(config.factor_source, "etf_moneyflow_basket")
        self.assertEqual(config.factor_input_root, Path("data/processed/tushare_etf_baskets"))
        self.assertEqual(config.moneyflow_input_root, Path("data/processed/tushare_moneyflow_inputs"))

    def test_pipeline_rejects_tushare_daily_basic_without_execution_lag(self):
        with tempfile.TemporaryDirectory() as tmp:
            bars = load_demo_market_bars()
            _write_daily_basic_factor_inputs(Path(tmp), bars)

            config = ResearchPipelineConfig(
                factor_name="pb_inverse",
                factor_source="tushare_daily_basic",
                factor_input_root=Path(tmp),
                market="CN",
                execution_lag=0,
                top_n=1,
            )

            with self.assertRaisesRegex(ValueError, "execution_lag"):
                run_research_pipeline(bars, config)

    def test_pipeline_runs_tushare_daily_basic_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            bars = load_demo_market_bars()
            _write_daily_basic_factor_inputs(Path(tmp), bars)

            result = run_research_pipeline(
                bars,
                ResearchPipelineConfig(
                    factor_name="pb_inverse",
                    factor_source="tushare_daily_basic",
                    factor_input_root=Path(tmp),
                    factor_input_required=True,
                    market="CN",
                    top_n=1,
                    execution_lag=1,
                ),
            )

            self.assertEqual(result["request"]["factor_source"], "tushare_daily_basic")
            self.assertEqual(result["request"]["factor_input_root"], str(Path(tmp)))
            self.assertGreater(result["artifact_rows"]["factor_inputs"], 0)
            self.assertGreater(result["artifact_rows"]["factors"], 0)
            self.assertGreater(result["artifact_rows"]["ic"], 0)

    def test_pipeline_rejects_tushare_moneyflow_without_execution_lag(self):
        with tempfile.TemporaryDirectory() as tmp:
            bars = load_demo_market_bars()
            _write_moneyflow_inputs(Path(tmp), bars)

            config = ResearchPipelineConfig(
                factor_name="net_mf_amount_ratio",
                factor_source="tushare_moneyflow",
                moneyflow_input_root=Path(tmp),
                market="CN",
                execution_lag=0,
                top_n=1,
            )

            with self.assertRaisesRegex(ValueError, "execution_lag"):
                run_research_pipeline(bars, config)

    def test_pipeline_runs_tushare_moneyflow_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            bars = load_demo_market_bars()
            _write_moneyflow_inputs(Path(tmp), bars)

            result = run_research_pipeline(
                bars,
                ResearchPipelineConfig(
                    factor_name="net_mf_amount_ratio",
                    factor_source="tushare_moneyflow",
                    moneyflow_input_root=Path(tmp),
                    market="CN",
                    top_n=1,
                    execution_lag=1,
                ),
            )

            self.assertEqual(result["request"]["factor_source"], "tushare_moneyflow")
            self.assertEqual(result["request"]["moneyflow_input_root"], str(Path(tmp)))
            self.assertGreater(result["artifact_rows"]["factor_inputs"], 0)
            self.assertGreater(result["artifact_rows"]["factors"], 0)
            self.assertGreater(result["artifact_rows"]["ic"], 0)

    def test_pipeline_rejects_etf_share_size_without_execution_lag(self):
        with tempfile.TemporaryDirectory() as tmp:
            bars = load_demo_market_bars()
            _write_etf_share_size_inputs(Path(tmp), bars)

            config = ResearchPipelineConfig(
                factor_name="share_change_1d",
                factor_source="etf_share_size",
                factor_input_root=Path(tmp),
                market="CN_ETF",
                execution_lag=0,
                top_n=1,
            )

            with self.assertRaisesRegex(ValueError, "execution_lag"):
                run_research_pipeline(bars, config)

    def test_pipeline_runs_etf_share_size_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            bars = load_demo_market_bars()
            _write_etf_share_size_inputs(Path(tmp), bars)

            result = run_research_pipeline(
                bars,
                ResearchPipelineConfig(
                    factor_name="share_change_1d",
                    factor_source="etf_share_size",
                    factor_input_root=Path(tmp),
                    factor_input_required=True,
                    market="CN_ETF",
                    top_n=1,
                    execution_lag=1,
                ),
            )

            self.assertEqual(result["request"]["factor_source"], "etf_share_size")
            self.assertEqual(result["request"]["factor_input_root"], str(Path(tmp)))
            self.assertGreater(result["artifact_rows"]["factor_inputs"], 0)
            self.assertGreater(result["artifact_rows"]["factors"], 0)
            self.assertGreater(result["artifact_rows"]["ic"], 0)

    def test_pipeline_rejects_etf_moneyflow_basket_without_execution_lag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = load_demo_market_bars()
            _write_moneyflow_inputs(root, bars)
            _write_etf_moneyflow_baskets(root, bars)

            config = ResearchPipelineConfig(
                factor_name="etf_net_mf_amount_ratio",
                factor_source="etf_moneyflow_basket",
                factor_input_root=root,
                moneyflow_input_root=root,
                market="CN_ETF",
                execution_lag=0,
                top_n=1,
            )

            with self.assertRaisesRegex(ValueError, "execution_lag"):
                run_research_pipeline(bars, config)

    def test_pipeline_runs_etf_moneyflow_basket_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = load_demo_market_bars()
            _write_moneyflow_inputs(root, bars)
            _write_etf_moneyflow_baskets(root, bars)

            result = run_research_pipeline(
                bars,
                ResearchPipelineConfig(
                    factor_name="etf_net_mf_amount_ratio",
                    factor_source="etf_moneyflow_basket",
                    factor_input_root=root,
                    factor_input_required=True,
                    moneyflow_input_root=root,
                    market="CN_ETF",
                    top_n=1,
                    execution_lag=1,
                ),
            )

            self.assertEqual(result["request"]["factor_source"], "etf_moneyflow_basket")
            self.assertEqual(result["request"]["factor_input_root"], str(root))
            self.assertEqual(result["request"]["moneyflow_input_root"], str(root))
            self.assertGreater(result["artifact_rows"]["factor_inputs"], 0)
            self.assertGreater(result["artifact_rows"]["factors"], 0)
            self.assertGreater(result["artifact_rows"]["ic"], 0)

    def test_pipeline_runs_moneyflow_technical_combo_factor_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            bars = load_demo_market_bars()
            _write_moneyflow_inputs(Path(tmp), bars)

            result = run_research_pipeline(
                bars,
                ResearchPipelineConfig(
                    factor_name="mf_low_plus_reversal_5",
                    factor_source="moneyflow_technical_combo",
                    factor_windows=(5, 10, 20),
                    moneyflow_input_root=Path(tmp),
                    market="CN",
                    top_n=1,
                    execution_lag=1,
                ),
            )

            self.assertEqual(result["request"]["factor_source"], "moneyflow_technical_combo")
            self.assertEqual(result["request"]["moneyflow_input_root"], str(Path(tmp)))
            self.assertGreater(result["artifact_rows"]["factor_inputs"], 0)
            self.assertGreater(result["artifact_rows"]["factors"], 0)
            self.assertGreater(result["artifact_rows"]["ic"], 0)

    def test_pipeline_computes_only_requested_moneyflow_technical_combo_factor(self):
        with tempfile.TemporaryDirectory() as tmp:
            bars = load_demo_market_bars()
            _write_moneyflow_inputs(Path(tmp), bars)

            with patch("quant_robot.research.pipeline.compute_moneyflow_technical_combo_factors") as combo_builder:
                combo_builder.return_value = pd.DataFrame(
                    {
                        "date": [],
                        "asset_id": [],
                        "market": [],
                        "factor_name": [],
                        "factor_value": [],
                        "lookback_window": [],
                    }
                )
                run_research_pipeline(
                    bars,
                    ResearchPipelineConfig(
                        factor_name="mf_low_plus_reversal_5",
                        factor_source="moneyflow_technical_combo",
                        factor_windows=(5, 10, 20),
                        moneyflow_input_root=Path(tmp),
                        market="CN",
                        top_n=1,
                        execution_lag=1,
                    ),
                )

            self.assertEqual(combo_builder.call_args.kwargs["factor_names"], ("mf_low_plus_reversal_5",))

    def test_pipeline_precomputed_factors_skip_moneyflow_input_loading(self):
        bars = load_demo_market_bars()
        factors = compute_basic_factors(bars, windows=(2,))

        result = run_research_pipeline(
            bars,
            ResearchPipelineConfig(
                factor_name="momentum_2",
                factor_source="moneyflow_technical_combo",
                factor_windows=(2,),
                market="CN",
                top_n=1,
            ),
            precomputed_factors=factors,
        )

        self.assertEqual(result["request"]["factor_source"], "moneyflow_technical_combo")
        self.assertGreater(result["artifact_rows"]["trades"], 0)

    def test_pipeline_requires_factor_input_root_when_requested(self):
        with self.assertRaisesRegex(ValueError, "factor_input_root"):
            run_research_pipeline(
                load_demo_market_bars(),
                ResearchPipelineConfig(
                    factor_name="pb_inverse",
                    factor_source="tushare_daily_basic",
                    factor_input_required=True,
                    market="CN",
                ),
            )


def _falling_regime_bars() -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2024-01-01", periods=8).date
    paths = {
        "CN_ETF_XSHG_510300": [10.0, 9.8, 9.6, 9.4, 9.2, 9.0, 8.8, 8.6],
        "CN_ETF_XSHG_510500": [5.0, 5.1, 5.3, 5.5, 5.8, 6.0, 6.2, 6.4],
    }
    symbols = {
        "CN_ETF_XSHG_510300": "510300.SH",
        "CN_ETF_XSHG_510500": "510500.SH",
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


def _write_daily_basic_factor_inputs(root: Path, bars: pd.DataFrame) -> None:
    cn_bars = bars[bars["market"] == "CN"].copy()
    rows = []
    for index, row in cn_bars.reset_index(drop=True).iterrows():
        expensive = row["asset_id"].endswith("600519")
        pb = 8.0 if expensive else 1.5
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
                "pe_ttm": 20.0 if expensive else 8.0,
                "pb": pb,
                "ps_ttm": 6.0 if expensive else 2.0,
                "dv_ttm": 1.5 if expensive else 3.0,
                "total_mv": 300000.0 if expensive else 120000.0,
                "circ_mv": 200000.0 if expensive else 90000.0,
            }
        )
    frame = pd.DataFrame(rows)
    DatasetStore(root).write_frame(
        frame,
        "processed/factor_inputs",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


def _write_moneyflow_inputs(root: Path, bars: pd.DataFrame) -> None:
    cn_bars = bars[bars["market"] == "CN"].copy()
    rows = []
    for index, row in cn_bars.reset_index(drop=True).iterrows():
        strong = row["asset_id"].endswith("600519")
        scale = 1.0 + index * 0.01
        net = 200.0 if strong else 50.0
        rows.append(
            {
                "date": row["date"],
                "asset_id": row["asset_id"],
                "symbol": row["symbol"],
                "market": "CN",
                "source": "tushare_moneyflow",
                "buy_sm_amount": 100.0 * scale,
                "sell_sm_amount": 80.0 * scale,
                "buy_md_amount": 300.0 * scale,
                "sell_md_amount": 250.0 * scale,
                "buy_lg_amount": 500.0 * scale,
                "sell_lg_amount": 450.0 * scale,
                "buy_elg_amount": 700.0 * scale,
                "sell_elg_amount": 650.0 * scale,
                "net_mf_amount": net,
            }
        )
    frame = pd.DataFrame(rows)
    DatasetStore(root).write_frame(
        frame,
        "processed/moneyflow_inputs",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


def _write_etf_share_size_inputs(root: Path, bars: pd.DataFrame) -> None:
    etf_bars = bars[bars["market"] == "CN_ETF"].copy()
    rows = []
    for asset_index, (asset_id, group) in enumerate(etf_bars.groupby("asset_id", sort=True), start=1):
        symbol = group["symbol"].iloc[0]
        exchange = "SSE" if symbol.endswith(".SH") else "SZSE"
        for index, row in group.sort_values("date").reset_index(drop=True).iterrows():
            share_change = pd.NA if index == 0 else 0.01 * asset_index
            size_change = pd.NA if index == 0 else 0.02 * asset_index
            rows.append(
                {
                    "date": row["date"],
                    "asset_id": asset_id,
                    "symbol": symbol,
                    "market": "CN_ETF",
                    "source": "tushare_etf_share_size",
                    "name": f"{symbol} ETF",
                    "exchange": exchange,
                    "total_share": 10_000_000.0 + index * 100_000.0 * asset_index,
                    "total_size": 40_000_000.0 + index * 800_000.0 * asset_index,
                    "nav": row["close"],
                    "close": row["close"] * (1.0 + 0.001 * asset_index),
                    "share_change_1d": share_change,
                    "size_change_1d": size_change,
                    "nav_premium_discount": 0.001 * asset_index,
                }
            )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/etf_share_size",
        {"frequency": "1d", "market": "CN_ETF", "year": "2024"},
    )


def _write_etf_moneyflow_baskets(root: Path, bars: pd.DataFrame) -> None:
    cn_assets = bars[bars["market"] == "CN"].drop_duplicates("asset_id").sort_values("asset_id")
    etf_assets = bars[bars["market"] == "CN_ETF"].drop_duplicates("asset_id").sort_values("asset_id")
    rows = []
    for etf_index, etf in enumerate(etf_assets.itertuples(index=False), start=1):
        for stock_index, stock in enumerate(cn_assets.itertuples(index=False), start=1):
            rows.append(
                {
                    "etf_asset_id": etf.asset_id,
                    "etf_symbol": etf.symbol,
                    "stock_asset_id": stock.asset_id,
                    "stock_symbol": stock.symbol,
                    "weight": stock_index / len(cn_assets),
                    "known_date": pd.Timestamp("2024-01-01").date(),
                    "end_date": pd.NaT,
                    "source": f"fixture_basket_{etf_index}",
                }
            )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "metadata/etf_moneyflow_baskets",
        {"market": "CN_ETF"},
    )


if __name__ == "__main__":
    unittest.main()
