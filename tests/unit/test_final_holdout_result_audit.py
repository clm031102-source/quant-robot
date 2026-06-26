import unittest

from quant_robot.ops.final_holdout_result_audit import build_final_holdout_result_audit


class FinalHoldoutResultAuditTests(unittest.TestCase):
    def test_blocks_aggregate_accepted_case_when_holdout_fold_rejected(self) -> None:
        report = {
            "holdout_policy": {
                "final_holdout_included": True,
                "final_holdout_start": "2026-01-01",
            },
            "leaderboard": [
                {
                    "case_id": "case_a",
                    "validation_status": "accepted",
                    "mean_test_overlap_autocorr_adjusted_sharpe": 1.0,
                }
            ],
            "folds": [
                {
                    "case_id": "case_a",
                    "fold": 4,
                    "test_start_date": "2025-12-23",
                    "test_end_date": "2026-05-28",
                    "fold_validation_status": "rejected",
                    "fold_validation_blockers": "test_total_return_below_minimum;extreme_trade_return_present",
                    "test_total_return": -0.01,
                    "test_overlap_autocorr_adjusted_sharpe": -2.0,
                    "extreme_trade_return_count": 1,
                }
            ],
        }

        audit = build_final_holdout_result_audit(report)

        self.assertEqual(audit["summary"]["aggregate_accepted_cases"], 1)
        self.assertEqual(audit["summary"]["holdout_passed_cases"], 0)
        self.assertFalse(audit["decision"]["paper_gate_allowed"])
        self.assertIn("no_case_passed_final_holdout_fold", audit["decision"]["blockers"])
        self.assertEqual(audit["case_results"][0]["holdout_status"], "rejected")

    def test_allows_paper_gate_when_aggregate_and_holdout_pass(self) -> None:
        report = {
            "holdout_policy": {
                "final_holdout_included": True,
                "final_holdout_start": "2026-01-01",
            },
            "leaderboard": [
                {
                    "case_id": "case_a",
                    "validation_status": "accepted",
                    "mean_test_overlap_autocorr_adjusted_sharpe": 1.1,
                }
            ],
            "folds": [
                {
                    "case_id": "case_a",
                    "fold": 4,
                    "test_start_date": "2026-01-05",
                    "test_end_date": "2026-05-28",
                    "fold_validation_status": "accepted",
                    "fold_validation_blockers": "",
                    "test_total_return": 0.02,
                    "test_overlap_autocorr_adjusted_sharpe": 1.2,
                    "extreme_trade_return_count": 0,
                }
            ],
        }

        audit = build_final_holdout_result_audit(report)

        self.assertEqual(audit["summary"]["holdout_passed_cases"], 1)
        self.assertTrue(audit["decision"]["paper_gate_allowed"])
        self.assertEqual(audit["decision"]["blockers"], [])


if __name__ == "__main__":
    unittest.main()
