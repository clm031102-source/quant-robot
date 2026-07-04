import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts.run_project_completion_gate import (
    build_completion_gate,
    completion_gate_exit_code,
    discover_latest_observation_sufficiency_pack,
)


class ProjectCompletionGateTests(unittest.TestCase):
    def test_blocks_factor_mining_when_main_integration_or_observation_is_incomplete(self) -> None:
        gate = build_completion_gate(
            current_branch="codex/factor-batch-cn-stock-execution-aware-round465-20260704",
            stable_branch="main",
            changed_paths=[],
            remote_topic_branches=[
                {
                    "name": "origin/codex/factor-batch-cn-stock-benchmark-relative-20260704",
                    "commit": "abc123",
                },
                {
                    "name": "origin/codex/factor-batch-cn-stock-execution-aware-round465-20260704",
                    "commit": "def456",
                },
            ],
            branch_discovery_errors=[],
            observation_pack={
                "status": "needs_more_observation_data",
                "decision": {"observation_sufficiency_cleared": False},
                "fills": {"observed_fills": 5, "required_fills": 20, "fill_deficit": 15},
            },
        )

        self.assertEqual(gate["status"], "blocked")
        self.assertFalse(gate["factor_mining_allowed"])
        self.assertEqual(gate["progress_estimate_percent"], 98)
        self.assertEqual(
            gate["blockers"],
            [
                "not_on_stable_branch",
                "remote_topic_branches_remaining",
                "observation_sufficiency_not_cleared",
            ],
        )
        self.assertEqual(gate["observation"]["observed_fills"], 5)
        self.assertEqual(gate["observation"]["required_fills"], 20)
        self.assertEqual(gate["next_actions"][0]["action"], "run_laptop_project_sync")

    def test_allows_factor_mining_only_after_project_completion_conditions_clear(self) -> None:
        gate = build_completion_gate(
            current_branch="main",
            stable_branch="main",
            changed_paths=[],
            remote_topic_branches=[],
            branch_discovery_errors=[],
            observation_pack={
                "status": "sufficient",
                "decision": {"observation_sufficiency_cleared": True},
                "fills": {"observed_fills": 24, "required_fills": 20, "fill_deficit": 0},
            },
        )

        self.assertEqual(gate["status"], "complete")
        self.assertTrue(gate["factor_mining_allowed"])
        self.assertEqual(gate["progress_estimate_percent"], 100)
        self.assertEqual(gate["blockers"], [])
        self.assertEqual(gate["next_actions"][0]["action"], "start_profit_factor_mining")

    def test_require_complete_exit_code_blocks_automation_until_gate_clears(self) -> None:
        blocked_gate = {"factor_mining_allowed": False}
        complete_gate = {"factor_mining_allowed": True}

        self.assertEqual(completion_gate_exit_code(blocked_gate, require_complete=True), 2)
        self.assertEqual(completion_gate_exit_code(complete_gate, require_complete=True), 0)
        self.assertEqual(completion_gate_exit_code(blocked_gate, require_complete=False), 0)

    def test_discovers_latest_non_fixture_observation_sufficiency_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_pack = root / "round477_observation_sufficiency" / "observation_sufficiency_pack.json"
            latest_pack = root / "round478_observation_sufficiency" / "observation_sufficiency_pack.json"
            fixture_pack = root / "observation_sufficiency_fixture" / "observation_sufficiency_pack.json"
            for pack, observed_fills in [(old_pack, 2), (latest_pack, 5), (fixture_pack, 999)]:
                pack.parent.mkdir(parents=True, exist_ok=True)
                pack.write_text(
                    json.dumps(
                        {
                            "status": "needs_more_observation_data",
                            "decision": {"observation_sufficiency_cleared": False},
                            "fills": {"observed_fills": observed_fills, "required_fills": 20},
                        }
                    ),
                    encoding="utf-8",
                )
            os.utime(old_pack, (100.0, 100.0))
            os.utime(latest_pack, (200.0, 200.0))
            os.utime(fixture_pack, (300.0, 300.0))

            self.assertEqual(discover_latest_observation_sufficiency_pack(root), latest_pack)


if __name__ == "__main__":
    unittest.main()
