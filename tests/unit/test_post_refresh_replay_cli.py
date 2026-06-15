import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class PostRefreshReplayCliTests(unittest.TestCase):
    def test_script_entrypoint_writes_blocked_replay_pack_from_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            recent_pack = root / "recent_data_refresh_pack.json"
            recent_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_7_tushare_recent_data_refresh",
                        "status": "blocked",
                        "mode": "dry_run",
                        "output_dir": str(root / "processed"),
                        "decision": {
                            "recent_data_ready": False,
                            "signal_data_stale_cleared": False,
                            "blockers": ["TUSHARE_TOKEN is not set"],
                        },
                    }
                ),
                encoding="utf-8",
            )
            report_dir = root / "report"
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_post_refresh_replay.py",
                    "--recent-data-refresh-pack",
                    str(recent_pack),
                    "--report-dir",
                    str(report_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("phase_5_8_post_refresh_replay", result.stdout)
            self.assertTrue((report_dir / "post_refresh_replay_pack.json").exists())
            payload = json.loads((report_dir / "post_refresh_replay_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["decision"]["blockers"], ["TUSHARE_TOKEN is not set"])


if __name__ == "__main__":
    unittest.main()
