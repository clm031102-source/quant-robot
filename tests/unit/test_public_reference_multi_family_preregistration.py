import unittest

from quant_robot.ops.public_reference_multi_family_preregistration import (
    ROUND126_SOURCE_AUDIT,
    ROUND128_NEXT_DIRECTION,
    SOURCE_EVIDENCE_STATUS,
    build_public_reference_multi_family_preregistration,
    default_public_reference_multi_family_candidate_specs,
)


class PublicReferenceMultiFamilyPreregistrationTests(unittest.TestCase):
    def test_preregisters_public_reference_multi_family_candidates_without_promotion(self) -> None:
        result = build_public_reference_multi_family_preregistration(min_candidates=18, min_families=6)

        self.assertEqual(result["stage"], "public_reference_multi_family_preregistration")
        self.assertTrue(result["summary"]["passes"])
        self.assertGreaterEqual(result["summary"]["candidate_count"], 18)
        self.assertGreaterEqual(result["summary"]["family_count"], 6)
        self.assertEqual(result["summary"]["portfolio_backtest_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["next_required_gate"], ROUND128_NEXT_DIRECTION)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])

        self.assertEqual(result["family_rotation_context"]["source_audit"], ROUND126_SOURCE_AUDIT)
        self.assertIn("low_turnover_repair", result["family_rotation_context"]["hibernated_families"])
        self.assertEqual(result["family_rotation_context"]["next_direction"], ROUND128_NEXT_DIRECTION)
        self.assertIn("qlib", result["public_reference_review"]["projects_reviewed"])
        self.assertIn("worldquant_101_alphas", result["public_reference_review"]["projects_reviewed"])
        self.assertIn("vectorbt", result["public_reference_review"]["projects_reviewed"])

        names = {candidate["factor_name"] for candidate in result["candidates"]}
        self.assertIn("smart_money_efficiency_reversal_20", names)
        self.assertIn("supertrend_pullback_lowvol_liquid_10_3", names)
        self.assertIn("rsrs_residual_reversal_liquid_18", names)
        self.assertIn("qvm_quality_value_momentum_blend_20_60", names)
        self.assertIn("alpha101_rank_pv_reversal_liquid_20", names)
        self.assertIn("qlib_alpha158_kbar_momentum_lowvol_20", names)

        for candidate in result["candidates"]:
            self.assertEqual(candidate["market"], "CN")
            self.assertEqual(candidate["asset_type"], "stock")
            self.assertEqual(candidate["direction"], "higher_is_better")
            self.assertEqual(candidate["source_evidence_status"], SOURCE_EVIDENCE_STATUS)
            self.assertTrue(candidate["economic_rationale"])
            self.assertTrue(candidate["public_reference_tags"])
            self.assertTrue(candidate["expected_failure_modes"])
            self.assertIn("min_signal_date_amount", candidate["capacity_filters"])
            self.assertIn("max_position_adv_participation", candidate["capacity_filters"])
            self.assertFalse(candidate["portfolio_backtest_allowed"])
            self.assertFalse(candidate["promotion_allowed"])
            self.assertEqual(candidate["next_required_gate"], ROUND128_NEXT_DIRECTION)
            self.assertNotIn("low_turnover", candidate["factor_name"])

    def test_default_specs_are_unique_curated_and_span_multiple_families(self) -> None:
        specs = default_public_reference_multi_family_candidate_specs()

        self.assertGreaterEqual(len(specs), 18)
        self.assertEqual(len({spec.factor_name for spec in specs}), len(specs))
        self.assertGreaterEqual(len({spec.family for spec in specs}), 6)
        self.assertTrue(all(spec.public_reference_tags for spec in specs))
        self.assertTrue(all(spec.expected_failure_modes for spec in specs))
        self.assertTrue(all(not spec.portfolio_backtest_allowed for spec in specs))
        self.assertTrue(all(not spec.promotion_allowed for spec in specs))
        self.assertTrue(all(len(spec.windows) <= 4 for spec in specs))
        self.assertTrue(
            any("supertrend" in spec.factor_name for spec in specs)
            and any("smart_money" in spec.factor_name for spec in specs)
            and any("qvm" in spec.factor_name for spec in specs)
        )

    def test_family_breadth_failure_blocks_preregistration(self) -> None:
        narrow_specs = [
            spec
            for spec in default_public_reference_multi_family_candidate_specs()
            if spec.family == "public_formula_alpha101"
        ]

        result = build_public_reference_multi_family_preregistration(
            min_candidates=3,
            min_families=3,
            candidate_specs=narrow_specs,
        )

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("family_breadth_below_minimum", result["summary"]["blockers"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
