import unittest

from quant_robot.ops.lottery_extreme_upside_reversal_preregistration import (
    NEXT_REQUIRED_GATE,
    build_lottery_extreme_upside_reversal_preregistration,
)
from quant_robot.ops.factor_mining_candidate_plan_gate import build_factor_mining_candidate_plan_gate


class LotteryExtremeUpsideReversalPreregistrationTests(unittest.TestCase):
    def test_preregisters_public_max_effect_candidates_without_portfolio_permission(self) -> None:
        result = build_lottery_extreme_upside_reversal_preregistration(min_candidates=6)

        self.assertEqual(result["stage"], "lottery_extreme_upside_reversal_preregistration")
        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["summary"]["next_required_gate"], NEXT_REQUIRED_GATE)
        self.assertEqual(result["summary"]["portfolio_backtest_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["live_boundary_allowed"])
        self.assertIn("research_control_plan", result)
        self.assertIn(
            "limit_up_down_filter",
            result["research_control_plan"]["declared_controls"]["cn_stock_tradeability"],
        )
        self.assertIn(
            "parameter_sensitivity_heatmap",
            result["research_control_plan"]["declared_controls"]["strict_statistics"],
        )
        plan_gate = build_factor_mining_candidate_plan_gate(result, gate_stage="discovery")
        self.assertTrue(plan_gate["decision"]["candidate_plan_gate_cleared"])
        self.assertFalse(plan_gate["decision"]["portfolio_grid_allowed"])

        candidates = {candidate["factor_name"]: candidate for candidate in result["candidates"]}
        self.assertIn("lottery_max_return_reversal_20", candidates)
        self.assertIn("lottery_limit_chase_exhaustion_20", candidates)
        self.assertIn("lottery_upside_tail_asymmetry_reversal_60", candidates)
        self.assertIn("max_effect", candidates["lottery_max_return_reversal_20"]["public_reference_tags"])
        self.assertIn("exclude_limit_up_down_if_untradable", candidates["lottery_limit_chase_exhaustion_20"]["capacity_filters"])

    def test_blocks_under_budget_or_duplicate_candidate_specs(self) -> None:
        result = build_lottery_extreme_upside_reversal_preregistration(
            candidate_specs=[
                {
                    "factor_name": "dup",
                    "family": "lottery",
                    "formula_template": "cs_z(-max_return_20)",
                    "direction": "higher_is_better",
                    "windows": [20],
                    "required_fields": ["adj_close"],
                    "economic_rationale": "Extreme upside demand can reverse.",
                    "public_reference_tags": ["max_effect"],
                },
                {
                    "factor_name": "dup",
                    "family": "lottery",
                    "formula_template": "cs_z(-max_return_60)",
                    "direction": "higher_is_better",
                    "windows": [60],
                    "required_fields": ["adj_close"],
                    "economic_rationale": "Duplicate names must not hide extra tests.",
                    "public_reference_tags": ["max_effect"],
                },
            ],
            min_candidates=3,
        )

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("duplicate_candidate_names", result["summary"]["blockers"])
        self.assertIn("candidate_count_below_minimum", result["summary"]["blockers"])


if __name__ == "__main__":
    unittest.main()
