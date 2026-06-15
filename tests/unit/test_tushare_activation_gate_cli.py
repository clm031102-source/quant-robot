import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TushareActivationGateCliTests(unittest.TestCase):
    def test_script_entrypoint_writes_blocked_pack_without_env_token(self):
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

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_tushare_activation_gate.py",
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
            )

            payload = json.loads((report_dir / "tushare_activation_gate_pack.json").read_text(encoding="utf-8"))
            serialized = json.dumps(payload, ensure_ascii=False)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("phase_5_12_tushare_activation_gate", result.stdout)
        self.assertEqual(payload["status"], "blocked_missing_readiness")
        self.assertIn("TUSHARE_TOKEN is not set", payload["decision"]["blockers"])
        self.assertEqual(payload["next_actions"][0]["action"], "set_tushare_token_env")
        self.assertNotIn("4743e70e52e8a48872d71135ffe6baadb391ac7075c2507189a964c0", serialized)
        self.assertFalse(payload["live_boundary_allowed"])


if __name__ == "__main__":
    unittest.main()
