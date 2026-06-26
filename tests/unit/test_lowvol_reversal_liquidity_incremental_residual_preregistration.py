import unittest

from quant_robot.ops.lowvol_reversal_liquidity_incremental_residual_preregistration import (
    ROUND118_SOURCE_AUDIT,
    ROUND120_NEXT_DIRECTION,
    build_lowvol_reversal_liquidity_incremental_residual_preregistration,
    default_lowvol_reversal_liquidity_incremental_residual_specs,
)


class LowvolReversalLiquidityIncrementalResidualPreregistrationTests(unittest.TestCase):
    def test_preregisters_incremental_residual_candidates_without_promotion(self) -> None:
        result = build_lowvol_reversal_liquidity_incremental_residual_preregistration(min_candidates=8)

        self.assertEqual(result["stage"], "lowvol_reversal_liquidity_incremental_residual_preregistration")
        self.assertTrue(result["summary"]["passes"])
        self.assertGreaterEqual(result["summary"]["candidate_count"], 8)
        self.assertEqual(result["summary"]["next_required_gate"], ROUND120_NEXT_DIRECTION)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertEqual(result["incremental_residual_context"]["source_audit"], ROUND118_SOURCE_AUDIT)
        self.assertIn(
            "amount_stability_reversal_5_20",
            result["incremental_residual_context"]["reference_cluster_members"],
        )
        self.assertIn("log_adv20_amount", result["incremental_residual_context"]["exposure_controls"])
        self.assertIn("beta_120", result["incremental_residual_context"]["exposure_controls"])
        self.assertIn("market_corr_60", result["incremental_residual_context"]["exposure_controls"])

        names = {candidate["factor_name"] for candidate in result["candidates"]}
        self.assertIn("qlib_blend_residual_vs_lowvol_cluster_5", names)
        self.assertIn("qlib_blend_cluster_exposure_neutral_residual_5", names)
        self.assertIn("range_contraction_incremental_residual_20", names)

        for candidate in result["candidates"]:
            self.assertEqual(candidate["market"], "CN")
            self.assertEqual(candidate["asset_type"], "stock")
            self.assertEqual(candidate["next_required_gate"], ROUND120_NEXT_DIRECTION)
            self.assertFalse(candidate["portfolio_backtest_allowed"])
            self.assertFalse(candidate["promotion_allowed"])
            self.assertIn("incremental_residual", candidate["source_evidence_status"])
            self.assertTrue(
                "cs_resid(" in candidate["formula_template"] or "orthogonalize(" in candidate["formula_template"]
            )

    def test_default_specs_are_unique_and_reference_controlled(self) -> None:
        specs = default_lowvol_reversal_liquidity_incremental_residual_specs()

        self.assertGreaterEqual(len(specs), 8)
        self.assertEqual(len({spec.factor_name for spec in specs}), len(specs))
        self.assertTrue(all(not spec.portfolio_backtest_allowed for spec in specs))
        self.assertTrue(all(not spec.promotion_allowed for spec in specs))
        self.assertTrue(all("reference_factor_matrix" in spec.required_fields for spec in specs))
        self.assertTrue(all(len(spec.windows) <= 3 for spec in specs))


if __name__ == "__main__":
    unittest.main()
