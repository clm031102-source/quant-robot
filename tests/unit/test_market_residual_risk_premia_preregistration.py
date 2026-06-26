import unittest

from quant_robot.ops.market_residual_risk_premia_preregistration import (
    ROUND107_109_SOURCE_AUDIT,
    ROUND110_NEXT_DIRECTION,
    build_market_residual_risk_premia_preregistration,
    default_market_residual_risk_premia_candidate_specs,
)


class MarketResidualRiskPremiaPreregistrationTests(unittest.TestCase):
    def test_preregisters_market_residual_candidates_without_promotion(self) -> None:
        result = build_market_residual_risk_premia_preregistration(min_candidates=8)

        self.assertEqual(result["stage"], "market_residual_risk_premia_preregistration")
        self.assertTrue(result["summary"]["passes"])
        self.assertGreaterEqual(result["summary"]["candidate_count"], 8)
        self.assertEqual(result["summary"]["portfolio_backtest_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])
        self.assertEqual(result["factor_model_context"]["source_audit"], ROUND107_109_SOURCE_AUDIT)
        self.assertEqual(result["family_rotation_context"]["next_direction"], ROUND110_NEXT_DIRECTION)
        self.assertIn("equal_weight_market_proxy", result["factor_model_context"]["market_proxy_policy"])
        self.assertIn("before_prescreen", result["promotion_policy"]["next_allowed_action"])
        names = {candidate["factor_name"] for candidate in result["candidates"]}
        self.assertIn("low_beta_120", names)
        self.assertIn("downside_beta_low_120", names)
        self.assertIn("residual_reversal_5_60", names)
        self.assertIn("crash_resilience_60", names)
        for candidate in result["candidates"]:
            self.assertEqual(candidate["market"], "CN")
            self.assertEqual(candidate["asset_type"], "stock")
            self.assertEqual(candidate["direction"], "higher_is_better")
            self.assertIn("adj_close", candidate["required_fields"])
            self.assertIn("market_equal_weight_return", candidate["required_fields"])
            self.assertTrue(candidate["economic_rationale"])
            self.assertTrue(candidate["public_reference_tags"])
            self.assertIn("min_signal_date_amount", candidate["capacity_filters"])
            self.assertIn("max_position_adv_participation", candidate["capacity_filters"])
            self.assertEqual(candidate["next_required_gate"], "alphalens_style_ic_quantile_turnover_prescreen")

    def test_default_specs_are_unique_and_residual_or_beta_named(self) -> None:
        specs = default_market_residual_risk_premia_candidate_specs()

        self.assertGreaterEqual(len(specs), 8)
        self.assertEqual(len({spec.factor_name for spec in specs}), len(specs))
        self.assertTrue(all(spec.public_reference_tags for spec in specs))
        self.assertTrue(all(not spec.portfolio_backtest_allowed for spec in specs))
        self.assertTrue(all(not spec.promotion_allowed for spec in specs))
        self.assertTrue(
            all(
                any(token in spec.factor_name for token in ("beta", "residual", "idio", "corr", "crash", "skew"))
                for spec in specs
            )
        )
        self.assertTrue(all("market_equal_weight_return" in spec.required_fields for spec in specs))


if __name__ == "__main__":
    unittest.main()
