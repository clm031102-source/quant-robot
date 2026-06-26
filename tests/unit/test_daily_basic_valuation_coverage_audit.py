import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.daily_basic_valuation_coverage_audit import (
    NEXT_REPAIR_PREREGISTRATION,
    NEXT_REQUIRES_DATA_BACKFILL,
    STAGE,
    summarize_daily_basic_valuation_coverage_audit,
    write_daily_basic_valuation_coverage_audit,
)


def _daily_basic_frame(*, dv_ttm_ratio: float, dv_ratio_ratio: float) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=8)
    assets = [f"CN_XSHG_TEST{i:03d}" for i in range(10)]
    rows = []
    for trade_date in dates:
        for idx, asset_id in enumerate(assets):
            rows.append(
                {
                    "date": trade_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "pb": 1.0 + idx * 0.02,
                    "ps_ttm": 2.0 + idx * 0.03,
                    "pe_ttm": 10.0 + idx * 0.2,
                    "dv_ttm": 1.0 if idx < int(len(assets) * dv_ttm_ratio) else pd.NA,
                    "dv_ratio": 0.8 if idx < int(len(assets) * dv_ratio_ratio) else pd.NA,
                }
            )
    return pd.DataFrame(rows)


class DailyBasicValuationCoverageAuditTests(unittest.TestCase):
    def test_low_dv_ttm_with_clean_dv_ratio_allows_only_preregistered_repair(self) -> None:
        result = summarize_daily_basic_valuation_coverage_audit(
            daily_basic_frame=_daily_basic_frame(dv_ttm_ratio=0.6, dv_ratio_ratio=1.0),
            target_factor_specs=[
                {
                    "factor_name": "daily_basic_valuation_reversion_quality_60",
                    "required_fields": ["pb", "ps_ttm", "dv_ttm"],
                    "replacement_field_candidates": {"dv_ttm": ["dv_ratio"]},
                }
            ],
            min_full_coverage_ratio=0.8,
            min_field_non_null_ratio=0.8,
        )

        self.assertEqual(result["stage"], STAGE)
        self.assertEqual(result["summary"]["target_factor_count"], 1)
        self.assertEqual(result["summary"]["coverage_pass_count"], 0)
        self.assertEqual(result["summary"]["repair_candidate_pre_registration_allowed_count"], 1)
        self.assertEqual(result["next_direction"], NEXT_REPAIR_PREREGISTRATION)
        self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])

        factor_row = result["factor_coverage"][0]
        self.assertFalse(factor_row["coverage_pass"])
        self.assertAlmostEqual(factor_row["full_required_field_coverage_ratio"], 0.6)
        self.assertEqual(factor_row["low_coverage_fields"], ["dv_ttm"])
        self.assertTrue(factor_row["repair_candidate_pre_registration_allowed"])

        repair_row = result["replacement_candidates"][0]
        self.assertEqual(repair_row["missing_field"], "dv_ttm")
        self.assertEqual(repair_row["candidate_field"], "dv_ratio")
        self.assertTrue(repair_row["replacement_pass"])

    def test_missing_required_field_without_safe_replacement_blocks_family(self) -> None:
        result = summarize_daily_basic_valuation_coverage_audit(
            daily_basic_frame=_daily_basic_frame(dv_ttm_ratio=0.5, dv_ratio_ratio=0.5),
            target_factor_specs=[
                {
                    "factor_name": "daily_basic_valuation_reversion_quality_60",
                    "required_fields": ["pb", "ps_ttm", "dv_ttm"],
                    "replacement_field_candidates": {"dv_ttm": ["dv_ratio"]},
                }
            ],
            min_full_coverage_ratio=0.8,
            min_field_non_null_ratio=0.8,
        )

        self.assertEqual(result["summary"]["repair_candidate_pre_registration_allowed_count"], 0)
        self.assertEqual(result["next_direction"], NEXT_REQUIRES_DATA_BACKFILL)
        self.assertIn("no_coverage_safe_replacement_field", result["gate"]["blockers"])
        self.assertFalse(result["factor_coverage"][0]["repair_candidate_pre_registration_allowed"])

    def test_write_outputs_json_csv_and_markdown(self) -> None:
        result = summarize_daily_basic_valuation_coverage_audit(
            daily_basic_frame=_daily_basic_frame(dv_ttm_ratio=0.6, dv_ratio_ratio=1.0),
            target_factor_specs=[
                {
                    "factor_name": "daily_basic_valuation_reversion_quality_60",
                    "required_fields": ["pb", "ps_ttm", "dv_ttm"],
                    "replacement_field_candidates": {"dv_ttm": ["dv_ratio"]},
                }
            ],
            min_full_coverage_ratio=0.8,
            min_field_non_null_ratio=0.8,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_daily_basic_valuation_coverage_audit(output_dir, result)

            self.assertTrue((output_dir / "daily_basic_valuation_coverage_audit_summary.json").exists())
            self.assertTrue((output_dir / "daily_basic_valuation_coverage_factor_coverage.csv").exists())
            self.assertTrue((output_dir / "daily_basic_valuation_coverage_field_coverage.csv").exists())
            self.assertTrue((output_dir / "daily_basic_valuation_coverage_replacement_candidates.csv").exists())
            self.assertTrue((output_dir / "daily_basic_valuation_coverage_monthly_coverage.csv").exists())
            self.assertTrue((output_dir / "daily_basic_valuation_coverage_audit.md").exists())


if __name__ == "__main__":
    unittest.main()
