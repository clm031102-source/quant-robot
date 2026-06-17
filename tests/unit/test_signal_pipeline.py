import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.signals.pipeline import SignalPipelineConfig, generate_signal_snapshot, write_signal_snapshot
from quant_robot.storage.dataset_store import DatasetStore


class SignalPipelineTests(unittest.TestCase):
    def test_signal_snapshot_uses_latest_signal_date_without_future_bars(self):
        config = SignalPipelineConfig(
            market="CN",
            factor_name="momentum_2",
            factor_windows=(2,),
            top_n=1,
            as_of_date="2024-01-08",
        )

        result = generate_signal_snapshot(load_demo_market_bars(), config)

        self.assertEqual(result["as_of_date"], "2024-01-08")
        self.assertEqual(result["signal_date"], "2024-01-08")
        self.assertEqual(result["request"]["portfolio_scope"], "market")
        self.assertEqual({row["market"] for row in result["targets"]}, {"CN"})
        self.assertTrue(all(pd.to_datetime(row["signal_date"]).date() <= pd.Timestamp("2024-01-08").date() for row in result["targets"]))

    def test_all_market_snapshot_defaults_to_global_portfolio_scope(self):
        config = SignalPipelineConfig(
            market="ALL",
            factor_name="momentum_2",
            factor_windows=(2,),
            top_n=2,
            as_of_date="2024-01-08",
        )

        result = generate_signal_snapshot(load_demo_market_bars(), config)

        self.assertEqual(result["request"]["portfolio_scope"], "global")
        self.assertAlmostEqual(sum(row["target_weight"] for row in result["targets"]), 1.0)
        self.assertAlmostEqual(result["cash_weight"], 0.0)

    def test_signal_snapshot_applies_risk_weight_caps(self):
        config = SignalPipelineConfig(
            market="ALL",
            factor_name="momentum_2",
            factor_windows=(2,),
            top_n=4,
            as_of_date="2024-01-08",
            max_asset_weight=0.25,
            max_market_weight=0.40,
            max_gross_exposure=0.80,
            min_cash_weight=0.10,
        )

        result = generate_signal_snapshot(load_demo_market_bars(), config)
        market_weights = {}
        for row in result["targets"]:
            self.assertLessEqual(row["target_weight"], 0.25)
            market_weights[row["market"]] = market_weights.get(row["market"], 0.0) + row["target_weight"]

        self.assertLessEqual(sum(row["target_weight"] for row in result["targets"]), 0.80)
        self.assertGreaterEqual(result["cash_weight"], 0.10)
        self.assertTrue(all(weight <= 0.40 for weight in market_weights.values()))

    def test_cn_etf_signal_snapshot_filters_targets_to_rotation_membership(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = load_demo_market_bars()
            membership = bars[bars["market"] == "CN_ETF"][["date", "asset_id", "market"]].copy()
            membership["symbol"] = membership["asset_id"].astype(str)
            membership["is_rotation_member"] = membership["asset_id"].eq("CN_ETF_XSHG_510300")
            DatasetStore(root).write_frame(
                membership,
                "metadata/cn_etf_rotation_membership",
                {"market": "CN_ETF"},
            )
            config = SignalPipelineConfig(
                market="CN_ETF",
                factor_name="momentum_2",
                factor_windows=(2,),
                top_n=4,
                as_of_date="2024-01-08",
                rotation_membership_root=root,
                rotation_membership_required=True,
            )

            result = generate_signal_snapshot(bars, config)

            self.assertEqual({row["asset_id"] for row in result["targets"]}, {"CN_ETF_XSHG_510300"})
            self.assertEqual(result["request"]["rotation_membership_root"], str(root))
            self.assertTrue(result["request"]["rotation_membership_required"])

    def test_signal_snapshot_writes_targets_and_manifest(self):
        config = SignalPipelineConfig(market="CN", factor_name="momentum_2", factor_windows=(2,), top_n=1)
        result = generate_signal_snapshot(load_demo_market_bars(), config)

        with tempfile.TemporaryDirectory() as tmp:
            write_signal_snapshot(result, Path(tmp))

            self.assertTrue((Path(tmp) / "targets.csv").exists())
            self.assertTrue((Path(tmp) / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
