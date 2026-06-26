import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_final_holdout_result_audit import run_final_holdout_result_audit


class FinalHoldoutResultAuditCliTests(unittest.TestCase):
    def test_cli_writes_result_audit_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "walk_forward.json"
            output_dir = root / "audit"
            report_path.write_text(
                json.dumps(
                    {
                        "holdout_policy": {
                            "final_holdout_included": True,
                            "final_holdout_start": "2026-01-01",
                        },
                        "leaderboard": [{"case_id": "case_a", "validation_status": "accepted"}],
                        "folds": [
                            {
                                "case_id": "case_a",
                                "test_end_date": "2026-05-28",
                                "fold_validation_status": "rejected",
                                "fold_validation_blockers": "test_total_return_below_minimum",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            audit = run_final_holdout_result_audit(report_path=report_path, output_dir=output_dir)

            self.assertFalse(audit["decision"]["paper_gate_allowed"])
            self.assertTrue((output_dir / "final_holdout_result_audit.json").exists())
            self.assertTrue((output_dir / "final_holdout_result_audit.md").exists())


if __name__ == "__main__":
    unittest.main()
