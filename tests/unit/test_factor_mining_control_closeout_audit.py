import unittest

from quant_robot.ops.factor_mining_control_closeout_audit import build_factor_mining_control_closeout_audit
from quant_robot.ops.factor_mining_quality_gate import build_factor_mining_quality_gate, required_control_ids


def _quality_gate_packet() -> dict:
    controls = required_control_ids()
    statuses = {control_id: "implemented" for control_id in controls}
    statuses.update(
        {
            "limit_up_down_filter": "partial",
            "suspension_filter": "partial",
            "financial_revision_announcement_handling": "planned",
            "risk_budget_position_sizing": "planned",
            "cn_etf_dedicated_signal_pack_for_etf_rotation": "planned",
        }
    )
    evidence = {control_id: f"evidence {control_id}" for control_id in controls}
    next_actions = {
        "limit_up_down_filter": "Add official daily limit/suspend fields.",
        "suspension_filter": "Backfill an official suspension/status feed.",
        "financial_revision_announcement_handling": "Add revision-aware handling.",
        "risk_budget_position_sizing": "Add portfolio sizing policies.",
        "cn_etf_dedicated_signal_pack_for_etf_rotation": "Keep ETF signal work separate.",
    }
    return build_factor_mining_quality_gate(
        {
            "control_status": statuses,
            "control_evidence": evidence,
            "control_next_actions": next_actions,
        }
    )


class FactorMiningControlCloseoutAuditTests(unittest.TestCase):
    def test_prioritizes_direct_mining_blockers_from_quality_gate_policy(self) -> None:
        packet = build_factor_mining_control_closeout_audit(_quality_gate_packet())

        self.assertEqual(packet["stage"], "factor_mining_control_closeout_audit")
        self.assertEqual(packet["status"], "direct_mining_blocked")
        self.assertFalse(packet["decision"]["direct_factor_generation_allowed"])
        self.assertEqual(packet["summary"]["direct_mining_blocker_count"], 4)
        self.assertGreaterEqual(packet["summary"]["priority_count"], 4)
        self.assertEqual(packet["priority_rows"][0]["control_id"], "limit_up_down_filter")
        self.assertEqual(packet["priority_rows"][0]["area_id"], "cn_stock_tradeability")
        self.assertEqual(packet["priority_rows"][0]["action_type"], "data_readiness_audit")
        self.assertEqual(
            packet["decision"]["next_round_direction"],
            "round198_continue_long_cycle_tradeability_backfill_until_manifest_coverage_then_mask_integration",
        )

    def test_scope_exempt_etf_signal_pack_is_not_direct_mining_priority(self) -> None:
        packet = build_factor_mining_control_closeout_audit(_quality_gate_packet())

        control_ids = {row["control_id"] for row in packet["priority_rows"]}
        self.assertNotIn("cn_etf_dedicated_signal_pack_for_etf_rotation", control_ids)
        self.assertIn("cn_etf_dedicated_signal_pack_for_etf_rotation", packet["scope_exempt_controls"])

    def test_ready_quality_gate_allows_direct_factor_generation(self) -> None:
        controls = required_control_ids()
        packet = build_factor_mining_quality_gate(
            {
                "control_status": {control_id: "implemented" for control_id in controls},
                "control_evidence": {control_id: f"evidence {control_id}" for control_id in controls},
            }
        )

        audit = build_factor_mining_control_closeout_audit(packet)

        self.assertEqual(audit["status"], "direct_mining_ready")
        self.assertTrue(audit["decision"]["direct_factor_generation_allowed"])
        self.assertEqual(audit["priority_rows"], [])
        self.assertEqual(audit["decision"]["next_round_direction"], "direct_factor_generation_allowed_after_control_closeout")


if __name__ == "__main__":
    unittest.main()
