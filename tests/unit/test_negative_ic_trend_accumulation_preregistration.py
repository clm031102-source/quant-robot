import unittest

from quant_robot.ops.negative_ic_trend_accumulation_preregistration import (
    ROUND105_SOURCE_AUDIT,
    ROUND106_NEXT_DIRECTION,
    build_negative_ic_trend_accumulation_preregistration,
    default_negative_ic_trend_accumulation_candidate_specs,
)


class NegativeIcTrendAccumulationPreregistrationTests(unittest.TestCase):
    def test_preregisters_anti_overheat_candidates_without_promotion(self) -> None:
        result = build_negative_ic_trend_accumulation_preregistration(min_candidates=8)

        self.assertEqual(result["stage"], "negative_ic_trend_accumulation_preregistration")
        self.assertTrue(result["summary"]["passes"])
        self.assertGreaterEqual(result["summary"]["candidate_count"], 8)
        self.assertEqual(result["summary"]["portfolio_backtest_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])
        self.assertEqual(result["negative_ic_context"]["source_audit"], ROUND105_SOURCE_AUDIT)
        self.assertEqual(result["family_rotation_context"]["next_direction"], ROUND106_NEXT_DIRECTION)
        self.assertIn("not_promotion_evidence", result["negative_ic_context"]["evidence_status"])
        names = {candidate["factor_name"] for candidate in result["candidates"]}
        self.assertIn("anti_money_pressure_efficiency_20", names)
        self.assertIn("overheat_avoidance_composite_20_60", names)
        self.assertTrue(all(("anti" in name or "avoidance" in name or "exhaustion" in name) for name in names))
        for candidate in result["candidates"]:
            self.assertEqual(candidate["market"], "CN")
            self.assertEqual(candidate["asset_type"], "stock")
            self.assertEqual(candidate["direction"], "higher_is_better")
            self.assertTrue(candidate["economic_rationale"])
            self.assertTrue(candidate["public_reference_tags"])
            self.assertIn("min_signal_date_amount", candidate["capacity_filters"])
            self.assertIn("max_position_adv_participation", candidate["capacity_filters"])
            self.assertEqual(candidate["next_required_gate"], "alphalens_style_ic_quantile_turnover_prescreen")

    def test_default_specs_are_unique_and_mark_round105_as_hypothesis_evidence(self) -> None:
        specs = default_negative_ic_trend_accumulation_candidate_specs()

        self.assertGreaterEqual(len(specs), 8)
        self.assertEqual(len({spec.factor_name for spec in specs}), len(specs))
        self.assertTrue(all(spec.public_reference_tags for spec in specs))
        self.assertTrue(all(not spec.portfolio_backtest_allowed for spec in specs))
        self.assertTrue(all(not spec.promotion_allowed for spec in specs))
        self.assertTrue(
            all(spec.source_evidence_status == "round105_negative_ic_hypothesis_not_promotion" for spec in specs)
        )


if __name__ == "__main__":
    unittest.main()
