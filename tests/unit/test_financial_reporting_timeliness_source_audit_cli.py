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


if __name__ == "__main__":
    unittest.main()
