import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from quant_robot.ops.cn_tradeability_limit_event_preregistration import (
    NEXT_REQUIRED_GATE,
    SOURCE_AUDIT,
    SOURCE_EVIDENCE_STATUS,
    build_cn_tradeability_limit_event_preregistration,
    default_cn_tradeability_limit_event_specs,
    write_cn_tradeability_limit_event_preregistration,
)


class CNTradeabilityLimitEventPreregistrationTests(unittest.TestCase):
    def test_preregisters_tradeability_event_candidates_without_promotion(self) -> None:
        result = build_cn_tradeability_limit_event_preregistration()

        self.assertEqual(result["stage"], "cn_tradeability_limit_event_preregistration")
        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["summary"]["candidate_count"], 8)
        self.assertGreaterEqual(result["summary"]["family_count"], 5)
        self.assertEqual(result["summary"]["rsrs_candidate_count"], 0)
        self.assertEqual(result["summary"]["moneyflow_candidate_count"], 0)
        self.assertEqual(result["summary"]["price_volume_shock_candidate_count"], 0)
        self.assertEqual(result["summary"]["portfolio_backtest_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["true_limit_status_audit_required_candidates"], 8)
        self.assertEqual(result["summary"]["tradeability_controls_required_candidates"], 8)
        self.assertEqual(result["summary"]["next_required_gate"], NEXT_REQUIRED_GATE)
        self.assertEqual(result["rotation_context"]["source_audit"], SOURCE_AUDIT)
        self.assertEqual(result["rotation_context"]["next_direction"], NEXT_REQUIRED_GATE)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_proxy_prescreen"])
        self.assertTrue(result["promotion_policy"]["requires_true_limit_status_audit"])
        self.assertTrue(result["promotion_policy"]["requires_cn_stock_tradeability_gate"])
        self.assertFalse(result["live_boundary_allowed"])

        names = {candidate["factor_name"] for candidate in result["candidates"]}
        self.assertIn("limit_down_relief_reversal_liquid_1_5", names)
        self.assertIn("near_limit_down_rebound_quality_3_10", names)
        self.assertIn("failed_limit_up_reversal_1_5", names)
        self.assertIn("limit_pressure_asymmetry_reversal_5_20", names)

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
            self.assertNotIn("moneyflow", searchable)
            self.assertNotIn("price_volume_shock", searchable)
            self.assertEqual(candidate["source_evidence_status"], SOURCE_EVIDENCE_STATUS)
            self.assertEqual(candidate["market"], "CN")
            self.assertEqual(candidate["asset_type"], "stock")
            self.assertFalse(candidate["portfolio_backtest_allowed"])
            self.assertFalse(candidate["promotion_allowed"])
            self.assertTrue(candidate["true_limit_status_audit_required"])
            self.assertTrue(candidate["tradeability_controls_required"])
            self.assertIn("cn_stock_tradeability_gate", candidate["required_controls"])
            self.assertIn("st_suspension_new_listing_delist_board_filter", candidate["required_controls"])
            self.assertEqual(candidate["next_required_gate"], NEXT_REQUIRED_GATE)

    def test_forbidden_family_reentry_blocks_preregistration(self) -> None:
        specs = default_cn_tradeability_limit_event_specs()
        specs[0] = replace(
            specs[0],
            factor_name="moneyflow_limit_down_relief_5",
            formula_template="cs_z(moneyflow_net_amount_5)",
            public_reference_tags=("moneyflow",),
        )

        result = build_cn_tradeability_limit_event_preregistration(candidate_specs=specs)

        self.assertFalse(result["summary"]["passes"])
        self.assertEqual(result["summary"]["moneyflow_candidate_count"], 1)
        self.assertIn("moneyflow_family_reentry_blocked", result["summary"]["blockers"])

    def test_family_breadth_failure_blocks_preregistration(self) -> None:
        narrow_specs = [
            spec
            for spec in default_cn_tradeability_limit_event_specs()
            if spec.family == "limit_down_recovery"
        ]

        result = build_cn_tradeability_limit_event_preregistration(
            min_candidates=2,
            min_families=2,
            candidate_specs=narrow_specs,
        )

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("family_breadth_below_minimum", result["summary"]["blockers"])

    def test_write_outputs(self) -> None:
        result = build_cn_tradeability_limit_event_preregistration()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_cn_tradeability_limit_event_preregistration(output, result)
            self.assertTrue((output / "cn_tradeability_limit_event_preregistration.json").exists())
            self.assertTrue((output / "cn_tradeability_limit_event_preregistration.md").exists())
            self.assertTrue((output / "cn_tradeability_limit_event_candidates.csv").exists())


if __name__ == "__main__":
    unittest.main()
