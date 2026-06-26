import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.external_feed_coverage_audit import run_external_feed_coverage_audit
from quant_robot.storage.dataset_store import DatasetStore


class ExternalFeedCoverageAuditTests(unittest.TestCase):
    def test_blocks_sparse_hk_hold_and_missing_lpr_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed_root"
            output_dir = Path(tmp) / "report"
            store = DatasetStore(root)
            store.write_frame(
                pd.DataFrame(
                    {
                        "date": [
                            pd.Timestamp("2025-03-31").date(),
                            pd.Timestamp("2025-06-30").date(),
                        ],
                        "available_date": [
                            pd.Timestamp("2025-04-01").date(),
                            pd.Timestamp("2025-07-01").date(),
                        ],
                        "symbol": ["000001.SZ", "000001.SZ"],
                        "asset_id": ["CN_XSHE_000001", "CN_XSHE_000001"],
                        "hold_ratio": [2.1, 2.3],
                        "hold_vol": [1000.0, 1200.0],
                    }
                ),
                "processed/external_hk_hold",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            store.write_frame(
                pd.DataFrame(
                    {
                        "date": pd.date_range("2025-01-02", periods=65, freq="B").date,
                        "available_date": pd.date_range("2025-01-03", periods=65, freq="B").date,
                        "shibor_1m": [1.2] * 65,
                        "shibor_3m": [1.4] * 65,
                        "shibor_1y": [1.8] * 65,
                        "lpr_1y": [pd.NA] * 65,
                        "lpr_5y": [pd.NA] * 65,
                    }
                ),
                "processed/external_macro_rates",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_external_feed_coverage_audit(
                processed_root=root,
                output_dir=output_dir,
                min_hk_hold_observation_dates=25,
                max_hk_hold_median_gap_days=10,
                min_macro_observation_dates=60,
                min_lpr_non_null_ratio=0.8,
            )

            self.assertFalse(result["summary"]["external_feed_ic_or_portfolio_allowed"])
            self.assertEqual(result["summary"]["blocked_count"], 2)
            hk_hold = result["feed_coverage"]["external_hk_hold"]
            self.assertEqual(hk_hold["status"], "blocked")
            self.assertIn("hk_hold_observation_dates_below_minimum", hk_hold["blockers"])
            self.assertIn("hk_hold_frequency_not_daily_enough_for_daily_rank", hk_hold["blockers"])
            self.assertEqual(hk_hold["detected_frequency"], "quarterly_or_sparse")
            macro = result["feed_coverage"]["external_macro_rates"]
            self.assertEqual(macro["status"], "blocked")
            self.assertEqual(macro["lpr_non_null_ratio"], 0.0)
            self.assertIn("lpr_non_missing_coverage_below_threshold", macro["blockers"])
            self.assertTrue((output_dir / "external_feed_coverage_audit.json").exists())
            self.assertTrue((output_dir / "external_feed_coverage_audit.md").exists())

    def test_passes_when_hk_hold_and_lpr_coverage_are_sufficient(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed_root"
            output_dir = Path(tmp) / "report"
            store = DatasetStore(root)
            dates = pd.date_range("2025-01-02", periods=30, freq="B")
            store.write_frame(
                pd.DataFrame(
                    {
                        "date": dates.date,
                        "available_date": (dates + pd.offsets.BDay(1)).date,
                        "symbol": ["000001.SZ"] * len(dates),
                        "asset_id": ["CN_XSHE_000001"] * len(dates),
                        "hold_ratio": [2.0] * len(dates),
                        "hold_vol": [1000.0] * len(dates),
                    }
                ),
                "processed/external_hk_hold",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            store.write_frame(
                pd.DataFrame(
                    {
                        "date": dates.date,
                        "available_date": (dates + pd.offsets.BDay(1)).date,
                        "shibor_1m": [1.2] * len(dates),
                        "shibor_3m": [1.4] * len(dates),
                        "shibor_1y": [1.8] * len(dates),
                        "lpr_1y": [3.45] * len(dates),
                        "lpr_5y": [3.95] * len(dates),
                    }
                ),
                "processed/external_macro_rates",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_external_feed_coverage_audit(
                processed_root=root,
                output_dir=output_dir,
                min_hk_hold_observation_dates=25,
                max_hk_hold_median_gap_days=10,
                min_macro_observation_dates=25,
                min_lpr_non_null_ratio=0.8,
            )

            self.assertTrue(result["summary"]["external_feed_ic_or_portfolio_allowed"])
            self.assertEqual(result["summary"]["pass_count"], 2)
            self.assertEqual(result["feed_coverage"]["external_hk_hold"]["status"], "pass")
            self.assertEqual(result["feed_coverage"]["external_macro_rates"]["status"], "pass")

    def test_accepts_processed_child_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed_root"
            output_dir = Path(tmp) / "report"
            store = DatasetStore(root)
            dates = pd.date_range("2025-01-02", periods=30, freq="B")
            store.write_frame(
                pd.DataFrame(
                    {
                        "date": dates.date,
                        "available_date": (dates + pd.offsets.BDay(1)).date,
                        "symbol": ["000001.SZ"] * len(dates),
                        "hold_ratio": [2.0] * len(dates),
                        "hold_vol": [1000.0] * len(dates),
                    }
                ),
                "processed/external_hk_hold",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            store.write_frame(
                pd.DataFrame(
                    {
                        "date": dates.date,
                        "available_date": (dates + pd.offsets.BDay(1)).date,
                        "shibor_1m": [1.2] * len(dates),
                        "shibor_3m": [1.4] * len(dates),
                        "shibor_1y": [1.8] * len(dates),
                        "lpr_1y": [3.45] * len(dates),
                        "lpr_5y": [3.95] * len(dates),
                    }
                ),
                "processed/external_macro_rates",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_external_feed_coverage_audit(
                processed_root=root / "processed",
                output_dir=output_dir,
                min_hk_hold_observation_dates=25,
                max_hk_hold_median_gap_days=10,
                min_macro_observation_dates=25,
                min_lpr_non_null_ratio=0.8,
            )

            self.assertTrue(result["summary"]["external_feed_ic_or_portfolio_allowed"])


if __name__ == "__main__":
    unittest.main()
