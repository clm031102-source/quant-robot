import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.factor_batch_readiness_gate import (
    build_factor_batch_readiness_gate,
    validate_factor_batch_readiness_gate_packet,
    write_factor_batch_readiness_gate,
)


class FactorBatchReadinessGateTests(unittest.TestCase):
    def test_blocks_when_source_queue_or_candidate_plan_gate_is_blocked(self) -> None:
        packet = build_factor_batch_readiness_gate(
            source_queue_packet={
                "decision": {
                    "status": "blocked",
                    "blockers": ["report_rc_quota_blocked"],
                    "next_action": "wait_for_report_rc_quota_reset_then_analyst_monthly_cache_preflight",
                },
                "summary": {"active_source_count": 1},
            },
            candidate_plan_gate_packet={
                "status": "blocked",
                "decision": {
                    "candidate_plan_gate_cleared": False,
                    "blockers": ["candidate_source_provider_not_allowed:analyst_report_revision"],
                },
                "summary": {"candidate_count": 4},
            },
            candidate_plan_path="configs/factor_mining_candidate_plan_round453_analyst_report_revision_20260627.json",
            source_queue_output_dir="data/reports/source_queue",
            candidate_plan_gate_output_dir="data/reports/candidate_gate",
        )

        self.assertEqual(packet["stage"], "factor_batch_readiness_gate")
        self.assertEqual(packet["status"], "blocked")
        self.assertFalse(packet["decision"]["factor_batch_ready"])
        self.assertFalse(packet["decision"]["research_screen_allowed"])
        self.assertIn("source_queue_blocked:report_rc_quota_blocked", packet["decision"]["blockers"])
        self.assertIn(
            "candidate_plan_gate_blocked:candidate_source_provider_not_allowed:analyst_report_revision",
            packet["decision"]["blockers"],
        )
        self.assertEqual(
            packet["decision"]["next_action"],
            "wait_for_report_rc_quota_reset_then_analyst_monthly_cache_preflight",
        )

    def test_clears_only_when_source_queue_and_candidate_plan_gate_clear(self) -> None:
        packet = build_factor_batch_readiness_gate(
            source_queue_packet={
                "decision": {
                    "status": "cleared",
                    "blockers": [],
                    "next_action": "analyst_monthly_cache_preflight_then_frozen_prescreen",
                },
                "summary": {"active_source_count": 1},
            },
            candidate_plan_gate_packet={
                "status": "research_ready",
                "decision": {
                    "candidate_plan_gate_cleared": True,
                    "research_screen_allowed": True,
                    "blockers": [],
                },
                "summary": {"candidate_count": 4},
            },
            candidate_plan_path="candidate_plan.json",
            source_queue_output_dir="source_queue",
            candidate_plan_gate_output_dir="candidate_gate",
        )

        self.assertEqual(packet["status"], "ready")
        self.assertTrue(packet["decision"]["factor_batch_ready"])
        self.assertTrue(packet["decision"]["research_screen_allowed"])
        self.assertEqual(packet["decision"]["blockers"], [])

    def test_blocks_when_provider_quota_preflight_is_blocked(self) -> None:
        packet = build_factor_batch_readiness_gate(
            source_queue_packet={
                "decision": {
                    "status": "cleared",
                    "blockers": [],
                    "next_action": "analyst_monthly_cache_preflight_then_frozen_prescreen",
                },
                "summary": {"active_source_count": 1},
            },
            candidate_plan_gate_packet={
                "status": "research_ready",
                "decision": {
                    "candidate_plan_gate_cleared": True,
                    "research_screen_allowed": True,
                    "blockers": [],
                },
                "summary": {"candidate_count": 4},
            },
            candidate_plan_path="candidate_plan.json",
            source_queue_output_dir="source_queue",
            candidate_plan_gate_output_dir="candidate_gate",
            provider_quota_preflight_packet={
                "decision": {
                    "request_allowed": False,
                    "blockers": ["daily_provider_request_budget_exhausted"],
                    "next_action": "collect_required_quota_pack_evidence",
                }
            },
        )

        self.assertEqual(packet["status"], "blocked")
        self.assertFalse(packet["decision"]["factor_batch_ready"])
        self.assertEqual(packet["summary"]["provider_quota_preflight_status"], "blocked")
        self.assertIn(
            "provider_quota_preflight_blocked:daily_provider_request_budget_exhausted",
            packet["decision"]["blockers"],
        )
        self.assertEqual(packet["decision"]["next_action"], "collect_required_quota_pack_evidence")

    def test_writer_outputs_json_and_markdown(self) -> None:
        packet = build_factor_batch_readiness_gate(
            source_queue_packet={"decision": {"status": "cleared", "blockers": []}, "summary": {}},
            candidate_plan_gate_packet={
                "status": "research_ready",
                "decision": {"candidate_plan_gate_cleared": True, "research_screen_allowed": True, "blockers": []},
                "summary": {},
            },
            candidate_plan_path="candidate_plan.json",
            source_queue_output_dir="source_queue",
            candidate_plan_gate_output_dir="candidate_gate",
        )

        with tempfile.TemporaryDirectory() as tmp:
            write_factor_batch_readiness_gate(tmp, packet)
            root = Path(tmp)
            payload = json.loads((root / "factor_batch_readiness_gate.json").read_text(encoding="utf-8"))
            self.assertTrue((root / "factor_batch_readiness_gate.md").exists())

        self.assertEqual(payload["status"], "ready")

    def test_validate_factor_batch_readiness_packet_requires_ready_gate(self) -> None:
        ready_packet = build_factor_batch_readiness_gate(
            source_queue_packet={"decision": {"status": "cleared", "blockers": []}, "summary": {}},
            candidate_plan_gate_packet={
                "status": "research_ready",
                "decision": {"candidate_plan_gate_cleared": True, "research_screen_allowed": True, "blockers": []},
                "summary": {},
            },
            candidate_plan_path="candidate_plan.json",
            source_queue_output_dir="source_queue",
            candidate_plan_gate_output_dir="candidate_gate",
        )
        blocked_packet = build_factor_batch_readiness_gate(
            source_queue_packet={
                "decision": {"status": "blocked", "blockers": ["report_rc_quota_blocked"]},
                "summary": {},
            },
            candidate_plan_gate_packet={
                "status": "blocked",
                "decision": {
                    "candidate_plan_gate_cleared": False,
                    "blockers": ["candidate_source_provider_not_allowed"],
                },
                "summary": {},
            },
            candidate_plan_path="candidate_plan.json",
            source_queue_output_dir="source_queue",
            candidate_plan_gate_output_dir="candidate_gate",
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ready_dir = root / "ready"
            blocked_dir = root / "blocked"
            write_factor_batch_readiness_gate(ready_dir, ready_packet)
            write_factor_batch_readiness_gate(blocked_dir, blocked_packet)

            loaded = validate_factor_batch_readiness_gate_packet(ready_dir / "factor_batch_readiness_gate.json")
            with self.assertRaisesRegex(ValueError, "factor batch readiness gate is not ready"):
                validate_factor_batch_readiness_gate_packet(blocked_dir / "factor_batch_readiness_gate.json")

        self.assertEqual(loaded["status"], "ready")
        self.assertTrue(loaded["decision"]["factor_batch_ready"])


if __name__ == "__main__":
    unittest.main()
