import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_duplicate_registry import run_duplicate_registry


class DuplicateRegistryCliTests(unittest.TestCase):
    def test_run_duplicate_registry_writes_registry_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "promotion_report.json"
            report_path.write_text(
                json.dumps(
                    {
                        "candidates": [
                            {
                                "promotion_rank": 1,
                                "case_id": "canonical_a",
                                "market": "CN_ETF",
                                "promotion_status": "paper_ready",
                                "duplicate_of": None,
                            },
                            {
                                "promotion_rank": 2,
                                "case_id": "duplicate_b",
                                "market": "CN_ETF",
                                "promotion_status": "blocked",
                                "duplicate_of": "canonical_a",
                                "duplicate_similarity": 0.99,
                                "blocking_reasons": ["duplicate_signal_candidate"],
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "duplicate_registry"

            registry = run_duplicate_registry(promotion_report=report_path, output_dir=output_dir)

            self.assertEqual(registry["stage"], "phase_3_4_duplicate_canonical_registry")
            self.assertTrue((output_dir / "duplicate_canonical_registry.json").exists())
            self.assertTrue((output_dir / "duplicate_canonical_registry.md").exists())
            self.assertTrue((output_dir / "canonical_candidates.csv").exists())
            self.assertTrue((output_dir / "duplicate_members.csv").exists())
            payload = json.loads((output_dir / "duplicate_canonical_registry.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["duplicate_members"], 1)


if __name__ == "__main__":
    unittest.main()
