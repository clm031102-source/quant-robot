import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_final_holdout_readiness_audit import run_final_holdout_readiness_audit


class FinalHoldoutReadinessAuditCliTests(unittest.TestCase):
    def test_cli_writes_readiness_artifacts(self) -> None:
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
                        "data_window": {
                            "max_bar_date": "2026-06-15",
                            "max_signal_date": "2025-12-23",
                        },
                        "summary": {"walk_forward_accepted_candidates": 6},
                        "folds": [],
                        "promotion_policy": {"blockers": ["final_holdout_not_read"]},
                    }
                ),
                encoding="utf-8",
            )

            audit = run_final_holdout_readiness_audit(report_path=report_path, output_dir=output_dir)

            self.assertFalse(audit["decision"]["final_holdout_actual_read"])
            self.assertTrue((output_dir / "final_holdout_readiness_audit.json").exists())
            self.assertTrue((output_dir / "final_holdout_readiness_audit.md").exists())


if __name__ == "__main__":
    unittest.main()
