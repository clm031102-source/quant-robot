import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ExpandedObservationReplayCliTests(unittest.TestCase):
    def test_script_entrypoint_writes_blocked_pack_from_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sufficiency_pack = root / "observation_sufficiency_pack.json"
            sufficiency_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_9_observation_sufficiency",
                        "status": "blocked_missing_observation",
                        "recommendation": {"priority": "rerun_post_refresh_replay"},
                        "decision": {"blockers": ["profile_observation_artifact_missing"]},
                    }
                ),
                encoding="utf-8",
            )
            report_dir = root / "expanded"

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_expanded_observation_replay.py",
                    "--observation-sufficiency-pack",
                    str(sufficiency_pack),
                    "--report-dir",
                    str(report_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("phase_5_10_expanded_observation_replay", result.stdout)
            self.assertTrue((report_dir / "expanded_observation_replay_pack.json").exists())
            payload = json.loads((report_dir / "expanded_observation_replay_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["decision"]["blockers"], ["profile_observation_artifact_missing"])


if __name__ == "__main__":
    unittest.main()
