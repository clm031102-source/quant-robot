import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.financial_reporting_timeliness_source_audit import (
    NEXT_BACKFILL,
    NEXT_CANDIDATE_PLAN,
    STAGE,
    summarize_financial_reporting_timeliness_source_audit,
    write_financial_reporting_timeliness_source_audit,
)


def _statement_rows(*, symbols: int, years: range, symbol_offset: int = 0) -> pd.DataFrame:
    rows = []
    for year in years:
        for symbol_idx in range(symbols):
            rows.append(
                {
                    "symbol": f"{symbol_idx + symbol_offset:06d}.SZ",
                    "ann_date": f"{year + 1}0430",
                    "end_date": f"{year}1231",
                    "report_type": "1",
                }
            )
    return pd.DataFrame(rows)


class FinancialReportingTimelinessSourceAuditTests(unittest.TestCase):
    def test_blocks_candidate_generation_when_symbol_or_year_coverage_is_too_low(self) -> None:
        result = summarize_financial_reporting_timeliness_source_audit(
            financial_frames={"statement": _statement_rows(symbols=2, years=range(2024, 2026))},
            analysis_start_date="2015-01-01",
            analysis_end_date="2025-12-31",
            min_unique_symbols=100,
            min_end_years=8,
        )

        self.assertEqual(result["stage"], STAGE)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["next_direction"], NEXT_BACKFILL)
        self.assertIn("unique_symbol_count_below_minimum", result["gate"]["blockers"])
        self.assertIn("end_year_coverage_below_minimum", result["gate"]["blockers"])
        self.assertFalse(result["candidate_plan_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])

    def test_allows_candidate_plan_only_after_source_coverage_passes(self) -> None:
        result = summarize_financial_reporting_timeliness_source_audit(
            financial_frames={"statement": _statement_rows(symbols=120, years=range(2015, 2026))},
            analysis_start_date="2015-01-01",
            analysis_end_date="2025-12-31",
            min_unique_symbols=100,
            min_end_years=8,
        )

        self.assertEqual(result["status"], "source_ready")
        self.assertEqual(result["next_direction"], NEXT_CANDIDATE_PLAN)
        self.assertEqual(result["summary"]["source_count"], 1)
        self.assertEqual(result["summary"]["source_ready_count"], 1)
        self.assertTrue(result["candidate_plan_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])

    def test_uses_aggregate_union_coverage_across_sharded_sources_for_source_gate(self) -> None:
        result = summarize_financial_reporting_timeliness_source_audit(
            financial_frames={
                "statement_shard_1": _statement_rows(symbols=60, years=range(2015, 2026), symbol_offset=0),
                "statement_shard_2": _statement_rows(symbols=60, years=range(2015, 2026), symbol_offset=60),
            },
            analysis_start_date="2015-01-01",
            analysis_end_date="2025-12-31",
            min_unique_symbols=100,
            min_end_years=8,
        )

        self.assertEqual(result["status"], "source_ready")
        self.assertEqual(result["summary"]["unique_symbols"], 120)
        self.assertEqual(result["summary"]["source_ready_count"], 1)
        self.assertEqual(result["aggregate_profile"]["source"], "aggregate_union")
        self.assertEqual(result["aggregate_profile"]["unique_symbols"], 120)
        self.assertTrue(result["candidate_plan_allowed"])

    def test_write_outputs_json_csv_and_markdown(self) -> None:
        result = summarize_financial_reporting_timeliness_source_audit(
            financial_frames={"statement": _statement_rows(symbols=120, years=range(2015, 2026))},
            analysis_start_date="2015-01-01",
            analysis_end_date="2025-12-31",
            min_unique_symbols=100,
            min_end_years=8,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_financial_reporting_timeliness_source_audit(output_dir, result)

            self.assertTrue((output_dir / "financial_reporting_timeliness_source_audit.json").exists())
            self.assertTrue((output_dir / "financial_reporting_timeliness_source_profiles.csv").exists())
            self.assertTrue((output_dir / "financial_reporting_timeliness_year_coverage.csv").exists())
            self.assertTrue((output_dir / "financial_reporting_timeliness_source_audit.md").exists())


if __name__ == "__main__":
    unittest.main()
