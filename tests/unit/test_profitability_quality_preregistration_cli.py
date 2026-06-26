import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_profitability_quality_preregistration import (
    run_profitability_quality_preregistration_cli,
)
from tests.unit.test_profitability_quality_preregistration import (
    _clean_financial_rows,
    _write_fina_indicator_inputs,
)


class ProfitabilityQualityPreregistrationCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_candidate_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output = Path(tmp) / "output"
            _write_fina_indicator_inputs(root, _clean_financial_rows())

            result = run_profitability_quality_preregistration_cli(
                input_root=root,
                output_dir=output,
                min_assets=2,
                min_passed_candidates=8,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output / "profitability_quality_preregistration.json").exists())
            self.assertTrue((output / "profitability_quality_preregistration.md").exists())
            self.assertTrue((output / "profitability_quality_candidate_coverage.csv").exists())
            payload = json.loads((output / "profitability_quality_preregistration.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["candidate_count"], result["summary"]["candidate_count"])


if __name__ == "__main__":
    unittest.main()
