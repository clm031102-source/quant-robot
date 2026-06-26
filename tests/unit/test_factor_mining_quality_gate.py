import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.factor_mining_quality_gate import (
    DEFAULT_CN_STOCK_QUALITY_AREAS,
    build_factor_mining_quality_gate,
    required_control_ids,
    validate_quality_gate_for_startup,
)


class FactorMiningQualityGateTests(unittest.TestCase):
    def test_default_gate_contains_user_requested_optimization_areas(self) -> None:
        area_ids = {area["id"] for area in DEFAULT_CN_STOCK_QUALITY_AREAS}

        self.assertGreaterEqual(
            area_ids,
            {
                "cn_stock_tradeability",
                "financial_pit_timing",
                "industry_style_neutralization",
                "etf_rotation_scope_boundary",
                "portfolio_construction",
                "strict_statistics",
                "final_holdout_promotion_gate",
                "china_market_regime",
                "event_factors",
            },
        )

    def test_missing_controls_block_startup(self) -> None:
        packet = build_factor_mining_quality_gate(
            {
                "control_status": {
                    "limit_up_down_filter": "implemented",
                }
            }
        )

        self.assertEqual(packet["status"], "blocked")
        self.assertFalse(packet["decision"]["startup_gate_cleared"])
        self.assertIn("missing_quality_control:suspension_filter", packet["decision"]["blockers"])

    def test_planned_controls_clear_startup_but_block_promotion(self) -> None:
        statuses = {control_id: "planned" for control_id in required_control_ids()}

        packet = build_factor_mining_quality_gate(
            {
                "control_status": statuses,
                "control_next_actions": {
                    control_id: f"finish {control_id}" for control_id in required_control_ids()
                },
            }
        )

        self.assertEqual(packet["status"], "classified")
        self.assertTrue(packet["decision"]["startup_gate_cleared"])
        self.assertFalse(packet["decision"]["promotion_gate_cleared"])
        self.assertEqual(packet["summary"]["missing_controls"], 0)
        self.assertEqual(packet["summary"]["planned_controls"], len(statuses))
        self.assertIn("promotion_control_not_implemented:limit_up_down_filter", packet["decision"]["promotion_blockers"])
        policy = packet["research_execution_policy"]
        self.assertFalse(policy["direct_factor_generation_allowed"])
        self.assertTrue(policy["candidate_preregistration_allowed"])
        self.assertIn("quality_control_implementation", policy["allowed_next_work_modes"])
        self.assertIn("candidate_preregistration_without_profit_claims", policy["allowed_next_work_modes"])
        self.assertIn("direct_parameter_grid_mining", policy["blocked_next_work_modes"])
        self.assertIn(
            "direct_mining_control_not_implemented:limit_up_down_filter",
            policy["direct_mining_blockers"],
        )

    def test_implemented_controls_clear_promotion(self) -> None:
        statuses = {control_id: "implemented" for control_id in required_control_ids()}

        packet = build_factor_mining_quality_gate(
            {
                "control_status": statuses,
                "control_evidence": {
                    control_id: f"evidence {control_id}" for control_id in required_control_ids()
                },
            }
        )

        self.assertEqual(packet["status"], "promotion_ready")
        self.assertTrue(packet["decision"]["startup_gate_cleared"])
        self.assertTrue(packet["decision"]["promotion_gate_cleared"])
        self.assertEqual(packet["decision"]["promotion_blockers"], [])
        self.assertTrue(packet["research_execution_policy"]["direct_factor_generation_allowed"])
        self.assertEqual(packet["research_execution_policy"]["direct_mining_blockers"], [])

    def test_area_rows_include_control_evidence(self) -> None:
        statuses = {control_id: "planned" for control_id in required_control_ids()}

        packet = build_factor_mining_quality_gate(
            {
                "control_status": statuses,
                "control_evidence": {
                    "limit_up_down_filter": "known limit-path cleanup exists but general mask is planned"
                },
                "control_next_actions": {
                    control_id: f"finish {control_id}" for control_id in required_control_ids()
                },
            }
        )

        tradeability = next(area for area in packet["quality_areas"] if area["id"] == "cn_stock_tradeability")
        limit_control = next(row for row in tradeability["controls"] if row["control_id"] == "limit_up_down_filter")
        self.assertEqual(
            limit_control["evidence"],
            "known limit-path cleanup exists but general mask is planned",
        )
        self.assertEqual(limit_control["next_action"], "finish limit_up_down_filter")

    def test_research_execution_policy_can_exempt_controls_from_direct_mining(self) -> None:
        statuses = {control_id: "implemented" for control_id in required_control_ids()}
        statuses["cn_etf_dedicated_signal_pack_for_etf_rotation"] = "not_applicable"

        packet = build_factor_mining_quality_gate(
            {
                "control_status": statuses,
                "control_evidence": {
                    control_id: f"evidence {control_id}" for control_id in required_control_ids()
                },
            }
        )

        policy = packet["research_execution_policy"]
        self.assertTrue(policy["direct_factor_generation_allowed"])
        self.assertNotIn(
            "direct_mining_control_not_implemented:cn_etf_dedicated_signal_pack_for_etf_rotation",
            policy["direct_mining_blockers"],
        )

    def test_cn_etf_dedicated_signal_pack_does_not_block_cn_stock_direct_mining(self) -> None:
        statuses = {control_id: "implemented" for control_id in required_control_ids()}
        statuses["cn_etf_dedicated_signal_pack_for_etf_rotation"] = "planned"

        packet = build_factor_mining_quality_gate(
            {
                "control_status": statuses,
                "control_evidence": {
                    control_id: f"evidence {control_id}" for control_id in required_control_ids()
                },
                "control_next_actions": {
                    "cn_etf_dedicated_signal_pack_for_etf_rotation": "keep ETF work on a separate branch"
                },
            }
        )

        self.assertFalse(packet["decision"]["promotion_gate_cleared"])
        self.assertTrue(packet["research_execution_policy"]["direct_factor_generation_allowed"])
        self.assertNotIn(
            "direct_mining_control_not_implemented:cn_etf_dedicated_signal_pack_for_etf_rotation",
            packet["research_execution_policy"]["direct_mining_blockers"],
        )

    def test_partial_and_implemented_controls_require_evidence(self) -> None:
        statuses = {control_id: "planned" for control_id in required_control_ids()}
        statuses["limit_up_down_filter"] = "partial"
        next_actions = {control_id: f"finish {control_id}" for control_id in required_control_ids()}

        packet = build_factor_mining_quality_gate(
            {
                "control_status": statuses,
                "control_next_actions": next_actions,
            }
        )

        self.assertEqual(packet["status"], "blocked")
        self.assertFalse(packet["decision"]["startup_gate_cleared"])
        self.assertIn("missing_quality_control_evidence:limit_up_down_filter", packet["decision"]["blockers"])
        self.assertEqual(packet["summary"]["missing_evidence_controls"], 1)

    def test_partial_and_planned_controls_require_next_action(self) -> None:
        statuses = {control_id: "implemented" for control_id in required_control_ids()}
        statuses["risk_budget_position_sizing"] = "planned"
        evidence = {control_id: f"evidence {control_id}" for control_id in required_control_ids()}

        packet = build_factor_mining_quality_gate(
            {
                "control_status": statuses,
                "control_evidence": evidence,
            }
        )

        self.assertEqual(packet["status"], "blocked")
        self.assertFalse(packet["decision"]["startup_gate_cleared"])
        self.assertIn("missing_quality_control_next_action:risk_budget_position_sizing", packet["decision"]["blockers"])
        self.assertEqual(packet["summary"]["missing_next_action_controls"], 1)

    def test_validate_quality_gate_for_startup_rejects_missing_controls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "quality_gate.json"
            path.write_text(
                json.dumps(build_factor_mining_quality_gate({"control_status": {}})),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "quality gate is not cleared"):
                validate_quality_gate_for_startup(path)


if __name__ == "__main__":
    unittest.main()
