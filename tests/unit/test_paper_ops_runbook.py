import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.paper_ops_runbook import build_paper_ops_runbook_pack, write_paper_ops_runbook_pack


class PaperOpsRunbookTests(unittest.TestCase):
    def test_runbook_builds_ordered_paper_cycle_when_guardrail_allows_continuation(self):
        guardrail = _guardrail_pack(
            status="paper_ops_watch",
            continued=True,
            live_candidate=False,
            blockers=[],
            warnings=["short_paper_history", "provider_missing_date_rows"],
        )

        pack = build_paper_ops_runbook_pack(guardrail)

        self.assertEqual(pack["stage"], "phase_5_15_paper_ops_runbook")
        self.assertEqual(pack["status"], "paper_cycle_ready")
        self.assertTrue(pack["decision"]["paper_cycle_allowed"])
        self.assertFalse(pack["decision"]["live_cycle_allowed"])
        self.assertEqual(pack["decision"]["blockers"], [])
        self.assertEqual(pack["summary"]["command_count"], 4)
        self.assertEqual(
            [row["action"] for row in pack["command_queue"]],
            [
                "check_tushare_readiness",
                "run_tushare_activation_gate",
                "update_paper_observation_history",
                "update_paper_ops_guardrail",
            ],
        )
        self.assertTrue(all(row["local_only"] for row in pack["command_queue"]))
        self.assertTrue(all(not row["live_boundary_allowed"] for row in pack["command_queue"]))
        self.assertIn("--execute", pack["command_queue"][1]["command"])
        self.assertFalse(pack["live_boundary_allowed"])

    def test_runbook_blocks_command_queue_when_guardrail_is_blocked(self):
        guardrail = _guardrail_pack(
            status="paper_ops_blocked",
            continued=False,
            live_candidate=False,
            blockers=["history_not_clear"],
            warnings=[],
        )

        pack = build_paper_ops_runbook_pack(guardrail)

        self.assertEqual(pack["status"], "paper_cycle_blocked")
        self.assertFalse(pack["decision"]["paper_cycle_allowed"])
        self.assertEqual(pack["decision"]["blockers"], ["history_not_clear"])
        self.assertEqual([row["action"] for row in pack["command_queue"]], ["inspect_paper_ops_guardrail_blockers"])

    def test_write_runbook_pack_outputs_artifacts(self):
        pack = build_paper_ops_runbook_pack(_guardrail_pack())
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)

            write_paper_ops_runbook_pack(output_dir, pack)

            self.assertTrue((output_dir / "paper_ops_runbook_pack.json").exists())
            self.assertTrue((output_dir / "paper_ops_runbook_pack.md").exists())
            self.assertTrue((output_dir / "paper_ops_runbook_commands.csv").exists())


def _guardrail_pack(
    *,
    status: str = "paper_ops_watch",
    continued: bool = True,
    live_candidate: bool = False,
    blockers: list[str] | None = None,
    warnings: list[str] | None = None,
) -> dict:
    return {
        "stage": "phase_5_14_paper_ops_guardrail",
        "status": status,
        "decision": {
            "continued_paper_observation_allowed": continued,
            "live_readiness_candidate": live_candidate,
            "blockers": blockers or [],
            "warnings": warnings or [],
        },
        "summary": {
            "history_run_count": 1,
            "paper_observation_ready_runs": 1,
            "ready_run_deficit_for_live_readiness": 19,
            "latest_required_assets": ["CN_ETF_XSHG_516160"],
            "latest_provider_missing_date_rows": 226,
        },
        "live_boundary_allowed": False,
    }


if __name__ == "__main__":
    unittest.main()
