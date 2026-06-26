import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.turnover_continuous_capacity_repair_preregistration import (
    TurnoverCapacityRepairCandidateSpec,
    build_turnover_continuous_capacity_repair_preregistration,
    render_turnover_continuous_capacity_repair_markdown,
    write_turnover_continuous_capacity_repair_preregistration,
)


class TurnoverContinuousCapacityRepairPreregistrationTests(unittest.TestCase):
    def test_preregisters_continuous_capacity_repairs_for_raw_turnover_leads(self):
        result = build_turnover_continuous_capacity_repair_preregistration(min_candidates=6)

        self.assertEqual(result["stage"], "turnover_continuous_capacity_repair_preregistration")
        self.assertTrue(result["summary"]["passes"])
        self.assertGreaterEqual(result["summary"]["candidate_count"], 6)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["portfolio_backtest_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["source_research_leads"], 2)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])
        self.assertIn("round122_aggressive_turnover_capacity_audit", result["source_evidence"]["audit_tags"])

        candidates = {candidate["factor_name"]: candidate for candidate in result["candidates"]}
        self.assertIn("turnover_rate_low_adv_soft_rank_20", candidates)
        self.assertIn("turnover_rate_f_low_adv_soft_rank_20", candidates)
        self.assertIn("turnover_rate_low_participation_budget_100k_20", candidates)
        self.assertIn("turnover_rate_f_low_participation_budget_100k_20", candidates)

        for candidate in candidates.values():
            self.assertIn(candidate["raw_factor_name"], {"turnover_rate_low", "turnover_rate_f_low"})
            self.assertEqual(candidate["market"], "CN")
            self.assertEqual(candidate["asset_type"], "stock")
            self.assertEqual(candidate["registration_status"], "pre_registered")
            self.assertEqual(candidate["repair_type"], "continuous_capacity_weight")
            self.assertNotIn("large_mv", candidate["factor_name"])
            self.assertNotIn("binary_large_mv", candidate["formula_template"])
            self.assertTrue(candidate["economic_rationale"])
            self.assertTrue(candidate["capacity_repair_rationale"])
            self.assertIn("amount", candidate["required_fields"])
            self.assertIn("circ_mv", candidate["required_fields"])
            self.assertIn("max_position_adv_participation", candidate["capacity_policy"])
            self.assertFalse(candidate["portfolio_backtest_allowed"])
            self.assertFalse(candidate["promotion_allowed"])
            self.assertEqual(candidate["next_required_gate"], "capacity_repair_ic_quantile_turnover_prescreen")

    def test_blocks_duplicate_or_binary_large_mv_or_promotion_specs(self):
        bad_specs = [
            TurnoverCapacityRepairCandidateSpec(
                factor_name="turnover_rate_low_large_mv",
                raw_factor_name="turnover_rate_low",
                formula_template="binary_large_mv + cs_z(-turnover_rate)",
                repair_type="binary_large_mv",
                required_fields=("turnover_rate", "circ_mv"),
                economic_rationale="Bad binary repair should not be re-registered.",
                capacity_repair_rationale="It repeats the failed large_mv repair.",
            ),
            TurnoverCapacityRepairCandidateSpec(
                factor_name="turnover_rate_low_large_mv",
                raw_factor_name="turnover_rate_low",
                formula_template="cs_z(-turnover_rate) + cs_z(log_adv20)",
                repair_type="continuous_capacity_weight",
                required_fields=("turnover_rate", "amount", "circ_mv"),
                economic_rationale="Duplicate name must be blocked.",
                capacity_repair_rationale="Duplicate tests inflate multiple-testing count.",
                promotion_allowed=True,
            ),
        ]

        result = build_turnover_continuous_capacity_repair_preregistration(
            candidate_specs=bad_specs,
            min_candidates=3,
        )

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("candidate_count_below_minimum", result["summary"]["blockers"])
        self.assertIn("duplicate_candidate_names", result["summary"]["blockers"])
        self.assertIn("binary_large_mv_repair_reused", result["summary"]["blockers"])
        self.assertIn("promotion_allowed_before_validation", result["summary"]["blockers"])

    def test_writer_emits_json_markdown_and_csv(self):
        result = build_turnover_continuous_capacity_repair_preregistration(min_candidates=6)
        markdown = render_turnover_continuous_capacity_repair_markdown(result)

        self.assertIn("Turnover Continuous Capacity Repair Preregistration", markdown)
        self.assertIn("capacity_repair_ic_quantile_turnover_prescreen", markdown)

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_turnover_continuous_capacity_repair_preregistration(output_dir, result)

            self.assertTrue((output_dir / "turnover_continuous_capacity_repair_preregistration.json").exists())
            self.assertTrue((output_dir / "turnover_continuous_capacity_repair_preregistration.md").exists())
            self.assertTrue((output_dir / "turnover_continuous_capacity_repair_candidates.csv").exists())


if __name__ == "__main__":
    unittest.main()
