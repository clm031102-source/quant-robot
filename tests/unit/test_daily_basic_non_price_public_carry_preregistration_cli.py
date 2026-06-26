import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_daily_basic_non_price_public_carry_preregistration import (
    run_daily_basic_non_price_public_carry_preregistration_cli,
)


class DailyBasicNonPricePublicCarryPreregistrationCliTests(unittest.TestCase):
    def test_cli_writes_preregistration_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "round131"

            result = run_daily_basic_non_price_public_carry_preregistration_cli(
                output_dir=output_dir,
                min_candidates=8,
                min_families=4,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output_dir / "daily_basic_non_price_public_carry_preregistration.json").exists())
            self.assertTrue((output_dir / "daily_basic_non_price_public_carry_preregistration.md").exists())
            self.assertTrue((output_dir / "daily_basic_non_price_public_carry_candidates.csv").exists())
            payload = json.loads(
                (output_dir / "daily_basic_non_price_public_carry_preregistration.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(payload["summary"]["candidate_count"], result["summary"]["candidate_count"])
            self.assertEqual(
                payload["summary"]["next_required_gate"],
                "round132_daily_basic_non_price_public_carry_prescreen",
            )


if __name__ == "__main__":
    unittest.main()
