import unittest

from scripts.sync_project import build_sync_plan, classify_changed_paths, is_forbidden_path


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
