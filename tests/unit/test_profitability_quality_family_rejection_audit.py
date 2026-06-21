import unittest

from quant_robot.ops.profitability_quality_family_rejection_audit import (
    build_profitability_quality_family_rejection_audit,
)


class ProfitabilityQualityFamilyRejectionAuditTests(unittest.TestCase):
    def test_zero_multiple_testing_leads_rejects_family_and_rotates_after_sync(self):
        audit = build_profitability_quality_family_rejection_audit(
            controlled_ic_screen=_controlled_ic_screen(research_leads=0, bonferroni=0, fdr=0),
            source_report="docs/research/cn_stock_profitability_quality_controlled_ic_screen_round98_2026-06-22.md",
            rounds=(97, 98, 99),
        )

        self.assertEqual(audit["stage"], "profitability_quality_family_rejection_audit")
        self.assertEqual(audit["status"], "family_rejected_rotate_after_sync")
        self.assertTrue(audit["decision"]["family_hibernated"])
        self.assertFalse(audit["decision"]["continue_same_family"])
        self.assertEqual(audit["decision"]["immediate_next_direction"], "round100_lightweight_stage_report_and_github_safe_sync")
        self.assertEqual(
            audit["decision"]["post_sync_research_direction"],
            "capacity_safe_price_volume_lowvol_reversal_composite_preregistration",
        )
        self.assertIn("zero_multiple_testing_leads", audit["decision"]["reject_reasons"])
        self.assertIn("profitability_quality_more_parameter_tuning_after_zero_ic_leads", audit["next_protocol"]["forbidden_directions"])
        self.assertIn("qlib", audit["public_reference_review"]["references"])
        self.assertIn("alphalens", audit["public_reference_review"]["references"])
        self.assertIn("vectorbt", audit["public_reference_review"]["references"])
        self.assertIn("worldquant_101_alphas", audit["public_reference_review"]["references"])
        self.assertFalse(audit["promotion_policy"]["portfolio_backtest_allowed"])
        self.assertIn("Family Rejection", audit["markdown"])

    def test_existing_multiple_testing_lead_blocks_rejection_and_requests_robustness(self):
        audit = build_profitability_quality_family_rejection_audit(
            controlled_ic_screen=_controlled_ic_screen(research_leads=1, bonferroni=1, fdr=1),
            rounds=(97, 98, 99),
        )

        self.assertEqual(audit["status"], "family_not_rejected_needs_robustness")
        self.assertFalse(audit["decision"]["family_hibernated"])
        self.assertTrue(audit["decision"]["continue_same_family"])
        self.assertEqual(
            audit["decision"]["immediate_next_direction"],
            "profitability_quality_lead_robustness_and_portfolio_translation_audit",
        )
        self.assertNotIn("zero_multiple_testing_leads", audit["decision"]["reject_reasons"])


def _controlled_ic_screen(*, research_leads: int, bonferroni: int, fdr: int) -> dict:
    return {
        "stage": "profitability_quality_controlled_ic_screen",
        "summary": {
            "passes": True,
            "candidate_count": 14,
            "test_count": 28,
            "ic_observation_count": 1204,
            "bonferroni_significant": bonferroni,
            "fdr_significant": fdr,
            "research_lead_count": research_leads,
            "aligned_rows": 117394,
            "blockers": [],
        },
        "multiple_testing": {"test_count": 28, "bonferroni_alpha": 0.0017857142857142859},
        "promotion_policy": {"portfolio_backtest_allowed": False, "promotion_allowed": False},
    }


if __name__ == "__main__":
    unittest.main()
