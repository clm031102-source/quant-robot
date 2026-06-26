import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_profitability_event_revision_matrix_label_smoke import (
    run_profitability_event_revision_matrix_label_smoke_cli,
)
from tests.unit.test_profitability_event_revision_matrix_label_smoke import _write_bars
from tests.unit.test_profitability_event_revision_preregistration import (
    _financial_rows,
    _write_fina_indicator_inputs,
)
from quant_robot.ops.profitability_event_revision_preregistration import (
    build_profitability_event_revision_preregistration,
    write_profitability_event_revision_preregistration,
)


class ProfitabilityEventRevisionMatrixLabelSmokeCliTests(unittest.TestCase):
    def test_cli_writes_round152_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            prereg_dir = root / "prereg"
            output = root / "output"
            _write_fina_indicator_inputs(financial_root, _financial_rows())
            _write_bars(bars_root, _financial_rows()["asset_id"].unique().tolist())
            prereg = build_profitability_event_revision_preregistration(
                input_root=financial_root,
                min_assets=3,
                min_passed_candidates=6,
                min_families=3,
            )
            write_profitability_event_revision_preregistration(prereg_dir, prereg)

            result = run_profitability_event_revision_matrix_label_smoke_cli(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_dir / "profitability_event_revision_preregistration.json",
                output_dir=output,
                horizons=[5],
                min_label_coverage=0.6,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output / "profitability_event_revision_matrix_label_smoke.json").exists())
            self.assertTrue((output / "profitability_event_revision_matrix_label_smoke.md").exists())
            self.assertTrue((output / "profitability_event_revision_matrix_candidate_summary.csv").exists())
            payload = json.loads((output / "profitability_event_revision_matrix_label_smoke.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["active_candidate_count"], 7)
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
