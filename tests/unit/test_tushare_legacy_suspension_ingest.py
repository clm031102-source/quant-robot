import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.ingest.tushare_legacy_suspension import run_tushare_legacy_suspension_ingest
from quant_robot.storage.dataset_store import DatasetStore


class FakeLegacySuspensionAdapter:
    def __init__(self, *, duplicate: bool = False, mismatched_symbol: bool = False) -> None:
        self.duplicate = duplicate
        self.mismatched_symbol = mismatched_symbol
        self.calls: list[tuple[str, str, str]] = []

    def fetch_legacy_suspension(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        self.calls.append((ts_code, start_date, end_date))
        rows = 2 if self.duplicate else 1
        return pd.DataFrame(
            {
                "ts_code": ["999999.SZ" if self.mismatched_symbol else ts_code] * rows,
                "suspend_date": ["20190429"] * rows,
                "resume_date": ["19000101"] * rows,
                "suspend_reason": ["major event"] * rows,
            }
        )


class MixedWindowLegacySuspensionAdapter:
    def fetch_legacy_suspension(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "ts_code": [ts_code, ts_code, ts_code],
                "suspend_date": ["20080102", "20170103", "20190429"],
                "resume_date": ["20080103", "20170103", "20220505"],
                "suspend_reason": ["old", "intraday", "major event"],
            }
        )


class TushareLegacySuspensionIngestTests(unittest.TestCase):
    def test_ingest_is_targeted_normalizes_open_end_and_writes_dataset(self):
        adapter = FakeLegacySuspensionAdapter()
        unresolved = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_002260"],
                "symbol": ["002260.SZ"],
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            report = run_tushare_legacy_suspension_ingest(
                adapter,
                unresolved,
                "2015-01-01",
                "2025-12-31",
                tmp,
            )

            self.assertEqual(adapter.calls, [("002260.SZ", "2015-01-01", "2025-12-31")])
            self.assertEqual(report["summary"]["requested_assets"], 1)
            self.assertEqual(report["summary"]["interval_rows"], 1)
            self.assertEqual(report["evidence_scope"], "data_quality_only")
            frame = DatasetStore(tmp).read_frame(
                "processed/legacy_suspension",
                {"market": "CN", "window": "20150101_20251231"},
            )
            self.assertEqual(frame.loc[0, "asset_id"], "CN_XSHE_002260")
            self.assertTrue(pd.isna(frame.loc[0, "resume_date"]))
            payload = json.loads(
                (Path(tmp) / "tushare_legacy_suspension_ingestion_report.json").read_text(encoding="utf-8")
            )
            self.assertFalse(payload["live_boundary_allowed"])

    def test_ingest_uses_explicit_historical_provider_symbol_mapping(self):
        adapter = FakeLegacySuspensionAdapter()
        unresolved = pd.DataFrame(
            {
                "asset_id": ["CN_XBEI_920039"],
                "symbol": ["920039.BJ"],
                "provider_symbol": ["831039.BJ"],
            }
        )

        with tempfile.TemporaryDirectory() as tmp:
            report = run_tushare_legacy_suspension_ingest(
                adapter,
                unresolved,
                "2015-01-01",
                "2025-12-31",
                tmp,
                provider_mapping_source="official-bse-map.html#sha256=test",
            )

            self.assertEqual(adapter.calls, [("831039.BJ", "2015-01-01", "2025-12-31")])
            self.assertEqual(report["summary"]["mapped_provider_symbols"], 1)
            self.assertEqual(report["provider_mapping_source"], "official-bse-map.html#sha256=test")
            frame = DatasetStore(tmp).read_frame(
                "processed/legacy_suspension",
                {"market": "CN", "window": "20150101_20251231"},
            )
            self.assertEqual(frame.loc[0, "asset_id"], "CN_XBEI_920039")
            self.assertEqual(frame.loc[0, "symbol"], "920039.BJ")
            self.assertEqual(frame.loc[0, "provider_symbol"], "831039.BJ")

    def test_rejects_duplicate_intervals_and_provider_symbol_mismatch(self):
        unresolved = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_002260"],
                "symbol": ["002260.SZ"],
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "duplicate legacy suspension intervals"):
                run_tushare_legacy_suspension_ingest(
                    FakeLegacySuspensionAdapter(duplicate=True),
                    unresolved,
                    "2015-01-01",
                    "2025-12-31",
                    tmp,
                )

    def test_ignores_out_of_window_and_same_day_intraday_events(self):
        unresolved = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_002260"],
                "symbol": ["002260.SZ"],
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            report = run_tushare_legacy_suspension_ingest(
                MixedWindowLegacySuspensionAdapter(),
                unresolved,
                "2015-01-01",
                "2025-12-31",
                tmp,
            )

            self.assertEqual(report["summary"]["out_of_window_rows_ignored"], 1)
            self.assertEqual(report["summary"]["intraday_rows_ignored"], 1)
            self.assertEqual(report["summary"]["interval_rows"], 1)
            frame = DatasetStore(tmp).read_frame(
                "processed/legacy_suspension",
                {"market": "CN", "window": "20150101_20251231"},
            )
            self.assertEqual(str(frame.loc[0, "suspend_date"]), "2019-04-29")
            with self.assertRaisesRegex(ValueError, "unexpected symbols"):
                run_tushare_legacy_suspension_ingest(
                    FakeLegacySuspensionAdapter(mismatched_symbol=True),
                    unresolved,
                    "2015-01-01",
                    "2025-12-31",
                    tmp,
                )

    def test_rejects_ambiguous_or_unbounded_request_lists(self):
        duplicate = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_002260", "CN_XSHE_002260"],
                "symbol": ["002260.SZ", "002260.SZ"],
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "unique asset_id"):
                run_tushare_legacy_suspension_ingest(
                    FakeLegacySuspensionAdapter(),
                    duplicate,
                    "2015-01-01",
                    "2025-12-31",
                    tmp,
                )

            too_many = pd.DataFrame(
                {
                    "asset_id": [f"CN_XSHE_{index:06d}" for index in range(101)],
                    "symbol": [f"{index:06d}.SZ" for index in range(101)],
                }
            )
            with self.assertRaisesRegex(ValueError, "at most 100"):
                run_tushare_legacy_suspension_ingest(
                    FakeLegacySuspensionAdapter(),
                    too_many,
                    "2015-01-01",
                    "2025-12-31",
                    tmp,
                )


if __name__ == "__main__":
    unittest.main()
