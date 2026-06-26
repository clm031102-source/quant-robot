import unittest

from quant_robot.ops.capacity_safe_trend_accumulation_preregistration import (
    build_capacity_safe_trend_accumulation_preregistration,
    default_capacity_safe_trend_accumulation_candidate_specs,
)


class CapacitySafeTrendAccumulationPreregistrationTests(unittest.TestCase):
    def test_preregisters_non_reversal_trend_accumulation_candidates(self) -> None:
        result = build_capacity_safe_trend_accumulation_preregistration(min_candidates=8)

        self.assertEqual(result["stage"], "capacity_safe_trend_accumulation_preregistration")
        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["summary"]["candidate_count"], 10)
        self.assertEqual(result["summary"]["portfolio_backtest_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])
        names = {candidate["factor_name"] for candidate in result["candidates"]}
        self.assertIn("volume_weighted_momentum_quality_20", names)
        self.assertIn("amount_accumulation_breakout_20_60", names)
        self.assertIn("money_pressure_efficiency_20", names)
        forbidden_tokens = ("bollinger", "rsi", "donchian", "range_contraction", "lowvol_reversal")
        self.assertFalse(any(token in name for name in names for token in forbidden_tokens))
        for candidate in result["candidates"]:
            self.assertEqual(candidate["market"], "CN")
            self.assertEqual(candidate["asset_type"], "stock")
            self.assertTrue(candidate["economic_rationale"])
            self.assertTrue(candidate["public_reference_tags"])
            self.assertIn("min_signal_date_amount", candidate["capacity_filters"])
            self.assertIn("max_position_adv_participation", candidate["capacity_filters"])
            self.assertEqual(candidate["next_required_gate"], "alphalens_style_ic_quantile_turnover_prescreen")

    def test_default_specs_are_unique_and_use_public_references(self) -> None:
        specs = default_capacity_safe_trend_accumulation_candidate_specs()

        self.assertEqual(len(specs), 10)
        self.assertEqual(len({spec.factor_name for spec in specs}), 10)
        self.assertTrue(all(spec.public_reference_tags for spec in specs))
        self.assertTrue(all(not spec.portfolio_backtest_allowed for spec in specs))
        self.assertTrue(all(not spec.promotion_allowed for spec in specs))


if __name__ == "__main__":
    unittest.main()
