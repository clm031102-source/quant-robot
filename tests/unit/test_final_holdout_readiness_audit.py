import unittest

from quant_robot.ops.final_holdout_readiness_audit import build_final_holdout_readiness_audit


class FinalHoldoutReadinessAuditTests(unittest.TestCase):
    def test_blocks_when_bars_cover_holdout_but_signals_do_not(self) -> None:
        report = {
            "stage": "candidate_walk_forward",
            "holdout_policy": {
                "final_holdout_included": True,
                "final_holdout_start": "2026-01-01",
            },
            "data_window": {
                "max_bar_date": "2026-06-15",
                "max_signal_date": "2025-12-23",
            },
            "summary": {"walk_forward_accepted_candidates": 6},
            "folds": [
                {"test_start_date": "2024-06-28", "test_end_date": "2024-11-26"},
                {"test_start_date": "2025-01-02", "test_end_date": "2025-06-24"},
            ],
            "promotion_policy": {"blockers": ["final_holdout_not_read"]},
        }

        audit = build_final_holdout_readiness_audit(report)

        self.assertFalse(audit["decision"]["final_holdout_actual_read"])
        self.assertTrue(audit["coverage"]["bars_cover_final_holdout"])
        self.assertFalse(audit["coverage"]["signals_cover_final_holdout"])
        self.assertEqual(audit["coverage"]["holdout_fold_count"], 0)
        self.assertIn("signals_do_not_cover_final_holdout", audit["decision"]["blockers"])
        self.assertEqual(audit["next_direction"], "refresh_factor_inputs_for_final_holdout")

    def test_passes_when_bars_signals_and_test_folds_cover_holdout(self) -> None:
        report = {
            "holdout_policy": {
                "final_holdout_included": True,
                "final_holdout_start": "2026-01-01",
            },
            "data_window": {
                "max_bar_date": "2026-06-15",
                "max_signal_date": "2026-05-29",
            },
            "summary": {"walk_forward_accepted_candidates": 1},
            "folds": [
                {"test_start_date": "2026-01-05", "test_end_date": "2026-03-31"},
            ],
            "promotion_policy": {"blockers": ["paper_gate_required_after_clean_walk_forward"]},
        }

        audit = build_final_holdout_readiness_audit(report)

        self.assertTrue(audit["decision"]["final_holdout_actual_read"])
        self.assertEqual(audit["decision"]["blockers"], [])
        self.assertEqual(audit["next_direction"], "run_paper_gate_or_holdout_result_review")


if __name__ == "__main__":
    unittest.main()
