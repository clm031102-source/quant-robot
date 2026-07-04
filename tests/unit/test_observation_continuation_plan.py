import unittest

from scripts.run_observation_continuation_plan import (
    build_observation_continuation_plan,
    default_profile_observation_pack_for_observation,
)


class ObservationContinuationPlanTests(unittest.TestCase):
    def test_needs_more_observation_emits_startup_refresh_replay_and_gate_commands(self) -> None:
        pack = {
            "status": "needs_more_observation_data",
            "fills": {"observed_fills": 5, "required_fills": 20, "fill_deficit": 15},
            "recommendation": {
                "priority": "extend_recent_data_window",
                "suggested_start_date": "2026-03-23",
                "suggested_end_date": "2026-06-26",
            },
            "decision": {"observation_sufficiency_cleared": False},
        }

        plan = build_observation_continuation_plan(
            observation_pack=pack,
            observation_pack_path="data/reports/round478/observation_sufficiency_pack.json",
            profile_observation_pack_path="data/reports/round478/profile_observation/profile_observation_pack.json",
            machine="office_desktop",
            task="data_pipeline",
            current_branch="codex/factor-batch-current",
            python_executable="python",
            output_root="data/reports/round487_observation_continuation",
            processed_output_dir="data/processed/round487_observation_continuation",
        )

        self.assertEqual(plan["status"], "ready")
        self.assertEqual(plan["blockers"], [])
        self.assertEqual(plan["fills"]["fill_deficit"], 15)
        self.assertEqual(
            plan["commands"],
            [
                [
                    "python",
                    "scripts/run_quant_pm_startup_gate.py",
                    "--machine",
                    "office_desktop",
                    "--task",
                    "data_pipeline",
                    "--branch",
                    "codex/factor-batch-current",
                ],
                [
                    "python",
                    "scripts/run_recent_data_refresh.py",
                    "--machine",
                    "office_desktop",
                    "--profile-observation-pack",
                    "data/reports/round478/profile_observation/profile_observation_pack.json",
                    "--start-date",
                    "2026-03-23",
                    "--end-date",
                    "2026-06-26",
                    "--output-dir",
                    "data/processed/round487_observation_continuation",
                    "--report-dir",
                    "data/reports/round487_observation_continuation/recent_data_refresh",
                    "--execute",
                ],
                [
                    "python",
                    "scripts/run_post_refresh_replay.py",
                    "--recent-data-refresh-pack",
                    "data/reports/round487_observation_continuation/recent_data_refresh/recent_data_refresh_pack.json",
                    "--report-dir",
                    "data/reports/round487_observation_continuation/post_refresh_replay",
                ],
                [
                    "python",
                    "scripts/run_observation_sufficiency.py",
                    "--post-refresh-replay-pack",
                    "data/reports/round487_observation_continuation/post_refresh_replay/post_refresh_replay_pack.json",
                    "--profile-observation-pack",
                    "data/reports/round487_observation_continuation/post_refresh_replay/profile_observation/profile_observation_pack.json",
                    "--output-dir",
                    "data/reports/round487_observation_continuation/observation_sufficiency",
                ],
                ["python", "scripts/run_checks.py", "--profile", "pre-alpha", "--execute"],
            ],
        )

    def test_blocks_ineligible_machine_task_and_missing_recommendation_dates(self) -> None:
        plan = build_observation_continuation_plan(
            observation_pack={"status": "needs_more_observation_data", "recommendation": {}},
            observation_pack_path="data/reports/latest/observation_sufficiency_pack.json",
            profile_observation_pack_path=None,
            machine="laptop",
            task="project_sync",
            current_branch="main",
            python_executable="python",
            output_root="data/reports/round487_observation_continuation",
            processed_output_dir="data/processed/round487_observation_continuation",
        )

        self.assertEqual(plan["status"], "blocked")
        self.assertEqual(
            plan["blockers"],
            [
                "machine_must_allow_data_pipeline",
                "task_must_be_data_pipeline",
                "profile_observation_pack_missing",
                "observation_recommendation_dates_missing",
            ],
        )
        self.assertEqual(plan["commands"], [])

    def test_sufficient_observation_does_not_emit_refresh_commands(self) -> None:
        plan = build_observation_continuation_plan(
            observation_pack={
                "status": "sufficient",
                "fills": {"observed_fills": 20, "required_fills": 20, "fill_deficit": 0},
                "recommendation": {"priority": "continue_paper_observation"},
                "decision": {"observation_sufficiency_cleared": True},
            },
            observation_pack_path="data/reports/latest/observation_sufficiency_pack.json",
            profile_observation_pack_path="data/reports/latest/profile_observation_pack.json",
            machine="office_desktop",
            task="data_pipeline",
            current_branch="codex/factor-batch-current",
            python_executable="python",
            output_root="data/reports/round487_observation_continuation",
            processed_output_dir="data/processed/round487_observation_continuation",
        )

        self.assertEqual(plan["status"], "no_action_sufficient")
        self.assertEqual(plan["blockers"], [])
        self.assertEqual(plan["commands"], [["python", "scripts/run_checks.py", "--profile", "pre-alpha", "--execute"]])

    def test_default_profile_pack_follows_selected_observation_round_before_latest_diagnostic(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            observation_pack = (
                root
                / "round478_observation_sufficiency_validated_latest_20260704"
                / "observation_sufficiency_pack.json"
            )
            matching_profile = (
                root
                / "round478_post_refresh_replay_validated_latest_20260704"
                / "profile_observation"
                / "profile_observation_pack.json"
            )
            latest_diagnostic_profile = (
                root
                / "round487_observation_pregap_20260704"
                / "post_refresh_replay"
                / "profile_observation"
                / "profile_observation_pack.json"
            )
            for path in [observation_pack, matching_profile, latest_diagnostic_profile]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")

            self.assertEqual(default_profile_observation_pack_for_observation(observation_pack), matching_profile)


if __name__ == "__main__":
    unittest.main()
