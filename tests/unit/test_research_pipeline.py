import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.research.pipeline import ResearchPipelineConfig, run_research_pipeline
from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.storage.processed_bars import load_processed_bars


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


if __name__ == "__main__":
    unittest.main()
