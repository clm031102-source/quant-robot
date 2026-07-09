import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.cn_stock_non_lpr_orthogonal_source_gate import (
    build_cn_stock_non_lpr_orthogonal_source_gate,
    write_cn_stock_non_lpr_orthogonal_source_gate,
)


class CNStockNonLPROrthogonalSourceGateTests(unittest.TestCase):
    def test_selects_analyst_report_extension_after_lpr_rejection(self) -> None:
        result = build_cn_stock_non_lpr_orthogonal_source_gate(
            round738_rotation_gate=_round738_rotation_gate(),
            readiness_gate=_round729_readiness_gate(),
            analyst_prescreen=_round729_analyst_prescreen(),
        )

        self.assertEqual(result["stage"], "cn_stock_non_lpr_orthogonal_source_gate")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["decision"]["selected_source"], "analyst_report_revision")
        self.assertTrue(result["decision"]["source_gate_selected"])
        self.assertFalse(result["decision"]["source_gate_ready"])
        self.assertTrue(result["decision"]["local_cached_prescreen_allowed"])
        self.assertFalse(result["decision"]["full_factor_batch_allowed"])
        self.assertFalse(result["decision"]["provider_request_allowed"])
        self.assertIn("provider_quota_preflight_blocked", result["decision"]["blockers"])
        self.assertIn("analyst_year_coverage_below_gate", result["decision"]["blockers"])
        self.assertFalse(result["decision"]["portfolio_grid_allowed"])
        self.assertFalse(result["decision"]["promotion_allowed"])
        selected = next(row for row in result["source_rows"] if row["source_id"] == "analyst_report_revision")
        self.assertEqual(selected["selection_status"], "selected_blocked_waiting_for_quota_and_year_coverage")
        self.assertEqual(selected["research_lead_count"], 0)
        self.assertEqual(selected["year_coverage_pass_count"], 0)
        lpr = next(row for row in result["source_rows"] if row["source_id"] == "lpr_gap_widening_residual")
        self.assertEqual(lpr["selection_status"], "closed_by_round738_rejection")

    def test_blocks_when_lpr_rotation_gate_did_not_clear(self) -> None:
        rotation = _round738_rotation_gate()
        rotation["status"] = "blocked"
        rotation["decision"]["rotation_source_gate_allowed_next"] = False

        result = build_cn_stock_non_lpr_orthogonal_source_gate(
            round738_rotation_gate=rotation,
            readiness_gate=_round729_readiness_gate(),
            analyst_prescreen=_round729_analyst_prescreen(),
        )

        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["decision"]["source_gate_selected"])
        self.assertEqual(result["decision"]["selected_source"], "")
        self.assertIn("round738_rotation_gate_not_cleared", result["decision"]["blockers"])

    def test_write_outputs(self) -> None:
        result = build_cn_stock_non_lpr_orthogonal_source_gate(
            round738_rotation_gate=_round738_rotation_gate(),
            readiness_gate=_round729_readiness_gate(),
            analyst_prescreen=_round729_analyst_prescreen(),
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_cn_stock_non_lpr_orthogonal_source_gate(output, result)

            self.assertTrue((output / "cn_stock_non_lpr_orthogonal_source_gate.json").exists())
            self.assertTrue((output / "cn_stock_non_lpr_orthogonal_source_gate.md").exists())
            self.assertTrue((output / "cn_stock_non_lpr_orthogonal_source_rows.csv").exists())


def _round738_rotation_gate() -> dict:
    return {
        "stage": "lpr_macro_regime_walk_forward_rejection_rotation_gate",
        "status": "cleared",
        "decision": {
            "rotation_source_gate_allowed_next": True,
            "same_lpr_candidate_retry_allowed": False,
            "statistical_reality_check_allowed_next": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
        },
        "rotation_policy": {
            "next_direction": "rotate_to_non_lpr_orthogonal_family_source_gate",
            "rerun_same_lpr_gap_widening_candidates_allowed": False,
            "parameter_tuning_allowed": False,
        },
    }


def _round729_readiness_gate() -> dict:
    return {
        "stage": "factor_batch_readiness_gate",
        "status": "blocked",
        "decision": {
            "factor_batch_ready": False,
            "research_screen_allowed": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "blockers": [
                "provider_quota_preflight_blocked:daily_provider_request_budget_exhausted",
                "source_queue_blocked:no_local_no_provider_source_ready",
            ],
        },
        "source_queue_decision": {
            "status": "blocked",
            "local_prescreen_allowed": True,
            "local_prescreen_next_action": "run_cached_local_prescreen_then_wait_for_report_rc_quota_reset",
            "provider_factor_batch_allowed": False,
            "no_provider_factor_batch_allowed": False,
            "provider_request_allowed": False,
        },
        "candidate_plan_gate_decision": {
            "local_prescreen_allowed": True,
            "research_screen_allowed": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
        },
        "provider_quota_preflight_decision": {
            "request_allowed": False,
            "blockers": ["daily_provider_request_budget_exhausted"],
            "next_action": "wait_or_review_provider_quota",
        },
        "summary": {"candidate_count": 4},
        "live_boundary_allowed": False,
    }


def _round729_analyst_prescreen() -> dict:
    return {
        "stage": "analyst_report_revision_prescreen",
        "summary": {
            "candidate_count": 4,
            "multiple_testing_lead_count": 4,
            "neutral_gate_pass_count": 2,
            "year_coverage_pass_count": 0,
            "research_lead_count": 0,
            "promotion_allowed_candidates": 0,
            "next_direction": "rotate_or_cache_more_analyst_report_history_after_zero_prescreen_leads",
        },
        "data_window": {
            "min_report_date": "2024-01-25",
            "max_report_date": "2024-06-30",
            "report_rows": 10509,
            "report_assets": 2226,
        },
        "results": [
            {
                "factor_name": "analyst_target_upside_60",
                "horizon": 5,
                "mean_spearman_ic": 0.1511,
                "ic_year_count": 1,
                "research_lead": False,
                "promotion_allowed": False,
                "blockers": ["ic_year_coverage_below_gate"],
            }
        ],
        "live_boundary_allowed": False,
    }


if __name__ == "__main__":
    unittest.main()
