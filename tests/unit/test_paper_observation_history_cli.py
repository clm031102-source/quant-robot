import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class PaperObservationHistoryCliTests(unittest.TestCase):
    def test_script_entrypoint_writes_history_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            activation_pack = root / "tushare_activation_gate_pack.json"
            activation_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_12_tushare_activation_gate",
                        "generated_at": "2026-06-15",
                        "status": "paper_observation_ready",
                        "source": "tushare-fixture",
                        "mode": "execute",
                        "live_boundary_allowed": False,
                        "decision": {
                            "recent_data_ready": True,
                            "activation_chain_allowed": True,
                            "paper_continuation_allowed": True,
                            "blockers": [],
                        },
                        "recent_data_refresh": {
                            "coverage": {
                                "coverage_scope": "required_assets",
                                "required_asset_ids": ["CN_ETF_XSHG_516160"],
                                "expected_trade_dates_count": 15,
                                "required_asset_missing_date_rows": 0,
                                "provider_missing_date_rows": 226,
                            }
                        },
                        "final_observation_sufficiency": {
                            "fills": {"observed_fills": 21, "required_fills": 20}
                        },
                        "iterative_observation_expansion": {"round_count": 2},
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "history"

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_paper_observation_history.py",
                    "--activation-gate-pack",
                    str(activation_pack),
                    "--output-dir",
                    str(output_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            payload = json.loads((output_dir / "paper_observation_history_pack.json").read_text(encoding="utf-8"))
            ledger_exists = (output_dir / "paper_observation_history_ledger.csv").exists()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("phase_5_13_paper_observation_history", result.stdout)
        self.assertEqual(payload["summary"]["run_count"], 1)
        self.assertTrue(payload["decision"]["history_clear_for_continued_paper_observation"])
        self.assertTrue(ledger_exists)


if __name__ == "__main__":
    unittest.main()
