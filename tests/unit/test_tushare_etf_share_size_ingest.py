import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.ingest.tushare_etf_share_size import run_tushare_etf_share_size_ingest
from quant_robot.storage.dataset_store import DatasetStore


class FakeTushareEtfShareSizeAdapter:
    def __init__(self) -> None:
        self.calls = []

    def fetch_trade_calendar(self, start_date: str, end_date: str):
        dates = pd.date_range(start_date, end_date, freq="D")
        return pd.DataFrame({"exchange": ["SSE"] * len(dates), "date": dates.date, "is_open": [1] * len(dates)})

    def fetch_etf_share_size_by_trade_date(self, trade_date: str, exchange: str = ""):
        self.calls.append((trade_date, exchange))
        date = pd.to_datetime(trade_date, format="%Y%m%d").date()
        if exchange == "SSE":
            day_offset = pd.Timestamp(date).day - 2
            return pd.DataFrame(
                {
                    "symbol": ["510300.SH"],
                    "date": [date],
                    "name": ["CSI 300 ETF"],
                    "total_share": [10_000_000.0 + day_offset * 100_000.0],
                    "total_size": [40_000_000.0 + day_offset * 800_000.0],
                    "nav": [4.0],
                    "close": [4.04],
                    "exchange": ["SSE"],
                }
            )
        day_offset = pd.Timestamp(date).day - 2
        return pd.DataFrame(
            {
                "symbol": ["159915.SZ"],
                "date": [date],
                "name": ["ChiNext ETF"],
                "total_share": [20_000_000.0 + day_offset * 200_000.0],
                "total_size": [40_000_000.0 + day_offset * 400_000.0],
                "nav": [2.0],
                "close": [1.98],
                "exchange": ["SZSE"],
            }
        )


class FakeInvalidTushareEtfShareSizeAdapter(FakeTushareEtfShareSizeAdapter):
    def fetch_etf_share_size_by_trade_date(self, trade_date: str, exchange: str = ""):
        self.calls.append((trade_date, exchange))
        return pd.DataFrame({"symbol": ["BAD"], "date": [pd.Timestamp("2024-01-02").date()]})


class TushareEtfShareSizeIngestTests(unittest.TestCase):
    def test_etf_share_size_ingest_writes_raw_processed_manifest_and_quality_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeTushareEtfShareSizeAdapter()

            result = run_tushare_etf_share_size_ingest(
                adapter,
                "2024-01-02",
                "2024-01-03",
                Path(tmp),
                exchanges=("SSE", "SZSE"),
            )

            self.assertEqual(
                adapter.calls,
                [
                    ("20240102", "SSE"),
                    ("20240102", "SZSE"),
                    ("20240103", "SSE"),
                    ("20240103", "SZSE"),
                ],
            )
            self.assertEqual(result["source"], "tushare")
            self.assertEqual(result["dataset"], "etf_share_size")
            self.assertEqual(result["market"], "CN_ETF")
            self.assertEqual(result["processed_rows"], 4)
            self.assertTrue((Path(tmp) / "manifest.json").exists())
            self.assertTrue((Path(tmp) / "etf_share_size_quality_report.json").exists())
            processed = DatasetStore(Path(tmp)).read_frame(
                "processed/etf_share_size",
                {"frequency": "1d", "market": "CN_ETF", "year": "2024"},
            )
            self.assertEqual(set(processed["asset_id"]), {"CN_ETF_XSHG_510300", "CN_ETF_XSHE_159915"})
            self.assertEqual(set(processed["source"]), {"tushare_etf_share_size"})
            self.assertIn("share_change_1d", processed.columns)
            self.assertIn("size_change_1d", processed.columns)
            self.assertIn("nav_premium_discount", processed.columns)
            csi_300 = processed[processed["asset_id"] == "CN_ETF_XSHG_510300"].sort_values("date").reset_index(drop=True)
            self.assertTrue(pd.isna(csi_300.loc[0, "share_change_1d"]))
            self.assertAlmostEqual(csi_300.loc[1, "share_change_1d"], 0.01)
            self.assertAlmostEqual(csi_300.loc[0, "nav_premium_discount"], 0.01)

    def test_etf_share_size_ingest_resume_skips_completed_exchange_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_tushare_etf_share_size_ingest(
                FakeTushareEtfShareSizeAdapter(),
                "2024-01-02",
                "2024-01-02",
                Path(tmp),
                exchanges=("SSE", "SZSE"),
            )
            second_adapter = FakeTushareEtfShareSizeAdapter()

            result = run_tushare_etf_share_size_ingest(
                second_adapter,
                "2024-01-02",
                "2024-01-02",
                Path(tmp),
                exchanges=("SSE", "SZSE"),
                resume=True,
            )

            self.assertEqual(second_adapter.calls, [])
            self.assertEqual(result["skipped_exchange_trade_dates"], ["SSE:20240102", "SZSE:20240102"])
            self.assertEqual(result["processed_rows"], 2)
            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("etf_share_size:SSE:20240102", manifest["completed"])
            self.assertIn("etf_share_size:SZSE:20240102", manifest["completed"])

    def test_etf_share_size_ingest_resume_reuses_raw_partitions_without_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            DatasetStore(root).write_frame(
                pd.DataFrame(
                    {
                        "symbol": ["510300.SH"],
                        "date": [pd.Timestamp("2024-01-02").date()],
                        "name": ["CSI 300 ETF"],
                        "total_share": [10_000_000.0],
                        "total_size": [40_000_000.0],
                        "nav": [4.0],
                        "close": [4.04],
                        "exchange": ["SSE"],
                    }
                ),
                "raw/tushare/etf_share_size",
                {"exchange": "SSE", "trade_date": "20240102"},
            )

            adapter = FakeTushareEtfShareSizeAdapter()
            result = run_tushare_etf_share_size_ingest(
                adapter,
                "2024-01-02",
                "2024-01-02",
                root,
                exchanges=("SSE", "SZSE"),
                resume=True,
            )

            self.assertEqual(adapter.calls, [("20240102", "SZSE")])
            self.assertEqual(result["downloaded_exchange_trade_dates"], ["SZSE:20240102"])
            self.assertEqual(result["reused_raw_exchange_trade_dates"], ["SSE:20240102"])
            self.assertEqual(result["skipped_exchange_trade_dates"], ["SSE:20240102"])
            self.assertEqual(result["processed_rows"], 2)
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("etf_share_size:SSE:20240102", manifest["completed"])
            self.assertIn("etf_share_size:SZSE:20240102", manifest["completed"])

    def test_etf_share_size_ingest_marks_failed_when_processing_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_tushare_etf_share_size_ingest(
                    FakeInvalidTushareEtfShareSizeAdapter(),
                    "2024-01-02",
                    "2024-01-02",
                    Path(tmp),
                    exchanges=("SSE",),
                )

            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn("etf_share_size:SSE:20240102", manifest["completed"])
            self.assertIn("etf_share_size:SSE:20240102", manifest["failed"])


if __name__ == "__main__":
    unittest.main()
