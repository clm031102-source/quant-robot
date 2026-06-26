import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_public_alpha101_capacity_safe_preregistration import (
    run_public_alpha101_capacity_safe_preregistration_cli,
)


class PublicAlpha101CapacitySafePreregistrationCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_candidate_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"

            result = run_public_alpha101_capacity_safe_preregistration_cli(
                output_dir=output,
                min_candidates=10,
            )

            self.assertEqual(result["stage"], "public_alpha101_capacity_safe_preregistration")
            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output / "public_alpha101_capacity_safe_preregistration.json").exists())
            self.assertTrue((output / "public_alpha101_capacity_safe_preregistration.md").exists())
            self.assertTrue((output / "public_alpha101_capacity_safe_candidates.csv").exists())
            payload = json.loads(
                (output / "public_alpha101_capacity_safe_preregistration.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["summary"]["candidate_count"], result["summary"]["candidate_count"])
            self.assertEqual(
                payload["family_rotation_context"]["next_direction"],
                "round115_public_alpha101_ic_quantile_turnover_prescreen",
            )
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
