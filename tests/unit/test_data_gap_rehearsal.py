import unittest

from quant_robot.ops.data_gap_rehearsal import build_data_gap_rehearsal


class DataGapRehearsalTests(unittest.TestCase):
    def test_rehearsal_builds_sample_resolution_and_before_after_counts(self):
        audit = {
            "stage": "phase_3_1_data_quality_gap_audit",
            "missing_dates": [
                {"asset_id": "ETF_A", "symbol": "510300.SH", "missing_date": "2024-01-03"},
                {"asset_id": "ETF_B", "symbol": "159915.SZ", "missing_date": "2024-01-04"},
                {"asset_id": "ETF_C", "symbol": "512100.SH", "missing_date": "2024-01-05"},
            ],
        }

        rehearsal = build_data_gap_rehearsal(audit, sample_size=2)

        self.assertEqual(rehearsal["stage"], "phase_4_6_data_gap_resolution_rehearsal")
        self.assertEqual(rehearsal["summary"]["source_gap_rows"], 3)
        self.assertEqual(rehearsal["summary"]["sample_resolution_rows"], 2)
        self.assertEqual(rehearsal["summary"]["source_blocking_gap_rows"], 3)
        self.assertEqual(rehearsal["summary"]["rehearsed_blocking_gap_rows"], 1)
        self.assertEqual(rehearsal["summary"]["blocker_delta"], 2)
        self.assertTrue(rehearsal["summary"]["blocks_api_boundary_after_rehearsal"])
        self.assertEqual(rehearsal["sample_resolution_rows"][0]["resolution_status"], "accepted_non_trading_day")
        self.assertEqual(rehearsal["sample_resolution_rows"][0]["reviewed_by"], "rehearsal")
        self.assertIn("Rehearsal only", rehearsal["sample_resolution_rows"][0]["evidence_note"])
        self.assertEqual(rehearsal["rehearsed_ledger_summary"]["accepted_non_trading_day"], 2)
        self.assertEqual(rehearsal["readiness_projection"]["status"], "block")
        self.assertIn("No broker", rehearsal["safety"])
        self.assertIn("Before", rehearsal["markdown"])

    def test_rehearsal_uses_current_nonblocking_ledger_as_baseline(self):
        audit = {
            "stage": "phase_3_1_data_quality_gap_audit",
            "missing_dates": [
                {"asset_id": "ETF_A", "symbol": "510300.SH", "missing_date": "2024-01-03"},
                {"asset_id": "ETF_B", "symbol": "159915.SZ", "missing_date": "2024-01-04"},
            ],
        }
        current_ledger = {
            "stage": "phase_4_2_data_gap_resolution_ledger",
            "summary": {"gap_rows": 2, "blocking_gap_rows": 0, "blocks_api_boundary": False, "needs_review": 0},
            "ledger_rows": [
                {"gap_id": "DG-ETF_A-20240103", "resolution_status": "accepted_non_trading_day", "blocks_api_boundary": False},
                {"gap_id": "DG-ETF_B-20240104", "resolution_status": "accepted_suspension_or_no_trade", "blocks_api_boundary": False},
            ],
        }

        rehearsal = build_data_gap_rehearsal(audit, sample_size=2, baseline_ledger=current_ledger)

        self.assertEqual(rehearsal["summary"]["source_gap_rows"], 2)
        self.assertEqual(rehearsal["summary"]["source_blocking_gap_rows"], 0)
        self.assertEqual(rehearsal["summary"]["sample_resolution_rows"], 0)
        self.assertEqual(rehearsal["summary"]["rehearsed_blocking_gap_rows"], 0)
        self.assertFalse(rehearsal["summary"]["blocks_api_boundary_after_rehearsal"])
        self.assertEqual(rehearsal["readiness_projection"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
