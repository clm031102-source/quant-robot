import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.factor_mining_quality_gate import build_factor_mining_quality_gate, required_control_ids
from scripts.run_factor_mining_control_closeout_audit import run_factor_mining_control_closeout_audit


class FactorMiningControlCloseoutAuditCliTests(unittest.TestCase):
    def test_cli_writes_control_closeout_audit_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            quality_gate_path = root / "quality_gate.json"
            output_dir = root / "output"
            controls = required_control_ids()
            statuses = {control_id: "implemented" for control_id in controls}
            statuses["limit_up_down_filter"] = "partial"
            quality_gate_path.write_text(
                json.dumps(
                    build_factor_mining_quality_gate(
                        {
                            "control_status": statuses,
                            "control_evidence": {
                                control_id: f"evidence {control_id}" for control_id in controls
                            },
                            "control_next_actions": {
                                "limit_up_down_filter": "Add official daily limit/suspend fields."
                            },
                        }
                    )
                ),
                encoding="utf-8",
            )

            packet = run_factor_mining_control_closeout_audit(
                quality_gate=quality_gate_path,
                output_dir=output_dir,
            )

            self.assertEqual(packet["status"], "direct_mining_blocked")
            self.assertTrue((output_dir / "factor_mining_control_closeout_audit.json").exists())
            self.assertTrue((output_dir / "factor_mining_control_closeout_audit.md").exists())
            markdown = (output_dir / "factor_mining_control_closeout_audit.md").read_text(encoding="utf-8")
            self.assertIn("Factor Mining Control Closeout Audit", markdown)
            self.assertIn("limit_up_down_filter", markdown)


if __name__ == "__main__":
    unittest.main()
