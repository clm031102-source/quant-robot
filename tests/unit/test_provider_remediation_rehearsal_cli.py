import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_provider_remediation_rehearsal import run_provider_remediation_rehearsal


class ProviderRemediationRehearsalCliTests(unittest.TestCase):
    def test_run_provider_remediation_rehearsal_writes_artifacts(self):
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
                                "missing": ["ccxt package is not installed"],
                            }
                        ],
                        "parquet": {"ready": False, "missing": ["pyarrow or fastparquet package is not installed"]},
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "provider_remediation_rehearsal"

            rehearsal = run_provider_remediation_rehearsal(provider_evidence=evidence_path, output_dir=output_dir)

            self.assertEqual(rehearsal["stage"], "phase_4_11_provider_remediation_review_rehearsal")
            self.assertTrue((output_dir / "provider_remediation_rehearsal.json").exists())
            self.assertTrue((output_dir / "provider_remediation_rehearsal.md").exists())
            self.assertTrue((output_dir / "sample_provider_remediation_reviews.csv").exists())
            self.assertTrue((output_dir / "rehearsed_provider_remediation_items.csv").exists())
            self.assertTrue((output_dir / "provider_remediation_rehearsal_summary.csv").exists())
            payload = json.loads((output_dir / "provider_remediation_rehearsal.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["sample_review_rows"], 1)
            sample_text = (output_dir / "sample_provider_remediation_reviews.csv").read_text(encoding="utf-8")
            self.assertIn("accepted_out_of_scope", sample_text)


if __name__ == "__main__":
    unittest.main()
