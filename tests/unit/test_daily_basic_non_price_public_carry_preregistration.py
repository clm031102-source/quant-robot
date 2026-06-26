import unittest

from quant_robot.ops.daily_basic_non_price_public_carry_preregistration import (
    KNOWN_DAILY_BASIC_FIELDS,
    ROUND130_SOURCE_AUDIT,
    ROUND132_NEXT_DIRECTION,
    SOURCE_EVIDENCE_STATUS,
    DailyBasicNonPricePublicCarryCandidateSpec,
    build_daily_basic_non_price_public_carry_preregistration,
    default_daily_basic_non_price_public_carry_specs,
)


class DailyBasicNonPricePublicCarryPreregistrationTests(unittest.TestCase):
    def test_preregisters_non_price_daily_basic_candidates_without_promotion(self) -> None:
        result = build_daily_basic_non_price_public_carry_preregistration(
            min_candidates=8,
            min_families=4,
        )

        self.assertEqual(result["stage"], "daily_basic_non_price_public_carry_preregistration")
        self.assertTrue(result["summary"]["passes"])
        self.assertGreaterEqual(result["summary"]["candidate_count"], 8)
        self.assertGreaterEqual(result["summary"]["family_count"], 4)
        self.assertEqual(result["summary"]["next_required_gate"], ROUND132_NEXT_DIRECTION)
        self.assertEqual(result["summary"]["portfolio_backtest_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])

        rotation = result["family_rotation_context"]
        self.assertEqual(rotation["source_audit"], ROUND130_SOURCE_AUDIT)
        self.assertIn("alpha101_rank_pv_reversal", rotation["hibernated_families"])
        self.assertIn("low_turnover_repair", rotation["hibernated_families"])
        self.assertEqual(rotation["next_direction"], ROUND132_NEXT_DIRECTION)
        self.assertIn("daily_basic_coverage_preflight", result["evaluation_gate"]["required_metrics"])

        names = {candidate["factor_name"] for candidate in result["candidates"]}
        self.assertIn("daily_basic_dividend_value_stability_carry_20", names)
        self.assertIn("daily_basic_value_yield_size_neutral_20", names)
        self.assertIn("daily_basic_valuation_reversion_quality_60", names)
        self.assertIn("daily_basic_free_float_supply_quality_20", names)

        forbidden_terms = ("low_turnover", "turnover_rate", "turnover_rate_f", "alpha101", "pv_", "moneyflow")
        known_fields = set(KNOWN_DAILY_BASIC_FIELDS)
        for candidate in result["candidates"]:
            self.assertEqual(candidate["market"], "CN")
            self.assertEqual(candidate["asset_type"], "stock")
            self.assertEqual(candidate["source_evidence_status"], SOURCE_EVIDENCE_STATUS)
            self.assertTrue(candidate["economic_rationale"])
            self.assertTrue(candidate["public_reference_tags"])
            self.assertTrue(candidate["expected_failure_modes"])
            self.assertFalse(candidate["portfolio_backtest_allowed"])
            self.assertFalse(candidate["promotion_allowed"])
            self.assertEqual(candidate["next_required_gate"], ROUND132_NEXT_DIRECTION)
            self.assertTrue(set(candidate["required_fields"]).issubset(known_fields))
            combined = f"{candidate['factor_name']} {candidate['formula_template']}".lower()
            for term in forbidden_terms:
                self.assertNotIn(term, combined)

    def test_default_specs_are_unique_daily_basic_only_and_curated(self) -> None:
        specs = default_daily_basic_non_price_public_carry_specs()

        self.assertGreaterEqual(len(specs), 8)
        self.assertEqual(len({spec.factor_name for spec in specs}), len(specs))
        self.assertGreaterEqual(len({spec.family for spec in specs}), 4)
        self.assertTrue(all(spec.public_reference_tags for spec in specs))
        self.assertTrue(all(spec.expected_failure_modes for spec in specs))
        self.assertTrue(all(not spec.portfolio_backtest_allowed for spec in specs))
        self.assertTrue(all(not spec.promotion_allowed for spec in specs))
        self.assertTrue(all(set(spec.required_fields).issubset(set(KNOWN_DAILY_BASIC_FIELDS)) for spec in specs))
        self.assertTrue(any(spec.family == "dividend_value_carry" for spec in specs))
        self.assertTrue(any(spec.family == "valuation_stability" for spec in specs))
        self.assertTrue(any(spec.family == "share_structure_quality" for spec in specs))

    def test_forbidden_field_or_missing_reference_blocks_preregistration(self) -> None:
        bad_spec = DailyBasicNonPricePublicCarryCandidateSpec(
            factor_name="bad_low_turnover_clone",
            family="forbidden",
            formula_template="cs_z(-turnover_rate)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("turnover_rate",),
            economic_rationale="Bad clone of rejected low-turnover line.",
            public_reference_tags=(),
            expected_failure_modes=(),
        )

        result = build_daily_basic_non_price_public_carry_preregistration(
            min_candidates=1,
            min_families=1,
            candidate_specs=[bad_spec],
        )

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("forbidden_low_turnover_or_price_volume_term", result["summary"]["blockers"])
        self.assertIn("unknown_or_forbidden_required_fields", result["summary"]["blockers"])
        self.assertIn("missing_public_reference_tags", result["summary"]["blockers"])
        self.assertIn("missing_expected_failure_modes", result["summary"]["blockers"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
