import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.lpr_macro_regime_walk_forward_rejection_rotation_gate import (
    summarize_lpr_macro_regime_walk_forward_rejection_rotation_gate,
    write_lpr_macro_regime_walk_forward_rejection_rotation_gate,
)


ANOMALY = "public_anomaly_residual_equal_weight_20_industry_size_liquidity_vol_residual"
WILLIAMS = "williams_range_failure_reversal_14_20_industry_size_liquidity_vol_residual"


class LPRMacroRegimeWalkForwardRejectionRotationGateTests(unittest.TestCase):
    def test_clears_rotation_after_clean_lpr_walk_forward_rejection(self) -> None:
        result = summarize_lpr_macro_regime_walk_forward_rejection_rotation_gate(_rejected_validation())

        self.assertEqual(result["stage"], "lpr_macro_regime_walk_forward_rejection_rotation_gate")
        self.assertEqual(result["status"], "cleared")
        self.assertEqual(result["summary"]["rejected_candidates"], 2)
        self.assertEqual(result["summary"]["accepted_candidates"], 0)
        self.assertEqual(result["failure_diagnostics"]["common_failed_test_folds"], [1])
        self.assertTrue(result["failure_diagnostics"]["capacity_not_blocker"])
        self.assertTrue(result["failure_diagnostics"]["exposure_challenge_not_blocker"])
        self.assertTrue(result["decision"]["rotation_source_gate_allowed_next"])
        self.assertFalse(result["decision"]["same_lpr_candidate_retry_allowed"])
        self.assertFalse(result["decision"]["statistical_reality_check_allowed_next"])
        self.assertFalse(result["rotation_policy"]["rerun_same_lpr_gap_widening_candidates_allowed"])
        self.assertFalse(result["rotation_policy"]["parameter_tuning_allowed"])
        self.assertFalse(result["rotation_policy"]["cost_threshold_relaxation_allowed"])
        self.assertFalse(result["rotation_policy"]["fold_threshold_relaxation_allowed"])
        self.assertEqual(
            result["rotation_policy"]["lpr_gap_widening_residual_path_status"],
            "rejected_pending_new_hypothesis",
        )
        self.assertEqual(
            result["rotation_policy"]["next_direction"],
            "rotate_to_non_lpr_orthogonal_family_source_gate",
        )
        self.assertEqual({row["retry_status"] for row in result["candidate_rotation_table"]}, {"retired_pending_new_hypothesis"})
        self.assertTrue(all(not row["same_candidate_retry_allowed"] for row in result["candidate_rotation_table"]))

    def test_blocks_rotation_when_validation_has_accepted_candidate(self) -> None:
        validation = _rejected_validation()
        validation["status"] = "accepted"
        validation["summary"]["accepted_candidates"] = 1
        validation["summary"]["rejected_candidates"] = 1
        validation["decision"]["statistical_reality_check_allowed_next"] = True
        validation["candidate_results"][0]["validation_status"] = "accepted"
        validation["candidate_results"][0]["rejection_reasons"] = []

        result = summarize_lpr_macro_regime_walk_forward_rejection_rotation_gate(validation)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("walk_forward_validation_not_rejected", result["decision"]["blockers"])
        self.assertIn("accepted_lpr_candidates_present", result["decision"]["blockers"])
        self.assertFalse(result["decision"]["rotation_source_gate_allowed_next"])
        self.assertFalse(result["rotation_policy"]["rerun_same_lpr_gap_widening_candidates_allowed"])
        self.assertFalse(result["rotation_policy"]["parameter_tuning_allowed"])

    def test_write_outputs(self) -> None:
        result = summarize_lpr_macro_regime_walk_forward_rejection_rotation_gate(_rejected_validation())

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_lpr_macro_regime_walk_forward_rejection_rotation_gate(output, result)

            self.assertTrue((output / "lpr_macro_regime_walk_forward_rejection_rotation_gate.json").exists())
            self.assertTrue((output / "lpr_macro_regime_walk_forward_rejection_rotation_gate.md").exists())
            self.assertTrue((output / "lpr_macro_regime_walk_forward_rejection_rotation_candidates.csv").exists())
            self.assertTrue((output / "lpr_macro_regime_walk_forward_rejection_rotation_reasons.csv").exists())


