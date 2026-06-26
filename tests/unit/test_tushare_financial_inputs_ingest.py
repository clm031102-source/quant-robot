import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.ingest.tushare_financial_inputs import run_tushare_fina_indicator_ingest
from quant_robot.storage.dataset_store import DatasetStore


class FakeTushareFinaIndicatorAdapter:
    def __init__(self) -> None:
        self.calls = []

    def fetch_fina_indicator(self, period: str, ts_code: str = ""):
        self.calls.append((ts_code, period))
        ann_date = {
            "20240331": "20240425",
            "20240630": "20240828",
        }[period]
        symbols = [ts_code] if ts_code else ["000001.SZ", "600519.SH"]
        return pd.DataFrame(
            {
                "symbol": symbols,
                "ann_date": [pd.to_datetime(ann_date, format="%Y%m%d").date()] * len(symbols),
                "end_date": [pd.to_datetime(period, format="%Y%m%d").date()] * len(symbols),
                "roe": [11.2 + index for index, _ in enumerate(symbols)],
                "roa": [0.92 + index for index, _ in enumerate(symbols)],
                "grossprofit_margin": [28.5 + index for index, _ in enumerate(symbols)],
                "netprofit_margin": [12.3 + index for index, _ in enumerate(symbols)],
                "netprofit_yoy": [8.7 + index for index, _ in enumerate(symbols)],
                "or_yoy": [6.5 + index for index, _ in enumerate(symbols)],
                "ocfps": [1.24 + index for index, _ in enumerate(symbols)],
                "cfps": [1.8 + index for index, _ in enumerate(symbols)],
            }
        )


class FakeEmptyFinaIndicatorAdapter(FakeTushareFinaIndicatorAdapter):
    def fetch_fina_indicator(self, period: str, ts_code: str = ""):
        self.calls.append((ts_code, period))
        return pd.DataFrame(
            columns=[
                "symbol",
                "ann_date",
                "end_date",
                "roe",
                "roa",
                "grossprofit_margin",
                "netprofit_margin",
                "netprofit_yoy",
                "or_yoy",
                "ocfps",
                "cfps",
            ]
        )


class FakeMixedEmptyFinaIndicatorAdapter(FakeTushareFinaIndicatorAdapter):
    def fetch_fina_indicator(self, period: str, ts_code: str = ""):
        if ts_code == "600519.SH":
            self.calls.append((ts_code, period))
            return pd.DataFrame(
                columns=[
                    "symbol",
                    "ann_date",
                    "end_date",
                    "roe",
                    "roa",
                    "grossprofit_margin",
                    "netprofit_margin",
                    "netprofit_yoy",
                    "or_yoy",
                    "ocfps",
                    "cfps",
                ]
            )
        return super().fetch_fina_indicator(period, ts_code=ts_code)


class FakeDuplicateFinaIndicatorAdapter(FakeTushareFinaIndicatorAdapter):
    def fetch_fina_indicator(self, period: str, ts_code: str = ""):
        frame = super().fetch_fina_indicator(period, ts_code=ts_code)
        return pd.concat([frame, frame], ignore_index=True)


class FakeSameKeyRestatedFinaIndicatorAdapter(FakeTushareFinaIndicatorAdapter):
    def fetch_fina_indicator(self, period: str, ts_code: str = ""):
        frame = super().fetch_fina_indicator(period, ts_code=ts_code)
        restated = frame.copy()
        restated.loc[:, "ocfps"] = 1.25
        return pd.concat([frame, restated], ignore_index=True)


