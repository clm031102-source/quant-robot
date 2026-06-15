import unittest

import pandas as pd

from quant_robot.data.gap_audit import build_data_quality_gap_audit


class DataQualityGapAuditTests(unittest.TestCase):
    def test_gap_audit_lists_missing_dates_by_asset_and_repair_actions(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["ETF_A", "ETF_A", "ETF_B", "ETF_B", "ETF_B"],
                "symbol": ["510300.SH", "510300.SH", "159915.SZ", "159915.SZ", "159915.SZ"],
                "market": ["CN_ETF", "CN_ETF", "CN_ETF", "CN_ETF", "CN_ETF"],
                "date": [
                    "2024-01-02",
                    "2024-01-04",
                    "2024-01-02",
                    "2024-01-03",
                    "2024-01-04",
                ],
                "volume": [100, 120, 200, 210, 220],
            }
        )

        audit = build_data_quality_gap_audit(
            bars,
            expected_dates=["2024-01-02", "2024-01-03", "2024-01-04"],
            source_root="data/processed/etf_csv",
        )

        self.assertEqual(audit["stage"], "phase_3_1_data_quality_gap_audit")
        self.assertEqual(audit["summary"]["missing_date_rows"], 1)
        self.assertEqual(audit["summary"]["assets_with_gaps"], 1)
        self.assertEqual(audit["missing_dates"][0]["asset_id"], "ETF_A")
        self.assertEqual(audit["missing_dates"][0]["missing_date"], "2024-01-03")
        self.assertEqual(audit["coverage_by_asset"][0]["asset_id"], "ETF_A")
        self.assertTrue(any("run_data_quality_audit.py" in action["command"] for action in audit["repair_actions"]))
        self.assertIn("Research only", audit["safety"])
        self.assertIn("ETF_A", audit["markdown"])

    def test_repair_actions_use_audited_market(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["CN_A", "CN_A"],
                "symbol": ["000001.SZ", "000001.SZ"],
                "market": ["CN", "CN"],
                "date": ["2024-01-02", "2024-01-04"],
                "volume": [100, 120],
            }
        )

        audit = build_data_quality_gap_audit(
            bars,
            expected_dates=["2024-01-02", "2024-01-03", "2024-01-04"],
            source_root="data/processed/tushare_alpha_factory_gate",
        )

        inspect_action = next(action for action in audit["repair_actions"] if action["action"] == "inspect_missing_dates")
        self.assertIn("--market CN ", inspect_action["command"])

        refresh_action = next(action for action in audit["repair_actions"] if action["action"] == "refresh_tushare_data")
        self.assertIn("--source tushare", refresh_action["command"])
        self.assertIn("--market CN ", refresh_action["command"])


if __name__ == "__main__":
    unittest.main()
