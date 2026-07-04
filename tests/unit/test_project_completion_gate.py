import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts.run_project_completion_gate import (
    build_completion_gate,
    completion_gate_exit_code,
    discover_latest_recent_data_refresh_pack,
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

    def test_progress_reaches_99_when_only_mainline_git_integration_remains(self) -> None:
        gate = build_completion_gate(
            current_branch="codex/factor-batch-current",
            stable_branch="main",
            changed_paths=[],
            remote_topic_branches=[{"name": "origin/codex/factor-batch-current", "commit": "abc123"}],
            branch_discovery_errors=[],
            observation_pack={
                "status": "sufficient",
                "decision": {"observation_sufficiency_cleared": True},
                "fills": {"observed_fills": 25, "required_fills": 20, "fill_deficit": 0},
            },
            recent_data_refresh_pack={"status": "completed", "coverage": {"target_end_covered": True}},
        )

        self.assertEqual(gate["progress_estimate_percent"], 99)
        self.assertEqual(gate["blockers"], ["not_on_stable_branch", "remote_topic_branches_remaining"])

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

    def test_discovery_prefers_stronger_observation_evidence_over_newer_diagnostic_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stronger_pack = root / "round478_observation_sufficiency_validated_latest" / "observation_sufficiency_pack.json"
            diagnostic_pack = root / "round487_observation_sufficiency" / "observation_sufficiency_pack.json"
            sufficient_pack = root / "round488_observation_sufficiency_validated" / "observation_sufficiency_pack.json"
            for pack, status, cleared, observed_fills, timestamp in [
                (stronger_pack, "needs_more_observation_data", False, 5, 100.0),
                (diagnostic_pack, "needs_more_observation_data", False, 1, 300.0),
                (sufficient_pack, "sufficient", True, 20, 200.0),
            ]:
                pack.parent.mkdir(parents=True, exist_ok=True)
                pack.write_text(
                    json.dumps(
                        {
                            "status": status,
                            "decision": {"observation_sufficiency_cleared": cleared},
                            "fills": {"observed_fills": observed_fills, "required_fills": 20},
                        }
                    ),
                    encoding="utf-8",
                )
                os.utime(pack, (timestamp, timestamp))

            self.assertEqual(discover_latest_observation_sufficiency_pack(root), sufficient_pack)
            sufficient_pack.unlink()
            self.assertEqual(discover_latest_observation_sufficiency_pack(root), stronger_pack)

    def test_discovery_prefers_validated_repaired_evidence_over_legacy_higher_fill_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy_pack = root / "round472_observation_sufficiency" / "observation_sufficiency_pack.json"
            validated_pack = (
                root
                / "round478_observation_sufficiency_validated_latest"
                / "observation_sufficiency_pack.json"
            )
            for pack, observed_fills, timestamp in [
                (legacy_pack, 6, 300.0),
                (validated_pack, 5, 200.0),
            ]:
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
                os.utime(pack, (timestamp, timestamp))

            self.assertEqual(discover_latest_observation_sufficiency_pack(root), validated_pack)

    def test_discovery_prefers_sufficient_pack_over_validated_incomplete_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            validated_incomplete = (
                root
                / "round478_observation_sufficiency_validated_latest"
                / "observation_sufficiency_pack.json"
            )
            sufficient_pack = root / "round501_observation_sufficiency" / "observation_sufficiency_pack.json"
            for pack, status, cleared, observed_fills, timestamp in [
                (validated_incomplete, "needs_more_observation_data", False, 5, 200.0),
                (sufficient_pack, "sufficient", True, 25, 100.0),
            ]:
                pack.parent.mkdir(parents=True, exist_ok=True)
                pack.write_text(
                    json.dumps(
                        {
                            "status": status,
                            "decision": {"observation_sufficiency_cleared": cleared},
                            "fills": {"observed_fills": observed_fills, "required_fills": 20},
                        }
                    ),
                    encoding="utf-8",
                )
                os.utime(pack, (timestamp, timestamp))

            self.assertEqual(discover_latest_observation_sufficiency_pack(root), sufficient_pack)

    def test_discovery_falls_back_to_tracked_docs_evidence_when_data_reports_are_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            reports_root = workspace / "data" / "reports"
            docs_root = workspace / "docs" / "research"
            reports_root.mkdir(parents=True)
            docs_root.mkdir(parents=True)
            evidence_pack = docs_root / "project_round501_completion_evidence_2026-07-04.json"
            evidence_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_9_observation_sufficiency",
                        "status": "sufficient",
                        "decision": {"observation_sufficiency_cleared": True},
                        "fills": {"observed_fills": 25, "required_fills": 20, "fill_deficit": 0},
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(discover_latest_observation_sufficiency_pack(reports_root), evidence_pack)

    def test_completion_gate_surfaces_required_asset_target_end_gap_next_action(self) -> None:
        gate = build_completion_gate(
            current_branch="main",
            stable_branch="main",
            changed_paths=[],
            remote_topic_branches=[],
            branch_discovery_errors=[],
            observation_pack={
                "status": "needs_more_observation_data",
                "decision": {"observation_sufficiency_cleared": False},
                "fills": {"observed_fills": 5, "required_fills": 20, "fill_deficit": 15},
            },
            recent_data_refresh_pack={
                "status": "data_quality_blocked",
                "target_window": {"start_date": "2026-05-06", "end_date": "2026-07-03"},
                "coverage": {
                    "target_start_covered": True,
                    "target_end_covered": False,
                    "required_asset_coverage": [
                        {
                            "asset_id": "CN_ETF_XSHE_160615",
                            "target_start_covered": True,
                            "target_end_covered": False,
                            "end_date": "2026-07-02",
                        }
                    ],
                },
            },
            recent_data_refresh_pack_path="data/reports/round491/recent_data_refresh_pack.json",
        )

        self.assertEqual(gate["blockers"], ["observation_sufficiency_not_cleared"])
        self.assertEqual(
            gate["recent_data_refresh"]["target_end_gap"],
            {
                "source_path": "data/reports/round491/recent_data_refresh_pack.json",
                "target_start_date": "2026-05-06",
                "target_end_date": "2026-07-03",
                "latest_clean_end_date": "2026-07-02",
                "required_asset_ids": ["CN_ETF_XSHE_160615"],
            },
        )
        self.assertEqual(gate["next_actions"][0]["action"], "wait_for_required_asset_target_end")
        self.assertIn("scripts/run_required_asset_target_end_check.py", gate["next_actions"][0]["command"])
        self.assertIn("CN_ETF_XSHE_160615", gate["next_actions"][0]["reason"])
        self.assertIn("2026-07-03", gate["next_actions"][0]["reason"])
        self.assertNotIn("continue_paper_observation", [row["action"] for row in gate["next_actions"]])

    def test_discovers_latest_non_fixture_recent_data_refresh_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_pack = root / "round490_recent_data_refresh" / "recent_data_refresh_pack.json"
            latest_pack = root / "round491_recent_data_refresh" / "recent_data_refresh_pack.json"
            fixture_pack = root / "recent_data_refresh_fixture" / "recent_data_refresh_pack.json"
            for pack, timestamp in [(old_pack, 100.0), (latest_pack, 200.0), (fixture_pack, 300.0)]:
                pack.parent.mkdir(parents=True, exist_ok=True)
                pack.write_text(
                    json.dumps(
                        {
                            "status": "data_quality_blocked",
                            "target_window": {"start_date": "2026-05-06", "end_date": "2026-07-03"},
                        }
                    ),
                    encoding="utf-8",
                )
                os.utime(pack, (timestamp, timestamp))

            self.assertEqual(discover_latest_recent_data_refresh_pack(root), latest_pack)


if __name__ == "__main__":
    unittest.main()
