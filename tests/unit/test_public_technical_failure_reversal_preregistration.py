import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.public_technical_failure_reversal_preregistration import (
    NEGATIVE_EVIDENCE_AUDIT,
    NEXT_REQUIRED_GATE,
    SOURCE_AUDIT,
    SOURCE_EVIDENCE_STATUS,
    build_public_technical_failure_reversal_preregistration,
    default_public_technical_failure_reversal_specs,
    write_public_technical_failure_reversal_preregistration,
)


class PublicTechnicalFailureReversalPreregistrationTests(unittest.TestCase):
    def test_preregisters_public_technical_failure_reversal_candidates_without_promotion(self) -> None:
        result = build_public_technical_failure_reversal_preregistration()

        self.assertEqual(result["stage"], "public_technical_failure_reversal_preregistration")
        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["summary"]["candidate_count"], 8)
        self.assertGreaterEqual(result["summary"]["family_count"], 4)
        self.assertEqual(result["summary"]["portfolio_backtest_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["next_required_gate"], NEXT_REQUIRED_GATE)
        self.assertEqual(result["rotation_context"]["source_audit"], SOURCE_AUDIT)
        self.assertEqual(result["rotation_context"]["negative_evidence_audit"], NEGATIVE_EVIDENCE_AUDIT)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])

        names = {candidate["factor_name"] for candidate in result["candidates"]}
        self.assertIn("inverse_donchian_breakout_failure_liquid_20", names)
        self.assertIn("inverse_supertrend_breakout_failure_10_20", names)
        self.assertIn("inverse_rsrs_slope_failure_liquid_18_60", names)
        for candidate in result["candidates"]:
            self.assertEqual(candidate["source_evidence_status"], SOURCE_EVIDENCE_STATUS)
            self.assertEqual(candidate["market"], "CN")
            self.assertEqual(candidate["asset_type"], "stock")
            self.assertFalse(candidate["portfolio_backtest_allowed"])
            self.assertFalse(candidate["promotion_allowed"])
            self.assertEqual(candidate["next_required_gate"], NEXT_REQUIRED_GATE)

    def test_family_breadth_failure_blocks_preregistration(self) -> None:
        narrow_specs = [
            spec
            for spec in default_public_technical_failure_reversal_specs()
            if spec.family == "supertrend_failure_reversal"
        ]

        result = build_public_technical_failure_reversal_preregistration(
            min_candidates=2,
            min_families=2,
            candidate_specs=narrow_specs,
        )

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("family_breadth_below_minimum", result["summary"]["blockers"])

    def test_write_outputs(self) -> None:
        result = build_public_technical_failure_reversal_preregistration()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_public_technical_failure_reversal_preregistration(output, result)
            self.assertTrue((output / "public_technical_failure_reversal_preregistration.json").exists())
            self.assertTrue((output / "public_technical_failure_reversal_preregistration.md").exists())
            self.assertTrue((output / "public_technical_failure_reversal_candidates.csv").exists())


if __name__ == "__main__":
    unittest.main()
