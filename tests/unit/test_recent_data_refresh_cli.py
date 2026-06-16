import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.run_recent_data_refresh import run_recent_data_refresh


class RecentDataRefreshCliTests(unittest.TestCase):
    WORKSTATION_CONFIG = {
        "machines": {
            "laptop": {"allowed_tasks": ["architecture_ops", "factor_smoke", "factor_review", "project_sync"]},
            "highspec_desktop": {"allowed_tasks": ["data_pipeline", "factor_batch", "factor_validation"]},
            "office_desktop": {"allowed_tasks": ["data_pipeline", "factor_batch", "factor_validation"]},
        },
        "tasks": {"data_pipeline": {"branch": "codex/tushare-data-pipeline"}},
    }

    def test_cli_writes_completed_fixture_refresh_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_pack = root / "profile_observation_pack.json"
            profile_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_6_profile_observation_ledger",
                        "run_date": "2024-01-04",
                        "decision": {"stop_reasons": ["signal_data_stale"]},
                        "ledger": [
                            {
                                "case_id": "case_fixture",
                                "signal_date": "2024-01-02",
                                "profile_id": "cap60_guard12_cd3",
                                "risk_tier": "aggressive_growth",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            processed_dir = root / "processed"
            report_dir = root / "report"

            pack = run_recent_data_refresh(
                profile_observation_pack=profile_pack,
                source="tushare-fixture",
                market="CN_ETF",
                output_dir=processed_dir,
                report_dir=report_dir,
                execute=True,
                readiness={"ready": True, "missing": []},
            )

            self.assertEqual(pack["stage"], "phase_5_7_tushare_recent_data_refresh")
            self.assertEqual(pack["status"], "completed")
            self.assertTrue(pack["decision"]["signal_data_stale_cleared"])
            self.assertTrue((report_dir / "recent_data_refresh_pack.json").exists())
            self.assertTrue((report_dir / "recent_data_refresh_pack.md").exists())
            self.assertTrue((report_dir / "recent_data_refresh_coverage.csv").exists())
            self.assertTrue((report_dir / "recent_data_refresh_next_actions.csv").exists())
            self.assertTrue((processed_dir / "quality_report.json").exists())
            self.assertGreater(pack["ingest"]["processed_rows"], 0)
            self.assertEqual(pack["coverage"]["latest_data_date"], "2024-01-04")

    def test_function_writes_machine_aware_handoff_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_pack = root / "profile_observation_pack.json"
            profile_pack.write_text(
                json.dumps(
                    {
                        "run_date": "2026-06-14",
                        "ledger": [{"signal_date": "2026-05-22", "profile_id": "cap60_guard12_cd3"}],
                    }
                ),
                encoding="utf-8",
            )
            report_dir = root / "report"

            pack = run_recent_data_refresh(
                profile_observation_pack=profile_pack,
                source="tushare",
                market="CN_ETF",
                output_dir=root / "processed",
                report_dir=report_dir,
                execute=False,
                readiness={"ready": True, "missing": []},
                machine="laptop",
                workstation_config=self.WORKSTATION_CONFIG,
            )

            self.assertEqual(pack["next_actions"][0]["action"], "handoff_recent_tushare_refresh")
            written_pack = json.loads((report_dir / "recent_data_refresh_pack.json").read_text(encoding="utf-8"))
            self.assertFalse(written_pack["workstation"]["can_run_data_pipeline"])
            self.assertIn("handoff_recent_tushare_refresh", (report_dir / "recent_data_refresh_pack.md").read_text(encoding="utf-8"))

    def test_execute_request_on_laptop_does_not_run_data_ingest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_pack = root / "profile_observation_pack.json"
            profile_pack.write_text(
                json.dumps(
                    {
                        "run_date": "2026-06-14",
                        "ledger": [{"signal_date": "2026-05-22", "profile_id": "cap60_guard12_cd3"}],
                    }
                ),
                encoding="utf-8",
            )

            def fail_if_called(**_kwargs):
                raise AssertionError("laptop must not run recent Tushare ingest")

            pack = run_recent_data_refresh(
                profile_observation_pack=profile_pack,
                source="tushare",
                market="CN_ETF",
                output_dir=root / "processed",
                report_dir=root / "report",
                execute=True,
                readiness={"ready": True, "missing": []},
                ingest_runner=fail_if_called,
                machine="laptop",
                workstation_config=self.WORKSTATION_CONFIG,
            )

            self.assertFalse(pack["will_download"])
            self.assertEqual(pack["status"], "ready_to_execute")
            self.assertEqual(pack["next_actions"][0]["action"], "handoff_recent_tushare_refresh")

    def test_script_entrypoint_runs_from_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_pack = root / "profile_observation_pack.json"
            profile_pack.write_text(
                json.dumps(
                    {
                        "run_date": "2024-01-04",
                        "ledger": [{"signal_date": "2024-01-02", "profile_id": "cap60_guard12_cd3"}],
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_recent_data_refresh.py",
                    "--profile-observation-pack",
                    str(profile_pack),
                    "--source",
                    "tushare-fixture",
                    "--output-dir",
                    str(root / "processed"),
                    "--report-dir",
                    str(root / "report"),
                    "--execute",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("phase_5_7_tushare_recent_data_refresh", result.stdout)


if __name__ == "__main__":
    unittest.main()
