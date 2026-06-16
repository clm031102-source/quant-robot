import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TushareActivationGateCliTests(unittest.TestCase):
    def test_script_entrypoint_writes_blocked_pack_without_env_token(self):
        repo_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_pack = root / "profile_observation_pack.json"
            profile_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_6_profile_observation_ledger",
                        "run_date": "2026-06-14",
                        "ledger": [{"signal_date": "2026-05-22", "profile_id": "cap60_guard12_cd3"}],
                    }
                ),
                encoding="utf-8",
            )
            report_dir = root / "activation"
            env = dict(os.environ)
            env["TUSHARE_TOKEN"] = ""
            env["PYTHONPATH"] = str(repo_root / "src") + os.pathsep + env.get("PYTHONPATH", "")

            result = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "scripts/run_tushare_activation_gate.py"),
                    "--profile-observation-pack",
                    str(profile_pack),
                    "--report-dir",
                    str(report_dir),
                    "--execute",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=env,
                cwd=root,
            )

            payload = json.loads((report_dir / "tushare_activation_gate_pack.json").read_text(encoding="utf-8"))
            serialized = json.dumps(payload, ensure_ascii=False)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("phase_5_12_tushare_activation_gate", result.stdout)
        self.assertEqual(payload["status"], "blocked_missing_readiness")
        self.assertIn("TUSHARE_TOKEN is not set", payload["decision"]["blockers"])
        self.assertEqual(payload["next_actions"][0]["action"], "set_tushare_token_env")
        self.assertNotIn(("f" * 64), serialized)
        self.assertFalse(payload["live_boundary_allowed"])

    def test_script_entrypoint_hands_off_execute_on_laptop(self):
        repo_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_pack = root / "profile_observation_pack.json"
            profile_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_6_profile_observation_ledger",
                        "run_date": "2026-06-14",
                        "ledger": [{"signal_date": "2026-05-22", "profile_id": "cap60_guard12_cd3"}],
                    }
                ),
                encoding="utf-8",
            )
            report_dir = root / "activation"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(repo_root / "src") + os.pathsep + env.get("PYTHONPATH", "")

            result = subprocess.run(
                [
                    sys.executable,
                    str(repo_root / "scripts/run_tushare_activation_gate.py"),
                    "--profile-observation-pack",
                    str(profile_pack),
                    "--report-dir",
                    str(report_dir),
                    "--source",
                    "tushare-fixture",
                    "--machine",
                    "laptop",
                    "--execute",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=env,
                cwd=repo_root,
            )

            payload = json.loads((report_dir / "tushare_activation_gate_pack.json").read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["status"], "ready_to_execute")
        self.assertEqual(payload["mode"], "dry_run")
        self.assertFalse(payload["workstation"]["can_run_data_pipeline"])
        self.assertEqual(payload["next_actions"][0]["action"], "handoff_tushare_activation_gate")
        self.assertFalse((report_dir / "post_refresh_replay").exists())


if __name__ == "__main__":
    unittest.main()
