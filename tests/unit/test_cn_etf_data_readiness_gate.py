import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.ops.cn_etf_data_readiness import build_cn_etf_data_readiness_gate
from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_cn_etf_data_readiness_gate import DEFAULT_DATA_ROOT, run_cn_etf_data_readiness_gate
from scripts.run_tushare_cn_etf_sync import run_tushare_cn_etf_sync_cli


class CnEtfDataReadinessGateTests(unittest.TestCase):
    def test_default_data_root_matches_tushare_full_history_sync_root(self):
        self.assertEqual(DEFAULT_DATA_ROOT, Path("data/processed/tushare_etf_full"))

    def test_gate_passes_after_fixture_sync_with_membership_and_auxiliary_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sync_pack = run_tushare_cn_etf_sync_cli(
                source="tushare-fixture",
                start_date="2024-01-02",
                end_date="2024-01-05",
                output_dir=root / "processed",
                report_dir=root / "sync_report",
                execute=True,
                min_rotation_history_rows=2,
                min_rotation_median_amount=100000.0,
            )

            pack = build_cn_etf_data_readiness_gate(
                data_root=root / "processed",
                sync_report_dir=root / "sync_report",
            )

            self.assertEqual(sync_pack["status"], "completed")
            self.assertEqual(pack["status"], "ready")
            self.assertEqual(pack["blockers"], [])
            self.assertEqual(pack["primary_market"], "CN_ETF")
            self.assertGreater(pack["bars"]["rows"], 0)
            self.assertGreater(pack["rotation_membership"]["member_rows"], 0)
            self.assertEqual(pack["sync_pack"]["status"], "completed")
            self.assertEqual(pack["auxiliary_feature_policy"]["cn_stock_moneyflow"], "auxiliary_only")
            self.assertFalse(pack["live_boundary_allowed"])

    def test_gate_blocks_when_rotation_membership_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = load_demo_market_bars()
            cn_etf = bars[bars["market"] == "CN_ETF"].reset_index(drop=True)
            DatasetStore(root / "processed").write_frame(
                cn_etf,
                "processed/bars",
                {"frequency": "1d", "market": "CN_ETF", "year": "2024"},
            )

            pack = build_cn_etf_data_readiness_gate(data_root=root / "processed")

            self.assertEqual(pack["status"], "blocked")
            self.assertIn("missing_rotation_membership", pack["blockers"])
            self.assertGreater(pack["bars"]["rows"], 0)
            self.assertEqual(pack["rotation_membership"]["rows"], 0)

    def test_script_writes_readiness_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_tushare_cn_etf_sync_cli(
                source="tushare-fixture",
                start_date="2024-01-02",
                end_date="2024-01-05",
                output_dir=root / "processed",
                report_dir=root / "sync_report",
                execute=True,
                min_rotation_history_rows=2,
            )

            pack = run_cn_etf_data_readiness_gate(
                data_root=root / "processed",
                sync_report_dir=root / "sync_report",
                output_dir=root / "readiness",
            )

            self.assertEqual(pack["status"], "ready")
            self.assertTrue((root / "readiness" / "cn_etf_data_readiness_gate.json").exists())
            self.assertTrue((root / "readiness" / "cn_etf_data_readiness_gate.md").exists())


if __name__ == "__main__":
    unittest.main()
