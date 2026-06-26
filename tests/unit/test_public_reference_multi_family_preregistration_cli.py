import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_public_reference_multi_family_preregistration import (
    run_public_reference_multi_family_preregistration_cli,
)


class PublicReferenceMultiFamilyPreregistrationCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_candidate_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"

            result = run_public_reference_multi_family_preregistration_cli(
                output_dir=output,
                min_candidates=18,
                min_families=6,
            )

            self.assertEqual(result["stage"], "public_reference_multi_family_preregistration")
            self.assertTrue((output / "public_reference_multi_family_preregistration.json").exists())
            self.assertTrue((output / "public_reference_multi_family_preregistration.md").exists())
            self.assertTrue((output / "public_reference_multi_family_candidates.csv").exists())
            payload = json.loads(
                (output / "public_reference_multi_family_preregistration.json").read_text(encoding="utf-8")
            )
            self.assertTrue(payload["summary"]["passes"])
            self.assertGreaterEqual(payload["summary"]["candidate_count"], 18)
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
