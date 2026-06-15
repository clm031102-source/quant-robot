import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.research.pipeline import ResearchPipelineConfig, run_research_pipeline
from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.storage.processed_bars import load_processed_bars
from scripts.run_research_pipeline import load_research_bars


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
            self.assertGreater(result["artifact_rows"]["trades"], 0)
            self.assertTrue((Path(tmp) / "metrics.json").exists())
            self.assertTrue((Path(tmp) / "factor_summary.json").exists())
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


if __name__ == "__main__":
    unittest.main()