def _rejected_validation() -> dict:
    return {
        "stage": "lpr_macro_regime_state_conditioned_walk_forward_validation",
        "status": "rejected",
        "summary": {
            "frozen_candidates": 2,
            "accepted_candidates": 0,
            "rejected_candidates": 2,
            "fold_results": 4,
            "accepted_folds": 2,
            "regime_allowed_dates": 160,
            "regime_blocked_dates": 57,
        },
        "decision": {
            "blockers": ["no_accepted_lpr_walk_forward_candidates"],
            "statistical_reality_check_allowed_next": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
        },
        "candidate_results": [
            {
                "factor_name": WILLIAMS,
                "state": "gap_widening",
                "validation_status": "rejected",
                "accepted_folds": 1,
                "folds": 2,
                "mean_test_ic": 0.0164,
                "mean_test_long_short_net_mean": 0.00029,
                "mean_test_long_short_net_total": 0.0058,
                "mean_test_long_short_net_positive_rate": 0.50,
                "max_test_participation_rate": 0.0000605,
                "test_capacity_limited_dates": 0,
                "moderate_exposure_challenge_required": False,
                "moderate_exposure_challenge_passed": True,
                "exposure_challenge_mean_abs_corr": 0.2836,
                "exposure_challenge_max_abs_corr": 0.4047,
                "rejection_reasons": [
                    "test_mean_ic_non_positive",
                    "test_positive_ic_rate_below_threshold",
                    "test_long_short_net_mean_non_positive",
                    "test_long_short_net_total_non_positive",
                    "test_long_short_net_positive_rate_below_threshold",
                    "accepted_folds_below_threshold",
                ],
            },
            {
                "factor_name": ANOMALY,
                "state": "gap_widening",
                "validation_status": "rejected",
                "accepted_folds": 1,
                "folds": 2,
                "mean_test_ic": 0.0321,
                "mean_test_long_short_net_mean": -0.00071,
                "mean_test_long_short_net_total": -0.0143,
                "mean_test_long_short_net_positive_rate": 0.425,
                "max_test_participation_rate": 0.0000605,
                "test_capacity_limited_dates": 0,
                "moderate_exposure_challenge_required": True,
                "moderate_exposure_challenge_passed": True,
                "exposure_challenge_mean_abs_corr": 0.2742,
                "exposure_challenge_max_abs_corr": 0.67,
                "rejection_reasons": [
                    "test_long_short_net_mean_non_positive",
                    "test_long_short_net_total_non_positive",
                    "test_long_short_net_positive_rate_below_threshold",
                    "accepted_folds_below_threshold",
                ],
            },
        ],
        "fold_results": [
            _fold(ANOMALY, 1, "rejected", ["test_long_short_net_mean_non_positive"], cap_dates=0),
            _fold(ANOMALY, 2, "accepted", [], cap_dates=0),
            _fold(WILLIAMS, 1, "rejected", ["test_mean_ic_non_positive", "test_long_short_net_mean_non_positive"], cap_dates=0),
            _fold(WILLIAMS, 2, "accepted", [], cap_dates=0),
        ],
        "portfolio_grid_policy": {"portfolio_grid_allowed": False, "parameter_expansion_allowed": False},
        "promotion_policy": {"promotion_allowed": False},
        "live_boundary_allowed": False,
        "safety": "research_to_paper_only_no_broker_no_live_orders",
    }


def _fold(factor_name: str, fold: int, status: str, reasons: list[str], *, cap_dates: int) -> dict:
    return {
        "factor_name": factor_name,
        "state": "gap_widening",
        "fold": fold,
        "fold_status": status,
        "test_capacity_limited_dates": cap_dates,
        "test_long_short_net_mean": -0.01 if reasons else 0.01,
        "fold_rejection_reasons": reasons,
    }


if __name__ == "__main__":
    unittest.main()
