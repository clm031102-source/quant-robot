import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class PaperOpsRunbookCliTests(unittest.TestCase):
    def test_script_entrypoint_writes_runbook_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            guardrail_pack = root / "paper_ops_guardrail_pack.json"
            guardrail_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_14_paper_ops_guardrail",
                        "status": "paper_ops_watch",
                        "decision": {
                            "continued_paper_observation_allowed": True,
                            "live_readiness_candidate": False,
                            "blockers": [],
                            "warnings": ["short_paper_history"],
                        },
                        "summary": {
                            "history_run_count": 1,
                            "paper_observation_ready_runs": 1,
                            "ready_run_deficit_for_live_readiness": 19,
                            "latest_required_assets": ["CN_ETF_XSHG_516160"],
                            "latest_provider_missing_date_rows": 226,
                        },
                        "live_boundary_allowed": False,
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "runbook"

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_paper_ops_runbook.py",
                    "--paper-ops-guardrail",
                    str(guardrail_pack),
                    "--output-dir",
                    str(output_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            payload = json.loads((output_dir / "paper_ops_runbook_pack.json").read_text(encoding="utf-8"))
            commands_exists = (output_dir / "paper_ops_runbook_commands.csv").exists()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("phase_5_15_paper_ops_runbook", result.stdout)
        self.assertEqual(payload["status"], "paper_cycle_ready")
        self.assertEqual(payload["summary"]["command_count"], 4)
        self.assertTrue(commands_exists)


if __name__ == "__main__":
    unittest.main()
