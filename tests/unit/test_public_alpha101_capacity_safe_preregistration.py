import unittest

from quant_robot.ops.public_alpha101_capacity_safe_preregistration import (
    ROUND113_SOURCE_AUDIT,
    ROUND115_NEXT_DIRECTION,
    build_public_alpha101_capacity_safe_preregistration,
    default_public_alpha101_candidate_specs,
)


class PublicAlpha101CapacitySafePreregistrationTests(unittest.TestCase):
    def test_preregisters_public_alpha101_candidates_without_promotion(self) -> None:
        result = build_public_alpha101_capacity_safe_preregistration(min_candidates=10)

        self.assertEqual(result["stage"], "public_alpha101_capacity_safe_preregistration")
        self.assertTrue(result["summary"]["passes"])
        self.assertGreaterEqual(result["summary"]["candidate_count"], 10)
        self.assertEqual(result["summary"]["portfolio_backtest_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])
        self.assertEqual(result["public_formula_context"]["source_audit"], ROUND113_SOURCE_AUDIT)
        self.assertEqual(result["family_rotation_context"]["next_direction"], ROUND115_NEXT_DIRECTION)
        self.assertIn("worldquant_101_alphas", result["public_reference_review"]["projects_reviewed"])
        self.assertIn("qlib_alpha158_alpha360", result["public_reference_review"]["projects_reviewed"])

        names = {candidate["factor_name"] for candidate in result["candidates"]}
        self.assertIn("alpha101_intraday_close_position_reversal", names)
        self.assertIn("alpha101_price_volume_corr_reversal_20", names)
        self.assertIn("qlib_alpha158_return_std_position_blend_20", names)
        self.assertIn("alpha101_vwap_proxy_reversion_liquid_20", names)

        for candidate in result["candidates"]:
            self.assertEqual(candidate["market"], "CN")
            self.assertEqual(candidate["asset_type"], "stock")
            self.assertEqual(candidate["direction"], "higher_is_better")
            self.assertTrue(candidate["economic_rationale"])
            self.assertIn("public_formula", candidate["source_evidence_status"])
            self.assertTrue(candidate["public_reference_tags"])
            self.assertIn("min_signal_date_amount", candidate["capacity_filters"])
            self.assertIn("max_position_adv_participation", candidate["capacity_filters"])
            self.assertFalse(candidate["portfolio_backtest_allowed"])
            self.assertFalse(candidate["promotion_allowed"])
            self.assertEqual(candidate["next_required_gate"], "round115_public_alpha101_ic_quantile_turnover_prescreen")

    def test_default_specs_are_unique_curated_and_not_random_grid(self) -> None:
        specs = default_public_alpha101_candidate_specs()

        self.assertGreaterEqual(len(specs), 10)
        self.assertEqual(len({spec.factor_name for spec in specs}), len(specs))
        self.assertTrue(all(spec.public_reference_tags for spec in specs))
        self.assertTrue(all(not spec.portfolio_backtest_allowed for spec in specs))
        self.assertTrue(all(not spec.promotion_allowed for spec in specs))
        self.assertTrue(all(len(spec.windows) <= 3 for spec in specs))
        self.assertTrue(
            all(
                any(tag in spec.public_reference_tags for tag in ("worldquant_101_alphas", "qlib_alpha158_alpha360"))
                for spec in specs
            )
        )


if __name__ == "__main__":
    unittest.main()
