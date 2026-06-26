import tempfile
import unittest
from pathlib import Path

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_daily_basic_valuation_coverage_audit import run_daily_basic_valuation_coverage_audit_cli
from tests.unit.test_daily_basic_valuation_coverage_audit import _daily_basic_frame


class DailyBasicValuationCoverageAuditCliTests(unittest.TestCase):
    def test_cli_reads_factor_inputs_and_writes_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            output_dir = Path(tmp) / "audit"
            DatasetStore(root).write_frame(
                _daily_basic_frame(dv_ttm_ratio=0.6, dv_ratio_ratio=1.0),
                "processed/factor_inputs",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_daily_basic_valuation_coverage_audit_cli(
                daily_basic_roots=[root],
                output_dir=output_dir,
                analysis_start_date="2025-01-01",
                analysis_end_date="2025-12-31",
            )

            self.assertEqual(result["summary"]["target_factor_count"], 2)
            self.assertTrue((output_dir / "daily_basic_valuation_coverage_audit_summary.json").exists())
            self.assertTrue((output_dir / "daily_basic_valuation_coverage_factor_coverage.csv").exists())


if __name__ == "__main__":
    unittest.main()
