import unittest

from scripts.sync_project import (
    audit_local_topic_branches,
    audit_remote_research_branches,
    audit_remote_topic_branches,
    build_sync_plan,
    classify_changed_paths,
    is_forbidden_path,
    should_push_existing_commits,
)


class SyncProjectTests(unittest.TestCase):
    def test_classifies_code_docs_and_configs_as_syncable(self) -> None:
        config = _config()

        result = classify_changed_paths(
            [
                "src/quant_robot/factors/example.py",
                "scripts/run_example.py",
                "configs/example.json",
                "tests/unit/test_example.py",
                "docs/example.md",
                "README.md",
                "AGENTS.md",
            ],
            config,
        )

        self.assertEqual(
            result["syncable"],
            [
                "src/quant_robot/factors/example.py",
                "scripts/run_example.py",
                "configs/example.json",
                "tests/unit/test_example.py",
                "docs/example.md",
                "README.md",
                "AGENTS.md",
            ],
        )
        self.assertEqual(result["blocked"], [])

    def test_blocks_data_tokens_logs_and_large_outputs(self) -> None:
        config = _config()

        result = classify_changed_paths(
            [
                "data/raw/tushare.csv",
                "data/processed/bars.parquet",
                "data/reports/alpha/leaderboard.csv",
                ".env",
                ".env.local",
                "run.log",
                "output/model.parquet",
            ],
            config,
        )

        self.assertEqual(result["syncable"], [])
        self.assertEqual(
            result["blocked"],
            [
                "data/raw/tushare.csv",
                "data/processed/bars.parquet",
                "data/reports/alpha/leaderboard.csv",
                ".env",
                ".env.local",
                "run.log",
                "output/model.parquet",
            ],
        )

    def test_env_example_is_allowed_but_real_env_files_are_forbidden(self) -> None:
        config = _config()

        self.assertFalse(is_forbidden_path(".env.example", config))
        self.assertTrue(is_forbidden_path(".env", config))
        self.assertTrue(is_forbidden_path(".env.production", config))

    def test_execute_plan_blocks_when_machine_or_task_is_missing(self) -> None:
        plan = build_sync_plan(
            _config(),
            current_branch="codex/factor-batch-moneyflow-alpha",
            changed_paths=["src/quant_robot/factors/example.py"],
            machine=None,
            task="factor_batch",
            execute=True,
            push=True,
            upstream_sync="0\t0",
        )

        self.assertFalse(plan["can_execute"])
        self.assertIn("machine_not_confirmed", plan["blockers"])

    def test_execute_plan_blocks_main_for_non_project_sync_task(self) -> None:
        plan = build_sync_plan(
            _config(),
            current_branch="main",
            changed_paths=["src/quant_robot/factors/example.py"],
            machine="laptop",
            task="factor_batch",
            execute=True,
            push=True,
            upstream_sync="0\t0",
        )

        self.assertFalse(plan["can_execute"])
        self.assertIn("main_requires_project_sync_or_manual_confirmation", plan["blockers"])

    def test_execute_plan_allows_clean_task_branch_with_syncable_files(self) -> None:
        plan = build_sync_plan(
            _config(),
            current_branch="codex/factor-batch-moneyflow-alpha",
            changed_paths=["src/quant_robot/factors/example.py", "docs/example.md"],
            machine="office_desktop",
            task="factor_batch",
            execute=True,
            push=True,
            upstream_sync="0\t0",
        )

        self.assertTrue(plan["can_execute"])
        self.assertEqual(plan["blockers"], [])
        self.assertEqual(plan["path_classification"]["blocked"], [])

    def test_reports_unabsorbed_remote_research_branch(self) -> None:
        pending = audit_remote_research_branches(
            [
                {"name": "origin/codex/factor-batch-moneyflow-alpha", "commit": "abc123"},
                {"name": "origin/main", "commit": "def456"},
            ],
            {"absorbed_branches": []},
            current_commits=set(),
        )

        self.assertEqual(
            pending,
            [
                {
                    "branch": "origin/codex/factor-batch-moneyflow-alpha",
                    "commit": "abc123",
                    "status": "pending_integration",
                }
            ],
        )

    def test_absorbed_remote_research_branch_is_not_pending(self) -> None:
        pending = audit_remote_research_branches(
            [{"name": "origin/codex/factor-batch-moneyflow-alpha", "commit": "abc123"}],
            {
                "absorbed_branches": [
                    {
                        "branch": "origin/codex/factor-batch-moneyflow-alpha",
                        "commit": "abc123",
                        "status": "absorbed",
                    }
                ]
            },
            current_commits=set(),
        )

        self.assertEqual(pending, [])

    def test_execute_plan_blocks_core_sync_when_research_branch_is_pending(self) -> None:
        plan = build_sync_plan(
            _config(),
            current_branch="codex/project-audit-2026-06-16",
            changed_paths=["src/quant_robot/factors/example.py"],
            machine="laptop",
            task="architecture_ops",
            execute=True,
            push=True,
            upstream_sync="0\t0",
            pending_research_branches=[
                {
                    "branch": "origin/codex/factor-batch-moneyflow-alpha",
                    "commit": "abc123",
                    "status": "pending_integration",
                }
            ],
        )

        self.assertFalse(plan["can_execute"])
        self.assertIn("pending_research_branches_require_integration", plan["blockers"])

    def test_reports_unabsorbed_remote_nonresearch_topic_branch(self) -> None:
        audit = audit_remote_topic_branches(
            [
                {"name": "origin/codex/profile-daily-ops-activation-2026-06-16", "commit": "abc123"},
                {"name": "origin/codex/factor-batch-moneyflow-alpha", "commit": "def456"},
                {"name": "origin/main", "commit": "main123"},
            ],
            {"absorbed_branches": []},
            current_commits=set(),
        )

        self.assertEqual(
            audit["pending"],
            [
                {
                    "branch": "origin/codex/profile-daily-ops-activation-2026-06-16",
                    "commit": "abc123",
                    "status": "pending_integration",
                }
            ],
        )
        self.assertEqual(audit["cleanup"], [])

    def test_reports_merged_or_absorbed_topic_branches_for_cleanup(self) -> None:
        audit = audit_remote_topic_branches(
            [
                {"name": "origin/codex/recent-refresh-handoff-2026-06-16", "commit": "abc123"},
                {"name": "origin/codex/profile-daily-ops-activation-2026-06-16", "commit": "def456"},
            ],
            {
                "absorbed_branches": [
                    {
                        "branch": "origin/codex/profile-daily-ops-activation-2026-06-16",
                        "commit": "def456",
                        "status": "absorbed",
                    }
                ]
            },
            current_commits={"abc123"},
        )

        self.assertEqual(audit["pending"], [])
        self.assertEqual(
            audit["cleanup"],
            [
                {
                    "branch": "origin/codex/profile-daily-ops-activation-2026-06-16",
                    "commit": "def456",
                    "status": "absorbed_by_manifest",
                },
                {
                    "branch": "origin/codex/recent-refresh-handoff-2026-06-16",
                    "commit": "abc123",
                    "status": "merged_to_stable_branch",
                },
            ],
        )

    def test_reports_local_merged_topic_branches_for_cleanup(self) -> None:
        cleanup = audit_local_topic_branches(
            [
                {"name": "codex/old-audit-branch", "commit": "abc123"},
                {"name": "codex/current-work", "commit": "def456"},
                {"name": "main", "commit": "main123"},
            ],
            current_branch="codex/current-work",
            stable_commits={"abc123", "def456"},
        )

        self.assertEqual(
            cleanup,
            [
                {
                    "branch": "codex/old-audit-branch",
                    "commit": "abc123",
                    "status": "merged_to_stable_branch",
                }
            ],
        )

    def test_execute_plan_blocks_core_sync_when_topic_branch_is_pending(self) -> None:
        plan = build_sync_plan(
            _config(),
            current_branch="codex/project-audit-2026-06-16",
            changed_paths=["scripts/run_daily_ops.py"],
            machine="laptop",
            task="architecture_ops",
            execute=True,
            push=True,
            upstream_sync="0\t0",
            pending_topic_branches=[
                {
                    "branch": "origin/codex/profile-daily-ops-activation-2026-06-16",
                    "commit": "abc123",
                    "status": "pending_integration",
                }
            ],
        )

        self.assertFalse(plan["can_execute"])
        self.assertIn("pending_topic_branches_require_integration", plan["blockers"])

    def test_execute_plan_allows_factor_batch_to_publish_pending_research_branch(self) -> None:
        plan = build_sync_plan(
            _config(),
            current_branch="codex/factor-batch-new-idea",
            changed_paths=["src/quant_robot/factors/example.py"],
            machine="office_desktop",
            task="factor_batch",
            execute=True,
            push=True,
            upstream_sync="0\t0",
            pending_research_branches=[
                {
                    "branch": "origin/codex/factor-batch-new-idea",
                    "commit": "abc123",
                    "status": "pending_integration",
                }
            ],
        )

        self.assertTrue(plan["can_execute"])
        self.assertNotIn("pending_research_branches_require_integration", plan["blockers"])

    def test_existing_commits_should_push_when_branch_has_no_upstream(self) -> None:
        self.assertTrue(should_push_existing_commits("no upstream", push=True))

    def test_existing_commits_should_push_when_branch_is_ahead(self) -> None:
        self.assertTrue(should_push_existing_commits("0\t2", push=True))

    def test_existing_commits_do_not_push_when_already_aligned(self) -> None:
        self.assertFalse(should_push_existing_commits("0\t0", push=True))
        self.assertFalse(should_push_existing_commits("0\t2", push=False))


def _config() -> dict:
    return {
        "branch_policy": {
            "stable_branch": "main",
            "main_rule": "Do not run exploratory factor development directly on main.",
        },
        "data_policy": {
            "ignored_paths": ["data/raw/", "data/processed/", "data/reports/", "*.parquet", "*.log"],
            "commit_forbidden": ["Tushare token", "broker credentials"],
        },
        "sync_policy": {
            "allowed_paths": [
                "AGENTS.md",
                "README.md",
                ".github/",
                "configs/",
                "docs/",
                "scripts/",
                "src/",
                "tests/",
                "pyproject.toml",
                ".env.example",
            ],
            "forbidden_paths": [
                ".env",
                ".env.*",
                "data/raw/",
                "data/processed/",
                "data/reports/",
                "*.parquet",
                "*.log",
            ],
        },
    }


if __name__ == "__main__":
    unittest.main()
