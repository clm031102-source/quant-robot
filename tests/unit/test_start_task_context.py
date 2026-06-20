import json
import tempfile
import unittest
from pathlib import Path

from scripts.start_task_context import build_context, load_config, recommend_branch


class StartTaskContextTests(unittest.TestCase):
    def test_factor_batch_branch_is_task_based_not_machine_based(self) -> None:
        config = {
            "tasks": {
                "factor_batch": {
                    "description": "Large factor experiments",
                    "branch": "codex/factor-batch-<topic-or-date>",
                }
            },
            "machines": {
                "highspec_desktop": {"allowed_tasks": ["factor_batch"]},
                "office_desktop": {"allowed_tasks": ["factor_batch"]},
            },
        }

        self.assertEqual(recommend_branch(config, "factor_batch"), "codex/factor-batch-<topic-or-date>")
        self.assertEqual(recommend_branch(config, "factor_batch"), recommend_branch(config, "factor_batch"))

    def test_missing_machine_task_and_branch_generate_startup_questions(self) -> None:
        config = {
            "machines": {"laptop": {"allowed_tasks": ["architecture_ops"]}},
            "tasks": {
                "architecture_ops": {
                    "description": "Architecture and ops",
                    "branch": "codex/architecture-ops",
                }
            },
            "branch_policy": {"stable_branch": "main"},
            "data_policy": {"ignored_paths": ["data/raw/", "data/processed/", "data/reports/"]},
        }

        context = build_context(config, current_branch="main")

        self.assertEqual(
            context["questions"],
            [
                "Which machine are you using today? Options: laptop.",
                "What task type are you starting? Options: architecture_ops.",
                "Which branch should this work use? Suggested task branches are listed in tasks.",
            ],
        )
        self.assertEqual(context["git"]["current_branch"], "main")
        self.assertEqual(context["data_policy"]["ignored_paths"], ["data/raw/", "data/processed/", "data/reports/"])

    def test_load_config_reads_workstation_policy(self) -> None:
        payload = {
            "machines": {"laptop": {"allowed_tasks": ["architecture_ops"]}},
            "tasks": {"architecture_ops": {"branch": "codex/architecture-ops"}},
        }
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "workstations.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            self.assertEqual(load_config(config_path), payload)

    def test_factor_validation_policy_mentions_progress_audit_promotion_gate(self) -> None:
        config = load_config(Path("configs/workstations.json"))
        description = config["tasks"]["factor_validation"]["description"]

        self.assertIn("long-cycle replay evidence", description)
        self.assertIn("walk-forward progress audit evidence", description)


if __name__ == "__main__":
    unittest.main()
