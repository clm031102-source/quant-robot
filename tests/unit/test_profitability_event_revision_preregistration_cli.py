import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_profitability_event_revision_preregistration import (
    run_profitability_event_revision_preregistration_cli,
)
from tests.unit.test_profitability_event_revision_preregistration import (
    _financial_rows,
    _write_fina_indicator_inputs,
)


class ProfitabilityEventRevisionPreregistrationCliTests(unittest.TestCase):
    def test_cli_writes_round151_artifacts_and_blocks_portfolio_permission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            output = Path(tmp) / "output"
            _write_fina_indicator_inputs(root, _financial_rows())

            result = run_profitability_event_revision_preregistration_cli(
                input_root=root,
                output_dir=output,
                min_assets=3,
                min_passed_candidates=6,
                allow_not_ready=False,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["candidate_count"], 10)
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
            self.assertTrue((output / "profitability_event_revision_preregistration.json").exists())
            self.assertTrue((output / "profitability_event_revision_preregistration.md").exists())
            self.assertTrue((output / "profitability_event_revision_candidates.csv").exists())
            payload = json.loads((output / "profitability_event_revision_preregistration.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["next_required_gate"], "round152_pit_profitability_event_revision_matrix_and_label_smoke")


if __name__ == "__main__":
    unittest.main()
