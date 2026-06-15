import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class PaperOpsGuardrailCliTests(unittest.TestCase):
    def test_script_entrypoint_writes_guardrail_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history_pack = root / "paper_observation_history_pack.json"
            history_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_13_paper_observation_history",
                        "decision": {
                            "history_clear_for_continued_paper_observation": True,
                            "blockers": [],
                        },
                        "summary": {
                            "run_count": 1,
                            "paper_observation_ready_runs": 1,
                            "latest_provider_missing_date_rows": 226,
                            "live_boundary_violations": 0,
                            "latest_status": "paper_observation_ready",
                            "latest_required_assets": ["CN_ETF_XSHG_516160"],
                            "latest_final_fills": 21,
                            "latest_required_fills": 20,
                        },
                        "live_boundary_allowed": False,
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "guardrail"

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_paper_ops_guardrail.py",
                    "--paper-observation-history",
                    str(history_pack),
                    "--output-dir",
                    str(output_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            payload = json.loads((output_dir / "paper_ops_guardrail_pack.json").read_text(encoding="utf-8"))
            checks_exists = (output_dir / "paper_ops_guardrail_checks.csv").exists()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("phase_5_14_paper_ops_guardrail", result.stdout)
        self.assertEqual(payload["status"], "paper_ops_watch")
        self.assertTrue(payload["decision"]["continued_paper_observation_allowed"])
        self.assertTrue(checks_exists)


if __name__ == "__main__":
    unittest.main()
