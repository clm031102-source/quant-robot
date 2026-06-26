import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.factor_mining_candidate_plan_gate import build_factor_mining_candidate_plan_gate
from quant_robot.ops.public_tradeable_indicator_composite_preregistration import (
    NEXT_REQUIRED_GATE,
    PublicTradeableIndicatorCompositeCandidateSpec,
    build_public_tradeable_indicator_composite_preregistration,
    default_public_tradeable_indicator_composite_candidate_specs,
    write_public_tradeable_indicator_composite_preregistration,
)


class PublicTradeableIndicatorCompositePreregistrationTests(unittest.TestCase):
    def test_preregisters_accessible_public_tradeable_indicator_composites_and_clears_candidate_gate(self) -> None:
        result = build_public_tradeable_indicator_composite_preregistration(min_candidates=8, min_families=4)

        self.assertEqual(result["stage"], "public_tradeable_indicator_composite_preregistration")
        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["summary"]["round"], 264)
        self.assertGreaterEqual(result["summary"]["candidate_count"], 8)
        self.assertGreaterEqual(result["summary"]["family_count"], 4)
        self.assertEqual(result["summary"]["portfolio_backtest_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["next_required_gate"], NEXT_REQUIRED_GATE)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])

        self.assertIn("alphalens", result["public_reference_review"]["projects_reviewed"])
        self.assertIn("vectorbt", result["public_reference_review"]["projects_reviewed"])
        self.assertIn("qtype", result["public_reference_review"]["static_checks"])

        families = {candidate["family"] for candidate in result["candidates"]}
        self.assertIn("trend_exhaustion_reversal_composite", families)
        self.assertIn("volume_price_absorption_composite", families)
        self.assertIn("volatility_compression_breakout_quality", families)
        self.assertIn("risk_adjusted_momentum_quality", families)

        names = {candidate["factor_name"] for candidate in result["candidates"]}
        self.assertIn("mfi_cmf_exhaustion_reversal_liquid_14_20", names)
        self.assertIn("supertrend_pullback_absorption_quality_10_3_20", names)
        self.assertIn("atr_bandwidth_compression_breakout_quality_20", names)
        self.assertIn("adx_efficiency_momentum_quality_14_20", names)

        forbidden_families = {
            "public_supertrend",
            "public_trend_volume_single_filter",
            "daily_basic_low_turnover_repair_after_round263_recovery_audit_failure",
            "smart_money_flow_public_reference_after_round263_low_icir_quantile_failure",
        }
        for candidate in result["candidates"]:
            self.assertEqual(candidate["market"], "CN")
            self.assertEqual(candidate["asset_type"], "stock")
            self.assertEqual(candidate["registration_status"], "pre_registered")
            self.assertNotIn(candidate["family"], forbidden_families)
            self.assertTrue(candidate["hypothesis_source"].startswith("public_indicator_composite:"))
            self.assertTrue(candidate["economic_rationale"])
            self.assertTrue(candidate["public_reference_tags"])
            self.assertTrue(candidate["expected_failure_modes"])
            self.assertTrue(candidate["regime_diagnostics_required"])
            self.assertTrue(candidate["twenty_fifteen_risk_diagnostic_required"])
            self.assertFalse(candidate["portfolio_backtest_allowed"])
            self.assertFalse(candidate["promotion_allowed"])
            self.assertIn("min_signal_date_amount", candidate["capacity_filters"])
            self.assertIn("max_position_adv_participation", candidate["capacity_filters"])
            self.assertLessEqual(len(candidate["windows"]), 4)

        gate = build_factor_mining_candidate_plan_gate(result, gate_stage="discovery")
        self.assertEqual(gate["status"], "research_ready")
        self.assertTrue(gate["decision"]["candidate_plan_gate_cleared"])
        self.assertFalse(gate["decision"]["portfolio_grid_allowed"])
        self.assertFalse(gate["decision"]["promotion_allowed"])

    def test_default_specs_are_unique_and_not_single_indicator_reentries(self) -> None:
        specs = default_public_tradeable_indicator_composite_candidate_specs()

        self.assertGreaterEqual(len(specs), 8)
        self.assertEqual(len({spec.factor_name for spec in specs}), len(specs))
        self.assertGreaterEqual(len({spec.family for spec in specs}), 4)
        self.assertTrue(all(spec.hypothesis_source.startswith("public_indicator_composite:") for spec in specs))
        self.assertTrue(all("public_supertrend" not in spec.family for spec in specs))
        self.assertTrue(all(spec.public_reference_tags for spec in specs))
        self.assertTrue(all(spec.expected_failure_modes for spec in specs))
        self.assertTrue(all(not spec.portfolio_backtest_allowed for spec in specs))
        self.assertTrue(all(not spec.promotion_allowed for spec in specs))

    def test_blocks_duplicate_or_forbidden_family_candidates(self) -> None:
        specs = [
            PublicTradeableIndicatorCompositeCandidateSpec(
                factor_name="duplicate_candidate",
                family="public_supertrend",
                formula_template="cs_z(supertrend_state_10_3)",
                direction="higher_is_better",
                windows=(10,),
                required_fields=("adj_close", "high", "low", "amount"),
                hypothesis_source="public_indicator_composite:forbidden_single_supertrend",
                economic_rationale="Forbidden family should stay hibernated after earlier failures.",
                public_reference_tags=("vectorbt",),
                expected_failure_modes=("single_indicator_reentry",),
            ),
            PublicTradeableIndicatorCompositeCandidateSpec(
                factor_name="duplicate_candidate",
                family="public_supertrend",
                formula_template="cs_z(supertrend_distance_10_3)",
                direction="higher_is_better",
                windows=(10,),
                required_fields=("adj_close", "high", "low", "amount"),
                hypothesis_source="public_indicator_composite:forbidden_duplicate",
                economic_rationale="Duplicate names should not be counted as separate hypotheses.",
                public_reference_tags=("vectorbt",),
                expected_failure_modes=("duplicate_name",),
            ),
        ]

        result = build_public_tradeable_indicator_composite_preregistration(
            candidate_specs=specs,
            min_candidates=3,
            min_families=2,
        )

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("duplicate_candidate_names", result["summary"]["blockers"])
        self.assertIn("candidate_count_below_minimum", result["summary"]["blockers"])
        self.assertIn("family_breadth_below_minimum", result["summary"]["blockers"])
        self.assertIn("forbidden_or_hibernated_family_present:public_supertrend", result["summary"]["blockers"])

    def test_writer_outputs_json_markdown_and_candidate_csv(self) -> None:
        result = build_public_tradeable_indicator_composite_preregistration()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_public_tradeable_indicator_composite_preregistration(output, result)

            self.assertTrue((output / "public_tradeable_indicator_composite_preregistration.json").exists())
            self.assertTrue((output / "public_tradeable_indicator_composite_preregistration.md").exists())
            self.assertTrue((output / "public_tradeable_indicator_composite_candidates.csv").exists())
            markdown = (output / "public_tradeable_indicator_composite_preregistration.md").read_text(encoding="utf-8")
            self.assertIn("Public Tradeable Indicator Composite Preregistration", markdown)
            self.assertIn("Round263 Historical Lead Recovery Audit", markdown)


if __name__ == "__main__":
    unittest.main()
