import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.profitability_quality_factor_matrix_smoke import (
    build_profitability_quality_factor_matrix_smoke,
)
from quant_robot.ops.profitability_quality_preregistration import (
    build_profitability_quality_preregistration,
    write_profitability_quality_preregistration,
)
from quant_robot.storage.dataset_store import DatasetStore
from tests.unit.test_profitability_quality_preregistration import (
    _clean_financial_rows,
    _write_fina_indicator_inputs,
)


class ProfitabilityQualityFactorMatrixSmokeTests(unittest.TestCase):
    def test_builds_factor_matrix_and_forward_labels_without_leakage(self) -> None:
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

            result = build_profitability_quality_factor_matrix_smoke(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_dir / "profitability_quality_preregistration.json",
                horizons=(5, 20),
                min_label_coverage=0.6,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertGreaterEqual(result["summary"]["candidate_count"], 12)
            self.assertGreater(result["summary"]["factor_value_rows"], 0)
            self.assertGreater(result["summary"]["label_aligned_rows"], 0)
            self.assertEqual(result["summary"]["alignment_violation_rows"], 0)
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertIn(5, result["summary"]["horizons"])
            self.assertIn(20, result["summary"]["horizons"])

    def test_blocks_when_forward_labels_are_not_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            prereg_dir = root / "prereg"
            financial = _clean_financial_rows()
            _write_fina_indicator_inputs(financial_root, financial)
            _write_sparse_bars(bars_root, financial["asset_id"].unique().tolist())
            prereg = build_profitability_quality_preregistration(
                input_root=financial_root,
                min_assets=2,
                min_passed_candidates=8,
            )
            write_profitability_quality_preregistration(prereg_dir, prereg)

            result = build_profitability_quality_factor_matrix_smoke(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_dir / "profitability_quality_preregistration.json",
                horizons=(20,),
                min_label_coverage=0.6,
            )

            self.assertFalse(result["summary"]["passes"])
            self.assertIn("label_coverage_below_threshold", result["summary"]["blockers"])


def _write_bars(root: Path, asset_ids: list[str]) -> None:
    dates = pd.bdate_range("2023-04-03", "2025-03-31")
    rows = []
    for asset_index, asset_id in enumerate(asset_ids):
        for index, day in enumerate(dates):
            rows.append(
                {
                    "date": day,
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": 10 + asset_index + index * 0.01,
                }
            )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/bars",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


def _write_sparse_bars(root: Path, asset_ids: list[str]) -> None:
    rows = [
        {"date": pd.Timestamp("2024-01-02"), "asset_id": asset_id, "market": "CN", "adj_close": 10.0}
        for asset_id in asset_ids
    ]
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/bars",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


if __name__ == "__main__":
    unittest.main()
