import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from scripts.run_external_feed_backfill_plan import main


class ExternalFeedBackfillPlanCliTests(unittest.TestCase):
    def test_cli_writes_plan_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "plan"
            with redirect_stdout(StringIO()):
                exit_code = main(
                    [
                        "--start-date",
                        "2025-01-01",
                        "--end-date",
                        "2025-01-31",
                        "--output-root",
                        "data/processed/external_feed_backfill_round172",
                        "--output-dir",
                        str(output_dir),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue((output_dir / "external_feed_long_cycle_backfill_plan.json").exists())
            self.assertTrue((output_dir / "external_feed_long_cycle_backfill_plan.md").exists())


if __name__ == "__main__":
    unittest.main()
