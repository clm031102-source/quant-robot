import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_provider_remediation import run_provider_remediation


class ProviderRemediationCliTests(unittest.TestCase):
    def test_run_provider_remediation_writes_matrix_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence_path = root / "provider_evidence_pack.json"
            evidence_path.write_text(
                json.dumps(
                    {
                        "providers": [
                            {
                                "provider": "ccxt",
                                "ready": False,
                                "package": "ccxt",
                                "readiness_status": "missing_dependency",
                                "missing": ["ccxt package is not installed"],
                            }
                        ],
                        "parquet": {"ready": True, "missing": []},
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "provider_remediation"
            review_path = root / "provider_remediation_review.csv"
            review_path.write_text(
                "\n".join(
                    [
                        "remediation_id,review_status,evidence_note,reviewed_by,reviewed_at",
                        "PR-ccxt-dependency,resolved_locally,Installed ccxt locally and reran checks,local-reviewer,2026-06-01T00:00:00Z",
                    ]
                ),
                encoding="utf-8",
            )

            matrix = run_provider_remediation(provider_evidence=evidence_path, review_file=review_path, output_dir=output_dir)

            self.assertEqual(matrix["stage"], "phase_4_7_provider_remediation_matrix")
            self.assertTrue((output_dir / "provider_remediation_matrix.json").exists())
            self.assertTrue((output_dir / "provider_remediation_matrix.md").exists())
            self.assertTrue((output_dir / "provider_remediation_items.csv").exists())
            self.assertTrue((output_dir / "provider_remediation_summary.csv").exists())
            self.assertTrue((output_dir / "provider_remediation_review_template.csv").exists())
            self.assertTrue((output_dir / "provider_remediation_status_options.csv").exists())
            self.assertTrue((output_dir / "provider_remediation_validation.csv").exists())
            payload = json.loads((output_dir / "provider_remediation_matrix.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["dependency_items"], 1)
            self.assertEqual(payload["summary"]["blocking_remediation_items"], 0)
            self.assertEqual(payload["review_validation"]["summary"]["applied_review_rows"], 1)
            template_text = (output_dir / "provider_remediation_review_template.csv").read_text(encoding="utf-8")
            status_text = (output_dir / "provider_remediation_status_options.csv").read_text(encoding="utf-8")
            validation_text = (output_dir / "provider_remediation_validation.csv").read_text(encoding="utf-8")
            self.assertIn("needs_review", template_text)
            self.assertIn("resolved_locally", status_text)
            self.assertIn("row_number", validation_text)

    def test_run_provider_remediation_uses_default_review_file_from_output_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence_path = root / "provider_evidence_pack.json"
            evidence_path.write_text(
                json.dumps(
                    {
                        "providers": [
                            {
                                "provider": "ccxt",
                                "ready": False,
                                "package": "ccxt",
                                "readiness_status": "missing_dependency",
                                "missing": ["ccxt package is not installed"],
                            }
                        ],
                        "parquet": {"ready": True, "missing": []},
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "provider_remediation"
            output_dir.mkdir()
            (output_dir / "provider_remediation_review.csv").write_text(
                "\n".join(
                    [
                        "remediation_id,review_status,evidence_note,reviewed_by,reviewed_at",
                        "PR-ccxt-dependency,accepted_out_of_scope,CRYPTO provider is outside the active CN_ETF准实盘 scope,codex,2026-06-09",
                    ]
                ),
                encoding="utf-8",
            )

            matrix = run_provider_remediation(provider_evidence=evidence_path, output_dir=output_dir)

            self.assertEqual(matrix["summary"]["accepted_out_of_scope"], 1)
            self.assertEqual(matrix["summary"]["blocking_remediation_items"], 0)
            self.assertEqual(matrix["review_validation"]["summary"]["applied_review_rows"], 1)


if __name__ == "__main__":
    unittest.main()
