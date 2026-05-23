import tempfile
import unittest
from pathlib import Path

from scripts.run_fixture_research import run_fixture_research


class FixturePipelineTests(unittest.TestCase):
    def test_fixture_pipeline_runs_research_markets_and_writes_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_fixture_research(Path(tmp))

            self.assertEqual(result["market_count"], 5)
            self.assertGreater(result["factor_rows"], 0)
            self.assertGreater(result["label_rows"], 0)
            self.assertIn("total_return", result["metrics"])
            self.assertTrue((Path(tmp) / "metrics.json").exists())
            self.assertTrue((Path(tmp) / "equity_curve.csv").exists())
            self.assertTrue((Path(tmp) / "equity_curve.svg").exists())
            self.assertTrue((Path(tmp) / "ic.svg").exists())


if __name__ == "__main__":
    unittest.main()
