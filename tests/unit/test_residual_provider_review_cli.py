import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_residual_provider_review import run_residual_provider_review


class ResidualProviderReviewCliTests(unittest.TestCase):
    def test_cli_writes_residual_provider_review_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rehearsal_path = root / "provider_rehearsal.json"
            output_dir = root / "out"
            rehearsal_path.write_text(
                json.dumps(
                    {
                        "stage": "phase_4_11_provider_remediation_review_rehearsal",
                        "summary": {"source_remediation_items": 1, "sample_review_rows": 0, "rehearsed_blocking_remediation_items": 1},
                        "rehearsed_remediation_items": [
                            {
                                "remediation_id": "PR-open",
                                "provider": "tushare",
                                "blocker_type": "dependency",
                                "blocker": "tushare package is not installed",
                                "review_status": "needs_review",
                                "evidence_note": "",
                                "verification_command": "python scripts\\check_readiness.py",
                                "resolution_hint": "install locally",
                                "blocks_provider_readiness": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            pack = run_residual_provider_review(
                provider_remediation_rehearsal=rehearsal_path,
                provider_remediation_matrix=None,
                output_dir=output_dir,
            )

            self.assertEqual(pack["summary"]["residual_remediation_items"], 1)
            self.assertTrue((output_dir / "residual_provider_review_pack.json").exists())
            self.assertTrue((output_dir / "residual_provider_review_pack.md").exists())
            self.assertTrue((output_dir / "residual_provider_remediation_items.csv").exists())
            self.assertTrue((output_dir / "residual_provider_review_template.csv").exists())
            self.assertTrue((output_dir / "residual_provider_action_queue.csv").exists())
            self.assertTrue((output_dir / "residual_provider_status_options.csv").exists())

    def test_cli_uses_current_remediation_matrix_when_supplied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rehearsal_path = root / "provider_rehearsal.json"
            matrix_path = root / "provider_remediation_matrix.json"
            output_dir = root / "out"
            rehearsal_path.write_text(
                json.dumps(
                    {
                        "stage": "phase_4_11_provider_remediation_review_rehearsal",
                        "summary": {"source_remediation_items": 1, "sample_review_rows": 0, "rehearsed_blocking_remediation_items": 1},
                        "rehearsed_remediation_items": [],
                    }
                ),
                encoding="utf-8",
            )
            matrix_path.write_text(
                json.dumps(
                    {
                        "stage": "phase_4_7_provider_remediation_matrix",
                        "summary": {"remediation_items": 1, "blocking_remediation_items": 1},
                        "remediation_items": [
                            {
                                "remediation_id": "PR-tushare-credential",
                                "provider": "tushare",
                                "blocker_type": "credential",
                                "blocker": "TUSHARE_TOKEN is not set",
                                "review_status": "blocked_external_change",
                                "evidence_note": "token required",
                                "verification_command": "python scripts\\show_provider_status.py",
                                "resolution_hint": "set token",
                                "blocks_provider_readiness": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            pack = run_residual_provider_review(
                provider_remediation_rehearsal=rehearsal_path,
                provider_remediation_matrix=matrix_path,
                output_dir=output_dir,
            )

            self.assertEqual(pack["source_stage"], "phase_4_7_provider_remediation_matrix")
            self.assertEqual(pack["summary"]["residual_remediation_items"], 1)
            self.assertEqual(pack["residual_items"][0]["review_status"], "blocked_external_change")


if __name__ == "__main__":
    unittest.main()
