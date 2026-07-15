import unittest

import pandas as pd

from quant_robot.data.gap_audit import build_data_quality_gap_audit


class DataQualityGapAuditTests(unittest.TestCase):
    def test_gap_audit_without_explicit_calendar_is_blocked(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["ETF_A", "ETF_A"],
                "market": ["CN_ETF", "CN_ETF"],
                "date": ["2024-01-02", "2024-01-03"],
                "volume": [100, 120],
            }
        )

        audit = build_data_quality_gap_audit(bars)

        self.assertEqual(audit["status"], "blocked")
        self.assertFalse(audit["decision"]["gap_audit_cleared"])
        self.assertIn("explicit_trading_calendar_required", audit["decision"]["blockers"])
        self.assertEqual(audit["summary"]["calendar_source"], "observed_dates_diagnostic_only")

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
        self.assertEqual(audit["summary"]["missing_date_examples"], 1)
        self.assertFalse(audit["summary"]["missing_date_examples_truncated"])
        self.assertEqual(audit["status"], "blocked")
        self.assertEqual(audit["missing_dates"][0]["asset_id"], "ETF_A")
        self.assertEqual(audit["missing_dates"][0]["missing_date"], "2024-01-03")
        self.assertEqual(audit["coverage_by_asset"][0]["asset_id"], "ETF_A")
        self.assertTrue(any("run_data_quality_audit.py" in action["command"] for action in audit["repair_actions"]))
        self.assertIn("Research only", audit["safety"])
        self.assertIn("ETF_A", audit["markdown"])

    def test_gap_audit_reports_whole_market_missing_sessions(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["ETF_A", "ETF_A", "ETF_B", "ETF_B"],
                "market": ["CN_ETF"] * 4,
                "date": ["2024-01-02", "2024-01-04", "2024-01-02", "2024-01-04"],
                "volume": [100, 120, 200, 220],
            }
        )

        audit = build_data_quality_gap_audit(
            bars,
            expected_dates=["2024-01-02", "2024-01-03", "2024-01-04"],
        )

        self.assertEqual(audit["summary"]["whole_market_missing_dates"], 1)
        self.assertEqual(
            audit["whole_market_missing_dates"],
            [{"market": "CN_ETF", "missing_date": "2024-01-03"}],
        )
        self.assertIn("whole_market_sessions_missing", audit["decision"]["blockers"])

    def test_gap_audit_keeps_total_missing_count_when_examples_are_truncated(self):
        expected_dates = pd.date_range("2024-01-01", periods=12).date.tolist()
        bars = pd.DataFrame(
            {
                "asset_id": ["ETF_A", "ETF_A"],
                "market": ["CN_ETF", "CN_ETF"],
                "date": [expected_dates[0], expected_dates[-1]],
                "volume": [100, 120],
            }
        )

        audit = build_data_quality_gap_audit(
            bars,
            expected_dates=expected_dates,
            max_examples_per_asset=2,
        )

        self.assertEqual(audit["summary"]["missing_date_rows"], 10)
        self.assertEqual(audit["summary"]["missing_date_examples"], 2)
        self.assertTrue(audit["summary"]["missing_date_examples_truncated"])
        self.assertEqual(len(audit["missing_dates"]), 2)

    def test_gap_audit_clears_only_with_complete_explicit_calendar(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["ETF_A", "ETF_A"],
                "market": ["CN_ETF", "CN_ETF"],
                "date": ["2024-01-02", "2024-01-03"],
                "volume": [100, 120],
            }
        )

        audit = build_data_quality_gap_audit(
            bars,
            expected_dates=["2024-01-02", "2024-01-03"],
        )

        self.assertEqual(audit["status"], "cleared")
        self.assertTrue(audit["decision"]["gap_audit_cleared"])
        self.assertEqual(audit["decision"]["blockers"], [])

    def test_stock_review_policy_keeps_asset_gaps_out_of_hard_blockers(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["CN_A", "CN_A", "CN_B", "CN_B", "CN_B"],
                "market": ["CN"] * 5,
                "date": ["2024-01-02", "2024-01-04", "2024-01-02", "2024-01-03", "2024-01-04"],
                "volume": [100, 120, 200, 210, 220],
            }
        )

        audit = build_data_quality_gap_audit(
            bars,
            expected_dates=["2024-01-02", "2024-01-03", "2024-01-04"],
            asset_gap_policy="review",
        )

        self.assertEqual(audit["status"], "review_required")
        self.assertFalse(audit["decision"]["gap_audit_cleared"])
        self.assertEqual(audit["decision"]["blockers"], [])
        self.assertEqual(audit["decision"]["review_reasons"], ["asset_sessions_require_suspension_review"])
        self.assertEqual(audit["summary"]["asset_gap_policy"], "review")

    def test_stock_review_policy_still_blocks_whole_market_session_loss(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["CN_A", "CN_A", "CN_B", "CN_B"],
                "market": ["CN"] * 4,
                "date": ["2024-01-02", "2024-01-04", "2024-01-02", "2024-01-04"],
                "volume": [100, 120, 200, 220],
            }
        )

        audit = build_data_quality_gap_audit(
            bars,
            expected_dates=["2024-01-02", "2024-01-03", "2024-01-04"],
            asset_gap_policy="review",
        )

        self.assertEqual(audit["status"], "blocked")
        self.assertIn("whole_market_sessions_missing", audit["decision"]["blockers"])

    def test_gap_audit_rejects_unknown_asset_gap_policy(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["CN_A"],
                "market": ["CN"],
                "date": ["2024-01-02"],
                "volume": [100],
            }
        )

        with self.assertRaisesRegex(ValueError, "asset_gap_policy"):
            build_data_quality_gap_audit(
                bars,
                expected_dates=["2024-01-02"],
                asset_gap_policy="ignore",
            )

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
