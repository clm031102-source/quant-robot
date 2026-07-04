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

    def test_gap_recovery_windows_follow_missing_trade_date_and_trade_calendar(self) -> None:
        observation_pack = {
            "status": "needs_more_observation_data",
            "fills": {"observed_fills": 5, "required_fills": 20, "fill_deficit": 15},
            "recommendation": {
                "priority": "extend_recent_data_window",
                "suggested_start_date": "2026-03-23",
                "suggested_end_date": "2026-06-26",
            },
            "decision": {"observation_sufficiency_cleared": False},
        }
        recent_refresh_pack = {
            "status": "data_quality_blocked",
            "target_window": {"start_date": "2026-03-23", "end_date": "2026-06-26"},
            "ingest": {
                "downloaded_trade_dates": [
                    "20260427",
                    "20260428",
                    "20260429",
                    "20260430",
                    "20260506",
                    "20260507",
                ],
                "skipped_trade_dates": ["20260323", "20260626"],
            },
            "coverage": {
                "required_asset_missing_trade_dates": [
                    {
                        "asset_id": "CN_ETF_XSHE_160615",
                        "missing_trade_dates": ["2026-04-30"],
                    }
                ]
            },
        }

        plan = build_observation_continuation_plan(
            observation_pack=observation_pack,
            observation_pack_path="data/reports/round478/observation_sufficiency_pack.json",
            recent_data_refresh_pack=recent_refresh_pack,
            recent_data_refresh_pack_path="data/reports/round488/recent_data_refresh_pack.json",
            profile_observation_pack_path="data/reports/round478/profile_observation/profile_observation_pack.json",
            machine="office_desktop",
            task="data_pipeline",
            current_branch="codex/factor-batch-current",
            python_executable="python",
            output_root="data/reports/round488_observation_recovery",
            processed_output_dir="data/processed/round488_observation_recovery",
        )

        self.assertEqual(
            plan["gap_recovery"]["windows"],
            [
                {
                    "label": "before_missing_trade_date",
                    "start_date": "2026-03-23",
                    "end_date": "2026-04-29",
                },
                {
                    "label": "after_missing_trade_date",
                    "start_date": "2026-05-06",
                    "end_date": "2026-06-26",
                },
            ],
        )
        self.assertEqual(plan["gap_recovery"]["missing_trade_dates"], ["2026-04-30"])
        self.assertEqual(
            [row["label"] for row in plan["gap_recovery"]["command_sets"]],
            ["before_missing_trade_date", "after_missing_trade_date"],
        )
        after_commands = plan["gap_recovery"]["command_sets"][1]["commands"]
        self.assertEqual(after_commands[1][after_commands[1].index("--start-date") + 1], "2026-05-06")
        self.assertEqual(after_commands[1][after_commands[1].index("--end-date") + 1], "2026-06-26")
        self.assertEqual(
            after_commands[1][after_commands[1].index("--report-dir") + 1],
            "data/reports/round488_observation_recovery/after_missing_trade_date/recent_data_refresh",
        )


if __name__ == "__main__":
    unittest.main()
