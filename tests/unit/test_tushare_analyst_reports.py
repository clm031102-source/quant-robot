import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.ingest.tushare_analyst_reports import run_tushare_analyst_report_cache


class TushareAnalystReportsTests(unittest.TestCase):
    def test_cache_normalizes_report_rc_windows_and_flags_row_caps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_analyst_report_cache(
                _FakeAnalystReportAdapter(),
                "2024-01-01",
                "2024-02-29",
                Path(tmp) / "reports",
                processed_output_dir=Path(tmp) / "processed",
                request_sleep_seconds=0.0,
                max_rows_per_window=1,
            )

            self.assertEqual(result["stage"], "tushare_analyst_report_cache")
            self.assertEqual(result["summary"]["windows"], 2)
            self.assertEqual(result["summary"]["rows"], 4)
            self.assertEqual(result["summary"]["assets"], 2)
            self.assertEqual(result["summary"]["row_cap_warning_windows"], 2)
            self.assertTrue(
                (
                    Path(tmp)
                    / "processed"
                    / "processed"
                    / "analyst_report_rc_window"
                    / "window_end=20240131"
                    / "window_start=20240101"
                ).exists()
            )
            self.assertTrue((Path(tmp) / "reports" / "tushare_analyst_report_cache.json").exists())


class _FakeAnalystReportAdapter:
    def fetch_report_rc(self, start_date: str = "", end_date: str = "", ts_code: str = "") -> pd.DataFrame:
        return pd.DataFrame(
            {
                "ts_code": ["000001.SZ", "600519.SH"],
                "report_date": [start_date, end_date],
                "name": ["A", "B"],
                "org_name": ["Org1", "Org2"],
                "author_name": ["Analyst1", "Analyst2"],
                "report_title": ["Title1", "Title2"],
                "report_type": ["company", "company"],
                "rating": ["买入", "增持"],
                "quarter": ["2024Q1", "2024Q1"],
                "eps": [1.0, 2.0],
                "np": [100.0, 200.0],
                "roe": [10.0, 20.0],
                "tp": [12.0, 24.0],
            }
        )


if __name__ == "__main__":
    unittest.main()
