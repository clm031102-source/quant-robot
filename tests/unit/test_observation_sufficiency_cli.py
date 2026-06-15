import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ObservationSufficiencyCliTests(unittest.TestCase):
    def test_script_entrypoint_writes_sufficiency_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            observation_dir = root / "profile_observation"
            observation_dir.mkdir()
            post_refresh_pack = root / "post_refresh_replay_pack.json"
            post_refresh_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_8_post_refresh_replay",
                        "status": "replay_blocked",
                        "decision": {"blockers": ["minimum_fills_observed"]},
                        "recent_data_refresh": {"target_window": {"end_date": "2026-06-14"}},
                        "profile_observation_output_dir": str(observation_dir),
                    }
                ),
                encoding="utf-8",
            )
            (observation_dir / "profile_observation_pack.json").write_text(
                json.dumps(
                    {
                        "run_date": "2026-06-14",
                        "decision": {"stop_reasons": ["minimum_fills_observed"]},
                        "observation_window": {"start_date": "2026-05-28", "end_date": "2026-06-13"},
                        "stop_rules": [
                            {"rule_id": "minimum_fills_observed", "status": "stop", "observed_value": 2, "threshold": 20}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "sufficiency"

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_observation_sufficiency.py",
                    "--post-refresh-replay-pack",
                    str(post_refresh_pack),
                    "--output-dir",
                    str(output_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("phase_5_9_observation_sufficiency", result.stdout)
            self.assertTrue((output_dir / "observation_sufficiency_pack.json").exists())
            payload = json.loads((output_dir / "observation_sufficiency_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "needs_more_observation_data")


if __name__ == "__main__":
    unittest.main()
