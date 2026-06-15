import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.run_recent_data_refresh import run_recent_data_refresh


class RecentDataRefreshCliTests(unittest.TestCase):
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
