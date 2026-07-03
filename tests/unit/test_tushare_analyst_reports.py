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

    def test_cache_records_provider_rate_limit_retry_after_seconds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_analyst_report_cache(
                _RateLimitedAnalystReportAdapter(),
                "2024-02-01",
                "2024-02-29",
                Path(tmp) / "reports",
                processed_output_dir=Path(tmp) / "processed",
                request_sleep_seconds=0.0,
            )

            self.assertEqual(result["summary"]["failed_windows"], 1)
            self.assertEqual(result["summary"]["rate_limited_windows"], 1)
            self.assertEqual(result["summary"]["next_retry_after_seconds"], 3600)
            self.assertEqual(result["failures"][0]["provider_rate_limit"], "1_per_hour")
            self.assertEqual(result["failures"][0]["retry_after_seconds"], 3600)

    def test_cache_stops_after_rate_limit_without_skipping_later_windows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_analyst_report_cache(
                _RateLimitedAnalystReportAdapter(),
                "2024-02-01",
                "2024-03-31",
                Path(tmp) / "reports",
                processed_output_dir=Path(tmp) / "processed",
                request_sleep_seconds=0.0,
            )

            self.assertTrue(result["summary"]["stopped_on_rate_limit"])
            self.assertEqual(result["summary"]["windows"], 2)
            self.assertEqual(len(result["rows_by_window"]), 1)
            self.assertEqual(result["rows_by_window"][0]["window_start"], "20240201")


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


class _RateLimitedAnalystReportAdapter:
    def fetch_report_rc(self, start_date: str = "", end_date: str = "", ts_code: str = "") -> pd.DataFrame:
        raise RuntimeError("抱歉，您访问接口(report_rc)频率超限(1次/小时)，具体频次详情：https://tushare.pro/document/1?doc_id=108。")


if __name__ == "__main__":
    unittest.main()
