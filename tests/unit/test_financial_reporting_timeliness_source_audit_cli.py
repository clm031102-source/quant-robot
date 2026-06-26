import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_financial_reporting_timeliness_source_audit import (
    run_financial_reporting_timeliness_source_audit_cli,
)


class FinancialReportingTimelinessSourceAuditCliTests(unittest.TestCase):
    def test_cli_writes_source_audit_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = root / "source"
            output_dir = root / "out"
            source_root.mkdir()
            pd.DataFrame(
                {
                    "symbol": ["000001.SZ", "000002.SZ"],
                    "ann_date": ["20260430", "20260429"],
                    "end_date": ["20251231", "20251231"],
                    "report_type": ["1", "1"],
                }
            ).to_parquet(source_root / "part-00000.parquet")

            result = run_financial_reporting_timeliness_source_audit_cli(
                financial_roots=(source_root,),
                output_dir=output_dir,
                analysis_start_date="2025-01-01",
                analysis_end_date="2025-12-31",
                min_unique_symbols=1,
                min_end_years=1,
            )

            self.assertEqual(result["status"], "source_ready")
            saved = json.loads((output_dir / "financial_reporting_timeliness_source_audit.json").read_text())
            self.assertEqual(saved["status"], "source_ready")
            self.assertTrue((output_dir / "financial_reporting_timeliness_source_audit.md").exists())

    def test_cli_expands_processed_root_and_ignores_non_financial_parquet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed_root = root / "data" / "processed"
            statement_root = processed_root / "round999_financial_statement_source"
            unrelated_root = processed_root / "daily_bars"
            statement_root.mkdir(parents=True)
            unrelated_root.mkdir()
            pd.DataFrame(
                {
                    "symbol": ["000001.SZ", "000002.SZ"],
                    "ann_date": ["20260430", "20260429"],
                    "end_date": ["20251231", "20251231"],
                    "report_type": ["1", "1"],
                    "large_unused_field": [1.0, 2.0],
                }
            ).to_parquet(statement_root / "part-00000.parquet")
            pd.DataFrame(
                {
                    "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002"],
                    "date": ["2025-12-31", "2025-12-31"],
                    "close": [10.0, 20.0],
                }
            ).to_parquet(unrelated_root / "bars.parquet")

            result = run_financial_reporting_timeliness_source_audit_cli(
                financial_roots=(processed_root,),
                output_dir=root / "out",
                analysis_start_date="2025-01-01",
                analysis_end_date="2025-12-31",
                min_unique_symbols=1,
                min_end_years=1,
            )

            self.assertEqual(result["summary"]["source_count"], 1)
            self.assertEqual(result["summary"]["row_count"], 2)
            self.assertEqual(result["summary"]["unique_symbols"], 2)
            self.assertEqual(result["status"], "source_ready")


if __name__ == "__main__":
    unittest.main()
