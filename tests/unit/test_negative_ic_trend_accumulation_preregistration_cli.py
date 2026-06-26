import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_negative_ic_trend_accumulation_preregistration import (
    run_negative_ic_trend_accumulation_preregistration_cli,
)


class NegativeIcTrendAccumulationPreregistrationCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_candidate_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"

            result = run_negative_ic_trend_accumulation_preregistration_cli(
                output_dir=output,
                min_candidates=8,
            )

            self.assertEqual(result["stage"], "negative_ic_trend_accumulation_preregistration")
            self.assertGreaterEqual(result["summary"]["candidate_count"], 8)
            self.assertTrue((output / "negative_ic_trend_accumulation_preregistration.json").exists())
            self.assertTrue((output / "negative_ic_trend_accumulation_preregistration.md").exists())
            self.assertTrue((output / "negative_ic_trend_accumulation_candidates.csv").exists())
            payload = json.loads(
                (output / "negative_ic_trend_accumulation_preregistration.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["summary"]["candidate_count"], result["summary"]["candidate_count"])
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
