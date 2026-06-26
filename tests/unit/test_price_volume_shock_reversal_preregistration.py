import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from quant_robot.ops.price_volume_shock_reversal_preregistration import (
    NEXT_REQUIRED_GATE,
    SOURCE_AUDIT,
    SOURCE_EVIDENCE_STATUS,
    build_price_volume_shock_reversal_preregistration,
    default_price_volume_shock_reversal_specs,
    write_price_volume_shock_reversal_preregistration,
)


class PriceVolumeShockReversalPreregistrationTests(unittest.TestCase):
    def test_preregisters_non_rsrs_price_volume_shock_candidates_without_promotion(self) -> None:
        result = build_price_volume_shock_reversal_preregistration()

        self.assertEqual(result["stage"], "price_volume_shock_reversal_preregistration")
        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["summary"]["candidate_count"], 8)
        self.assertGreaterEqual(result["summary"]["family_count"], 4)
        self.assertEqual(result["summary"]["rsrs_candidate_count"], 0)
        self.assertEqual(result["summary"]["portfolio_backtest_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["next_required_gate"], NEXT_REQUIRED_GATE)
        self.assertEqual(result["rotation_context"]["source_audit"], SOURCE_AUDIT)
        self.assertEqual(result["rotation_context"]["next_direction"], NEXT_REQUIRED_GATE)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_neutral_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])

        names = {candidate["factor_name"] for candidate in result["candidates"]}
        self.assertIn("amihud_shock_reversal_liquid_20_60", names)
        self.assertIn("volume_climax_reversal_close_location_20", names)
        self.assertIn("range_expansion_exhaustion_reversal_20", names)
        self.assertIn("gap_range_failure_reversal_5_20", names)

        for candidate in result["candidates"]:
            searchable = " ".join(
                [
                    candidate["factor_name"],
                    candidate["family"],
                    candidate["formula_template"],
                    " ".join(candidate["public_reference_tags"]),
                ]
            ).lower()
            self.assertNotIn("rsrs", searchable)
            self.assertEqual(candidate["source_evidence_status"], SOURCE_EVIDENCE_STATUS)
            self.assertEqual(candidate["market"], "CN")
            self.assertEqual(candidate["asset_type"], "stock")
            self.assertFalse(candidate["portfolio_backtest_allowed"])
            self.assertFalse(candidate["promotion_allowed"])
            self.assertEqual(candidate["next_required_gate"], NEXT_REQUIRED_GATE)

    def test_rsrs_reentry_blocks_preregistration(self) -> None:
        specs = default_price_volume_shock_reversal_specs()
        specs[0] = replace(
            specs[0],
            factor_name="rsrs_reentry_20",
            formula_template="cs_z(rsrs_slope_18)",
            public_reference_tags=("public_rsrs",),
        )

        result = build_price_volume_shock_reversal_preregistration(candidate_specs=specs)

        self.assertFalse(result["summary"]["passes"])
        self.assertEqual(result["summary"]["rsrs_candidate_count"], 1)
        self.assertIn("rsrs_family_reentry_blocked", result["summary"]["blockers"])

    def test_family_breadth_failure_blocks_preregistration(self) -> None:
        narrow_specs = [
            spec
            for spec in default_price_volume_shock_reversal_specs()
            if spec.family == "liquidity_stress_reversal"
        ]

        result = build_price_volume_shock_reversal_preregistration(
            min_candidates=2,
            min_families=2,
            candidate_specs=narrow_specs,
        )

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("family_breadth_below_minimum", result["summary"]["blockers"])

    def test_write_outputs(self) -> None:
        result = build_price_volume_shock_reversal_preregistration()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_price_volume_shock_reversal_preregistration(output, result)
            self.assertTrue((output / "price_volume_shock_reversal_preregistration.json").exists())
            self.assertTrue((output / "price_volume_shock_reversal_preregistration.md").exists())
            self.assertTrue((output / "price_volume_shock_reversal_candidates.csv").exists())


if __name__ == "__main__":
    unittest.main()
