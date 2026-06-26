import tempfile
import unittest
from pathlib import Path

from scripts.run_cn_calendar_seasonality_preregistration import (
    run_cn_calendar_seasonality_preregistration_cli,
)


class CNCalendarSeasonalityPreregistrationCliTests(unittest.TestCase):
    def test_cli_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)

            result = run_cn_calendar_seasonality_preregistration_cli(output_dir=output)

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["candidate_count"], 8)
            self.assertTrue((output / "cn_calendar_seasonality_preregistration.json").exists())
            self.assertTrue((output / "cn_calendar_seasonality_preregistration.md").exists())
            self.assertTrue((output / "cn_calendar_seasonality_candidates.csv").exists())


if __name__ == "__main__":
    unittest.main()
