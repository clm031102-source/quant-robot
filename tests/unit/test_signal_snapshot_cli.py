import tempfile
import unittest
from pathlib import Path

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_signal_snapshot import run_signal_snapshot


class SignalSnapshotCliTests(unittest.TestCase):
    def test_run_signal_snapshot_writes_research_only_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_signal_snapshot(
                source="fixture",
                market="CN",
                factor_name="momentum_2",
                factor_windows=(2,),
                top_n=1,
                output_dir=Path(tmp),
            )

            self.assertEqual(result["data_mode"], "fixture")
            self.assertFalse(result["rebalance_plan"][0]["executable"])
            self.assertTrue((Path(tmp) / "targets.csv").exists())
            self.assertTrue((Path(tmp) / "rebalance_plan.csv").exists())
            self.assertTrue((Path(tmp) / "manifest.json").exists())

    def test_run_signal_snapshot_loads_all_processed_markets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "store"
            bars = load_demo_market_bars()
            for market, group in bars.groupby("market"):
                DatasetStore(root).write_frame(
                    group.reset_index(drop=True),
                    "processed/bars",
                    {"frequency": "1d", "market": market, "year": "2024"},
                )

            result = run_signal_snapshot(
                source="processed-bars",
                data_root=root,
                market="ALL",
                factor_name="momentum_2",
                factor_windows=(2,),
                top_n=2,
            )

            self.assertEqual(result["request"]["portfolio_scope"], "global")
            self.assertGreaterEqual(len({row["market"] for row in result["targets"]}), 1)

    def test_processed_cn_etf_snapshot_auto_uses_rotation_membership(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "store"
            bars = load_demo_market_bars()
            cn_etf = bars[bars["market"] == "CN_ETF"].reset_index(drop=True)
            DatasetStore(root).write_frame(
                cn_etf,
                "processed/bars",
                {"frequency": "1d", "market": "CN_ETF", "year": "2024"},
            )
            membership = cn_etf[["date", "asset_id", "market"]].copy()
            membership["symbol"] = membership["asset_id"].astype(str)
            membership["is_rotation_member"] = membership["asset_id"].eq("CN_ETF_XSHG_510300")
            DatasetStore(root).write_frame(
                membership,
                "metadata/cn_etf_rotation_membership",
                {"market": "CN_ETF"},
            )

            result = run_signal_snapshot(
                source="processed-bars",
                data_root=root,
                market="CN_ETF",
                factor_name="momentum_2",
                factor_windows=(2,),
                top_n=4,
                as_of_date="2024-01-08",
            )

            self.assertEqual({row["asset_id"] for row in result["targets"]}, {"CN_ETF_XSHG_510300"})
            self.assertEqual(result["request"]["rotation_membership_root"], str(root))
            self.assertTrue(result["request"]["rotation_membership_required"])


if __name__ == "__main__":
    unittest.main()
