import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.profitability_quality_controlled_ic_screen import (
    build_profitability_quality_controlled_ic_screen,
    summarize_controlled_ic,
)
from quant_robot.ops.profitability_quality_preregistration import (
    build_profitability_quality_preregistration,
    write_profitability_quality_preregistration,
)
from tests.unit.test_profitability_quality_factor_matrix_smoke import _write_bars
from tests.unit.test_profitability_quality_preregistration import (
    _clean_financial_rows,
    _write_fina_indicator_inputs,
)


class ProfitabilityQualityControlledIcScreenTests(unittest.TestCase):
    def test_summarizes_spearman_ic_and_multiple_testing_controls(self) -> None:
        aligned = _strong_ic_aligned_frame()

        result = summarize_controlled_ic(
            aligned,
            min_cross_section=20,
            min_ic_observations=4,
            alpha=0.05,
        )

        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["summary"]["test_count"], 2)
        self.assertEqual(result["summary"]["bonferroni_significant"], 1)
        self.assertEqual(result["summary"]["fdr_significant"], 1)
        rows = {(row["factor_name"], row["horizon"]): row for row in result["ic_results"]}
        strong = rows[("strong_quality", 5)]
        weak = rows[("weak_quality", 5)]
        self.assertGreater(strong["ic_mean"], 0.95)
        self.assertGreater(strong["t_stat"], 10)
        self.assertTrue(strong["bonferroni_significant"])
        self.assertFalse(weak["bonferroni_significant"])

    def test_builds_ic_screen_from_preregistered_financial_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            prereg_dir = root / "prereg"
            financial = _clean_financial_rows()
            _write_fina_indicator_inputs(financial_root, financial)
            _write_bars(bars_root, financial["asset_id"].unique().tolist())
            prereg = build_profitability_quality_preregistration(
                input_root=financial_root,
                min_assets=2,
                min_passed_candidates=8,
            )
            write_profitability_quality_preregistration(prereg_dir, prereg)

            result = build_profitability_quality_controlled_ic_screen(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_dir / "profitability_quality_preregistration.json",
                horizons=(5, 20),
                min_cross_section=2,
                min_ic_observations=2,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertGreater(result["summary"]["aligned_rows"], 0)
            self.assertGreater(result["summary"]["test_count"], 0)
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])


def _strong_ic_aligned_frame() -> pd.DataFrame:
    rows = []
    for period_index in range(6):
        end_date = pd.Timestamp("2023-03-31") + pd.offsets.QuarterEnd(period_index)
        for asset_index in range(30):
            asset_id = f"asset_{asset_index:03d}"
            rows.append(
                {
                    "factor_name": "strong_quality",
                    "horizon": 5,
                    "asset_id": asset_id,
                    "end_date": end_date,
                    "factor_value": asset_index,
                    "forward_return": asset_index / 100.0,
                }
            )
            rows.append(
                {
                    "factor_name": "weak_quality",
                    "horizon": 5,
                    "asset_id": asset_id,
                    "end_date": end_date,
                    "factor_value": asset_index,
                    "forward_return": asset_index / 100.0 if period_index % 2 == 0 else -asset_index / 100.0,
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