class TushareFinancialInputsIngestTests(unittest.TestCase):
    def test_fina_indicator_ingest_writes_raw_processed_manifest_and_quality_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeTushareFinaIndicatorAdapter()

            result = run_tushare_fina_indicator_ingest(adapter, ["20240331", "20240630"], Path(tmp))

            self.assertEqual(adapter.calls, [("", "20240331"), ("", "20240630")])
            self.assertEqual(result["source"], "tushare")
            self.assertEqual(result["dataset"], "fina_indicator")
            self.assertEqual(result["processed_rows"], 4)
            self.assertTrue((Path(tmp) / "manifest.json").exists())
            self.assertTrue((Path(tmp) / "financial_input_quality_report.json").exists())
            processed = DatasetStore(Path(tmp)).read_frame(
                "processed/fina_indicator_inputs",
                {"frequency": "1q", "market": "CN", "year": "2024"},
            )
            self.assertEqual(set(processed["asset_id"]), {"CN_XSHE_000001", "CN_XSHG_600519"})
            self.assertEqual(set(processed["source"]), {"tushare_fina_indicator"})
            self.assertIn("ann_date", processed.columns)
            self.assertIn("end_date", processed.columns)
            self.assertIn("roe", processed.columns)

    def test_fina_indicator_ingest_resume_skips_completed_periods(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_tushare_fina_indicator_ingest(FakeTushareFinaIndicatorAdapter(), ["20240331", "20240630"], Path(tmp))
            second_adapter = FakeTushareFinaIndicatorAdapter()

            result = run_tushare_fina_indicator_ingest(second_adapter, ["20240331", "20240630"], Path(tmp), resume=True)

            self.assertEqual(second_adapter.calls, [])
            self.assertEqual(result["skipped_periods"], ["20240331", "20240630"])
            self.assertEqual(result["processed_rows"], 4)
            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("fina_indicator:20240331", manifest["completed"])

    def test_fina_indicator_ingest_rejects_empty_raw_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "empty raw response"):
                run_tushare_fina_indicator_ingest(FakeEmptyFinaIndicatorAdapter(), ["20240331"], Path(tmp))

            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn("fina_indicator:20240331", manifest["completed"])
            self.assertIn("fina_indicator:20240331", manifest["failed"])

    def test_fina_indicator_ingest_supports_ts_code_smoke_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeTushareFinaIndicatorAdapter()

            result = run_tushare_fina_indicator_ingest(
                adapter,
                ["20240331"],
                Path(tmp),
                ts_codes=["000001.SZ", "600519.SH"],
            )

            self.assertEqual(adapter.calls, [("000001.SZ", "20240331"), ("600519.SH", "20240331")])
            self.assertEqual(result["processed_rows"], 2)
            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("fina_indicator:000001.SZ:20240331", manifest["completed"])
            self.assertIn("fina_indicator:600519.SH:20240331", manifest["completed"])

    def test_fina_indicator_ingest_can_record_empty_symbol_periods_for_backfill_smoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeMixedEmptyFinaIndicatorAdapter()

            result = run_tushare_fina_indicator_ingest(
                adapter,
                ["20240331"],
                Path(tmp),
                ts_codes=["000001.SZ", "600519.SH"],
                empty_response_policy="record",
            )

            self.assertEqual(adapter.calls, [("000001.SZ", "20240331"), ("600519.SH", "20240331")])
            self.assertEqual(result["processed_rows"], 1)
            self.assertEqual(result["empty_requests"], ["600519.SH:20240331"])
            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["completed"]["fina_indicator:600519.SH:20240331"]["rows"], 0)
            self.assertNotIn("fina_indicator:600519.SH:20240331", manifest["failed"])

    def test_fina_indicator_ingest_resume_skips_recorded_empty_symbol_periods(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_tushare_fina_indicator_ingest(
                FakeMixedEmptyFinaIndicatorAdapter(),
                ["20240331"],
                Path(tmp),
                ts_codes=["000001.SZ", "600519.SH"],
                empty_response_policy="record",
            )
            second_adapter = FakeMixedEmptyFinaIndicatorAdapter()

            result = run_tushare_fina_indicator_ingest(
                second_adapter,
                ["20240331"],
                Path(tmp),
                ts_codes=["000001.SZ", "600519.SH"],
                resume=True,
                empty_response_policy="record",
            )

            self.assertEqual(second_adapter.calls, [])
            self.assertEqual(result["skipped_requests"], ["000001.SZ:20240331", "600519.SH:20240331"])
            self.assertEqual(result["empty_requests"], ["600519.SH:20240331"])
            self.assertEqual(result["processed_rows"], 1)

    def test_fina_indicator_ingest_deduplicates_identical_financial_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_fina_indicator_ingest(
                FakeDuplicateFinaIndicatorAdapter(),
                ["20240331"],
                Path(tmp),
                ts_codes=["000001.SZ"],
            )

            self.assertEqual(result["processed_rows"], 1)
            self.assertEqual(result["quality_report"]["duplicate_rows"], 0)
            processed = DatasetStore(Path(tmp)).read_frame(
                "processed/fina_indicator_inputs",
                {"frequency": "1q", "market": "CN", "year": "2024"},
            )
            self.assertEqual(len(processed), 1)

    def test_fina_indicator_ingest_deduplicates_same_key_restated_financial_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_fina_indicator_ingest(
                FakeSameKeyRestatedFinaIndicatorAdapter(),
                ["20240331"],
                Path(tmp),
                ts_codes=["000001.SZ"],
            )

            self.assertEqual(result["processed_rows"], 1)
            self.assertEqual(result["quality_report"]["duplicate_rows"], 0)
            processed = DatasetStore(Path(tmp)).read_frame(
                "processed/fina_indicator_inputs",
                {"frequency": "1q", "market": "CN", "year": "2024"},
            )
            self.assertEqual(len(processed), 1)
            self.assertEqual(float(processed["ocfps"].iloc[0]), 1.25)


if __name__ == "__main__":
    unittest.main()
