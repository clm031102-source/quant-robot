import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.profitability_quality_preregistration import (
    build_profitability_quality_preregistration,
    write_profitability_quality_preregistration,
)
from scripts.run_profitability_quality_controlled_ic_screen import (
    run_profitability_quality_controlled_ic_screen_cli,
)
from tests.unit.test_profitability_quality_factor_matrix_smoke import _write_bars
from tests.unit.test_profitability_quality_preregistration import (
    _clean_financial_rows,
    _write_fina_indicator_inputs,
)


class ProfitabilityQualityControlledIcScreenCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            prereg_dir = root / "prereg"
            output = root / "output"
            financial = _clean_financial_rows()
            _write_fina_indicator_inputs(financial_root, financial)
            _write_bars(bars_root, financial["asset_id"].unique().tolist())
            prereg = build_profitability_quality_preregistration(
                input_root=financial_root,
                min_assets=2,
                min_passed_candidates=8,
            )
            write_profitability_quality_preregistration(prereg_dir, prereg)

            result = run_profitability_quality_controlled_ic_screen_cli(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_dir / "profitability_quality_preregistration.json",
                output_dir=output,
                horizons=[5, 20],
                min_cross_section=2,
                min_ic_observations=2,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output / "profitability_quality_controlled_ic_screen.json").exists())
            self.assertTrue((output / "profitability_quality_controlled_ic_screen.md").exists())
            self.assertTrue((output / "profitability_quality_controlled_ic_results.csv").exists())
            payload = json.loads((output / "profitability_quality_controlled_ic_screen.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["test_count"], result["summary"]["test_count"])


if __name__ == "__main__":
    unittest.main()
