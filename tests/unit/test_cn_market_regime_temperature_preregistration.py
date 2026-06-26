import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from quant_robot.ops.cn_market_regime_temperature_preregistration import (
    NEXT_REQUIRED_GATE,
    SOURCE_AUDIT,
    SOURCE_EVIDENCE_STATUS,
    build_cn_market_regime_temperature_preregistration,
    default_cn_market_regime_temperature_specs,
    write_cn_market_regime_temperature_preregistration,
)


class CNMarketRegimeTemperaturePreregistrationTests(unittest.TestCase):
    def test_preregisters_regime_temperature_candidates_without_portfolio_or_promotion(self) -> None:
        result = build_cn_market_regime_temperature_preregistration()

        self.assertEqual(result["stage"], "cn_market_regime_temperature_preregistration")
        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["summary"]["candidate_count"], 6)
        self.assertGreaterEqual(result["summary"]["family_count"], 4)
        self.assertEqual(result["summary"]["failed_recent_family_candidate_count"], 0)
        self.assertEqual(result["summary"]["portfolio_backtest_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["lagged_regime_required_candidates"], 6)
        self.assertEqual(result["summary"]["residual_prescreen_required_candidates"], 6)
        self.assertEqual(result["summary"]["next_required_gate"], NEXT_REQUIRED_GATE)
        self.assertEqual(result["rotation_context"]["source_audit"], SOURCE_AUDIT)
        self.assertEqual(result["rotation_context"]["next_direction"], NEXT_REQUIRED_GATE)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_residual_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])

        names = {candidate["factor_name"] for candidate in result["candidates"]}
        self.assertIn("regime_cold_liquidity_reversal_quality_20_5", names)
        self.assertIn("market_temperature_state_interaction_composite_20_5", names)

        for candidate in result["candidates"]:
            self.assertEqual(candidate["market"], "CN")
            self.assertEqual(candidate["asset_type"], "stock")
            self.assertEqual(candidate["source_evidence_status"], SOURCE_EVIDENCE_STATUS)
            self.assertFalse(candidate["portfolio_backtest_allowed"])
            self.assertFalse(candidate["promotion_allowed"])
            self.assertTrue(candidate["lagged_regime_state_required"])
            self.assertTrue(candidate["residual_prescreen_required"])
            self.assertIn("lagged_market_temperature_state", candidate["required_controls"])
            self.assertIn("no_same_day_forward_label_leakage", candidate["required_controls"])
            self.assertIn("industry_style_residual_evaluation", candidate["required_controls"])

    def test_forbidden_recent_family_reentry_blocks_preregistration(self) -> None:
        specs = default_cn_market_regime_temperature_specs()
        specs[0] = replace(
            specs[0],
            family="tradeability_limit_events",
            factor_name="limit_event_regime_temperature_retry",
            public_reference_tags=("limit_event",),
        )

        result = build_cn_market_regime_temperature_preregistration(candidate_specs=specs)

        self.assertFalse(result["summary"]["passes"])
        self.assertEqual(result["summary"]["failed_recent_family_candidate_count"], 1)
        self.assertIn("failed_recent_family_reentry_blocked", result["summary"]["blockers"])

    def test_missing_lagged_regime_control_blocks_preregistration(self) -> None:
        specs = default_cn_market_regime_temperature_specs()
        specs[0] = replace(specs[0], lagged_regime_state_required=False)

        result = build_cn_market_regime_temperature_preregistration(candidate_specs=specs)

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("lagged_regime_state_not_required_for_all_candidates", result["summary"]["blockers"])

    def test_write_outputs(self) -> None:
        result = build_cn_market_regime_temperature_preregistration()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_cn_market_regime_temperature_preregistration(output, result)
            self.assertTrue((output / "cn_market_regime_temperature_preregistration.json").exists())
            self.assertTrue((output / "cn_market_regime_temperature_preregistration.md").exists())
            self.assertTrue((output / "cn_market_regime_temperature_candidates.csv").exists())


if __name__ == "__main__":
    unittest.main()
