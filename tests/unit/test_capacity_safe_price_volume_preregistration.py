import unittest

from quant_robot.ops.capacity_safe_price_volume_preregistration import (
    CapacitySafePriceVolumeCandidateSpec,
    build_capacity_safe_price_volume_preregistration,
)


class CapacitySafePriceVolumePreregistrationTests(unittest.TestCase):
    def test_preregisters_public_reference_candidates_with_capacity_and_promotion_gates(self) -> None:
        result = build_capacity_safe_price_volume_preregistration(min_candidates=8)

        self.assertEqual(result["stage"], "capacity_safe_price_volume_preregistration")
        self.assertTrue(result["summary"]["passes"])
        self.assertGreaterEqual(result["summary"]["candidate_count"], 8)
        self.assertEqual(result["summary"]["portfolio_backtest_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])
        self.assertIn("alphalens", result["public_reference_review"]["projects_reviewed"])
        self.assertIn("worldquant_101_alphas", result["public_reference_review"]["projects_reviewed"])

        candidates = {candidate["factor_name"]: candidate for candidate in result["candidates"]}
        self.assertIn("pv_lowvol_reversal_blend_20", candidates)
        self.assertIn("bollinger_reversal_lowvol_liquid_20", candidates)
        self.assertIn("skip5_momentum_lowvol_20", candidates)

        for candidate in candidates.values():
            self.assertEqual(candidate["registration_status"], "pre_registered")
            self.assertEqual(candidate["market"], "CN")
            self.assertEqual(candidate["asset_type"], "stock")
            self.assertTrue(candidate["economic_rationale"])
            self.assertTrue(candidate["public_reference_tags"])
            self.assertIn("min_signal_date_amount", candidate["capacity_filters"])
            self.assertIn("max_position_adv_participation", candidate["capacity_filters"])
            self.assertFalse(candidate["portfolio_backtest_allowed"])
            self.assertFalse(candidate["promotion_allowed"])
            self.assertEqual(
                candidate["next_required_gate"],
                "alphalens_style_ic_quantile_turnover_prescreen",
            )

    def test_blocks_duplicate_or_under_budget_candidate_registration(self) -> None:
        duplicate_specs = [
            CapacitySafePriceVolumeCandidateSpec(
                factor_name="duplicate_candidate",
                family="price_volume",
                formula_template="cs_z(reversal_5)",
                direction="higher_is_better",
                windows=(5,),
                required_fields=("adj_close",),
                economic_rationale="Short-horizon reversal is a public mean-reversion hypothesis.",
                public_reference_tags=("alphalens",),
            ),
            CapacitySafePriceVolumeCandidateSpec(
                factor_name="duplicate_candidate",
                family="price_volume",
                formula_template="cs_z(reversal_20)",
                direction="higher_is_better",
                windows=(20,),
                required_fields=("adj_close",),
                economic_rationale="Duplicate names must not be registered as separate tests.",
                public_reference_tags=("alphalens",),
            ),
        ]

        result = build_capacity_safe_price_volume_preregistration(
            candidate_specs=duplicate_specs,
            min_candidates=3,
        )

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("duplicate_candidate_names", result["summary"]["blockers"])
        self.assertIn("candidate_count_below_minimum", result["summary"]["blockers"])


if __name__ == "__main__":
    unittest.main()
