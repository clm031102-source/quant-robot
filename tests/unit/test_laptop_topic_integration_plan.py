import unittest
from types import SimpleNamespace

from scripts.run_laptop_topic_integration_plan import (
    build_laptop_topic_integration_plan,
    execute_laptop_topic_integration_plan,
    plan_handoff_ready,
)


class LaptopTopicIntegrationPlanTests(unittest.TestCase):
    def test_plan_orders_ancestor_branch_before_descendant_and_emits_finish_commands(self) -> None:
        branches = [
            {"name": "origin/codex/factor-batch-current", "commit": "new"},
            {"name": "origin/codex/factor-batch-benchmark", "commit": "old"},
        ]

        plan = build_laptop_topic_integration_plan(
            machine="laptop",
            task="project_sync",
            current_branch="main",
            worktree_clean=True,
            main_upstream_sync="0\t0",
            remote_topic_branches=branches,
            stable_commits=set(),
            manifest={"absorbed_branches": [], "ignored_branches": []},
            is_ancestor=lambda ancestor, descendant: ancestor == "old" and descendant == "new",
            python_executable="python",
        )

        self.assertEqual(plan["status"], "ready")
        self.assertEqual(plan["blockers"], [])
        self.assertEqual(plan["handoff"]["blockers"], [])
        self.assertEqual(plan["handoff"]["blocker_count"], 0)
        self.assertEqual(plan["handoff"]["status"], "ready")
        self.assertTrue(plan["handoff"]["ready_for_handoff"])
        self.assertTrue(plan["handoff"]["executable_here"])
        self.assertTrue(plan["handoff"]["next_command_allowed_here"])
        self.assertEqual(plan["handoff"]["recommended_command"], plan["handoff"]["next_command"])
        self.assertEqual(plan["handoff"]["recommended_command_action"], "execute_integration")
        self.assertEqual(
            [item["branch"] for item in plan["merge_order"]],
            [
                "origin/codex/factor-batch-benchmark",
                "origin/codex/factor-batch-current",
            ],
        )
        self.assertEqual(
            plan["commands"],
            [
                ["git", "fetch", "origin", "--prune"],
                ["git", "checkout", "main"],
                ["git", "pull", "--ff-only", "origin", "main"],
                [
                    "git",
                    "merge",
                    "--no-ff",
                    "-m",
                    "Merge origin/codex/factor-batch-benchmark for project sync",
                    "origin/codex/factor-batch-benchmark",
                ],
                [
                    "git",
                    "merge",
                    "--no-ff",
                    "-m",
                    "Merge origin/codex/factor-batch-current for project sync",
                    "origin/codex/factor-batch-current",
                ],
                ["python", "scripts/run_checks.py", "--profile", "laptop-integration", "--execute"],
                ["git", "push", "origin", "main"],
                [
                    "python",
                    "scripts/sync_project.py",
                    "--machine",
                    "laptop",
                    "--task",
                    "project_sync",
                    "--execute",
                    "--cleanup-topic-branches",
                ],
                ["python", "scripts/run_checks.py", "--profile", "pre-alpha", "--execute"],
            ],
        )

    def test_plan_blocks_when_not_laptop_main_project_sync_or_clean(self) -> None:
        plan = build_laptop_topic_integration_plan(
            machine="office_desktop",
            task="factor_batch",
            current_branch="codex/factor-batch-current",
            worktree_clean=False,
            main_upstream_sync="1\t0",
            remote_topic_branches=[{"name": "origin/codex/factor-batch-current", "commit": "new"}],
            stable_commits=set(),
            manifest={"absorbed_branches": [], "ignored_branches": []},
            is_ancestor=lambda ancestor, descendant: False,
            python_executable="python",
        )

        self.assertEqual(plan["status"], "blocked")
        self.assertEqual(
            plan["blockers"],
            [
                "machine_must_be_laptop",
                "task_must_be_project_sync",
                "current_branch_must_be_main",
                "working_tree_dirty",
                "main_behind_origin_pull_first",
            ],
        )
        self.assertEqual(plan["handoff"]["blockers"], plan["blockers"])
        self.assertEqual(plan["handoff"]["blocker_count"], 5)
        self.assertFalse(plan["handoff"]["ready_for_handoff"])
        self.assertIsNone(plan["handoff"]["recommended_command"])
        self.assertEqual(plan["handoff"]["recommended_command_action"], "resolve_blockers")

    def test_plan_marks_topic_branch_handoff_ready_on_main_when_only_branch_blocks(self) -> None:
        plan = build_laptop_topic_integration_plan(
            machine="laptop",
            task="project_sync",
            current_branch="codex/factor-batch-current",
            worktree_clean=True,
            main_upstream_sync="0\t0",
            remote_topic_branches=[{"name": "origin/codex/factor-batch-current", "commit": "new"}],
            stable_commits=set(),
            manifest={"absorbed_branches": [], "ignored_branches": []},
            is_ancestor=lambda ancestor, descendant: False,
            python_executable="python",
        )

        self.assertEqual(plan["status"], "blocked")
        self.assertEqual(plan["blockers"], ["current_branch_must_be_main"])
        self.assertEqual(plan["handoff"]["blockers"], ["current_branch_must_be_main"])
        self.assertEqual(plan["handoff"]["blocker_count"], 1)
        self.assertEqual(plan["handoff"]["status"], "ready_on_main")
        self.assertTrue(plan["handoff"]["ready_for_handoff"])
        self.assertEqual(plan["handoff"]["required_machine"], "laptop")
        self.assertEqual(plan["handoff"]["required_task"], "project_sync")
        self.assertEqual(plan["handoff"]["required_branch"], "main")
        self.assertTrue(plan["handoff"]["rerun_plan_before_execute"])
        self.assertEqual(plan["handoff"]["merge_order_count"], 1)
        self.assertEqual(
            plan["handoff"]["next_command"],
            "python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --execute",
        )
        self.assertEqual(plan["handoff"]["next_command_context"], "laptop main only")
        self.assertFalse(plan["handoff"]["next_command_allowed_here"])
        self.assertEqual(
            plan["handoff"]["here_command"],
            "python scripts/run_laptop_topic_integration_plan.py --machine laptop --task project_sync --require-handoff-ready",
        )
        self.assertEqual(plan["handoff"]["recommended_command"], plan["handoff"]["here_command"])
        self.assertEqual(plan["handoff"]["recommended_command_action"], "check_handoff_ready")
        self.assertFalse(plan["handoff"]["executable_here"])
        self.assertEqual(
            plan["handoff"]["status_description"],
            "handoff-ready only; rerun from laptop on main before executing",
        )

    def test_plan_skips_stable_and_manifest_absorbed_topic_branches(self) -> None:
        plan = build_laptop_topic_integration_plan(
            machine="laptop",
            task="project_sync",
            current_branch="main",
            worktree_clean=True,
            main_upstream_sync="0\t0",
            remote_topic_branches=[
                {"name": "origin/codex/already-merged", "commit": "merged"},
                {"name": "origin/codex/absorbed", "commit": "absorbed"},
                {"name": "origin/codex/pending", "commit": "pending"},
            ],
            stable_commits={"merged"},
            manifest={
                "absorbed_branches": [
                    {
                        "branch": "origin/codex/absorbed",
                        "commit": "absorbed",
                        "status": "absorbed",
                    }
                ],
                "ignored_branches": [],
            },
            is_ancestor=lambda ancestor, descendant: False,
            python_executable="python",
        )

        self.assertEqual(plan["status"], "ready")
        self.assertEqual([item["branch"] for item in plan["merge_order"]], ["origin/codex/pending"])
        self.assertEqual(
            plan["skipped"],
            [
                {
                    "branch": "origin/codex/absorbed",
                    "commit": "absorbed",
                    "reason": "absorbed_by_manifest",
                },
                {
                    "branch": "origin/codex/already-merged",
                    "commit": "merged",
                    "reason": "already_in_stable",
                },
            ],
        )

    def test_plan_marks_no_topic_branches_not_ready_for_handoff(self) -> None:
        plan = build_laptop_topic_integration_plan(
            machine="laptop",
            task="project_sync",
            current_branch="main",
            worktree_clean=True,
            main_upstream_sync="0\t0",
            remote_topic_branches=[],
            stable_commits=set(),
            manifest={"absorbed_branches": [], "ignored_branches": []},
            is_ancestor=lambda ancestor, descendant: False,
            python_executable="python",
        )

        self.assertEqual(plan["status"], "no_topic_branches")
        self.assertFalse(plan["handoff"]["ready_for_handoff"])

    def test_execute_runs_ready_plan_commands_and_accepts_pre_alpha_block_exit(self) -> None:
        plan = {
            "status": "ready",
            "commands": [
                ["git", "fetch", "origin", "--prune"],
                ["python", "scripts/run_checks.py", "--profile", "pre-alpha", "--execute"],
            ],
        }
        calls: list[list[str]] = []

        def runner(command: list[str]):
            calls.append(command)
            return SimpleNamespace(returncode=2 if "--profile" in command and "pre-alpha" in command else 0)

        result = execute_laptop_topic_integration_plan(plan, command_runner=runner)

        self.assertEqual(result["status"], "executed")
        self.assertEqual(result["failed_command"], None)
        self.assertEqual(calls, plan["commands"])
        self.assertEqual([row["returncode"] for row in result["commands"]], [0, 2])

    def test_execute_refuses_blocked_plan_without_running_commands(self) -> None:
        calls: list[list[str]] = []
        plan = {"status": "blocked", "blockers": ["current_branch_must_be_main"], "commands": [["git", "fetch"]]}

        result = execute_laptop_topic_integration_plan(plan, command_runner=lambda command: calls.append(command))

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["blockers"], ["current_branch_must_be_main"])
        self.assertEqual(calls, [])

    def test_plan_handoff_ready_accepts_ready_on_main_or_ready_plan_only(self) -> None:
        self.assertTrue(plan_handoff_ready({"status": "ready", "handoff": {"status": "ready"}}))
        self.assertTrue(plan_handoff_ready({"status": "blocked", "handoff": {"status": "ready_on_main"}}))
        self.assertFalse(plan_handoff_ready({"status": "blocked", "handoff": {"status": "blocked"}}))
        self.assertFalse(plan_handoff_ready({"status": "no_topic_branches", "handoff": {"status": "no_topic_branches"}}))


if __name__ == "__main__":
    unittest.main()
