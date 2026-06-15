import unittest

import pandas as pd

from quant_robot.data.quality_report import build_quality_report


class QualityReportTests(unittest.TestCase):
    def test_report_counts_duplicates_zero_volume_and_missing_dates(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["A", "A", "A", "B"],
                "market": ["CN", "CN", "CN", "CN"],
                "date": [
                    pd.Timestamp("2024-01-02").date(),
                    pd.Timestamp("2024-01-02").date(),
                    pd.Timestamp("2024-01-04").date(),
                    pd.Timestamp("2024-01-02").date(),
                ],
                "timestamp": pd.to_datetime(
                    ["2024-01-02", "2024-01-02", "2024-01-04", "2024-01-02"], utc=True
                ),
                "frequency": ["1d", "1d", "1d", "1d"],
                "source": ["fixture", "fixture", "fixture", "fixture"],
                "open": [1.0, 1.0, 1.2, 2.0],
                "high": [1.1, 1.1, 1.3, 2.1],
                "low": [0.9, 0.9, 1.1, 1.9],
                "close": [1.0, 1.0, 1.2, 2.0],
                "volume": [100.0, 100.0, 0.0, 200.0],
            }
        )

        report = build_quality_report(bars)

        self.assertEqual(report["duplicate_bars"], 1)
        self.assertEqual(report["zero_volume_rows"], 1)
        self.assertEqual(report["assets"], 2)
        self.assertEqual(report["missing_date_rows"], 1)
        self.assertIn("extreme_return_rows", report)
        self.assertIn("stale_price_rows", report)
        self.assertIn("adj_close_jump_rows", report)

    def test_report_uses_expected_trading_dates_when_provided(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["A", "A"],
                "market": ["CN", "CN"],
                "date": [pd.Timestamp("2024-01-05").date(), pd.Timestamp("2024-01-08").date()],
                "volume": [100.0, 100.0],
            }
        )

        report = build_quality_report(
            bars,
            expected_dates=[pd.Timestamp("2024-01-05").date(), pd.Timestamp("2024-01-08").date()],
        )

        self.assertEqual(report["missing_date_rows"], 0)

    def test_report_counts_extreme_stale_and_adjustment_anomalies(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["A"] * 5,
                "market": ["CN"] * 5,
                "date": pd.date_range("2024-01-02", periods=5).date,
                "volume": [100.0, 100.0, 100.0, 100.0, 100.0],
                "close": [10.0, 10.0, 10.0, 10.0, 15.0],
                "adj_close": [10.0, 10.0, 10.0, 10.0, 30.0],
            }
        )

        report = build_quality_report(bars)

        self.assertEqual(report["extreme_return_rows"], 1)
        self.assertGreaterEqual(report["stale_price_rows"], 1)
        self.assertEqual(report["adj_close_jump_rows"], 1)


if __name__ == "__main__":
    unittest.main()
