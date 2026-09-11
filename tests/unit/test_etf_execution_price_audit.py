import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.data.etf_execution_price_audit import BAR_COLUMNS, _read_partition, audit_price_frames, run_execution_price_audit


def prices():
    raw = pd.DataFrame({"symbol": ["510300.SH", "510300.SH"],
        "date": ["2024-01-02", "2024-01-03"], "open": [10.0, 9.0], "high": [10.0, 9.0],
        "low": [10.0, 9.0], "close": [10.0, 9.0], "volume": [100, 100], "amount": [1000, 900]})
    bars = raw.assign(asset_id="CN_ETF_XSHG_510300", market="CN_ETF", frequency="1d",
                      source="tushare", adjusted=False, adj_close=raw.close)
    return bars, raw


class ExecutionPriceAuditTests(unittest.TestCase):
    def test_matching_raw_prices_do_not_certify_adjustment_or_accounting(self):
        result = audit_price_frames(*prices(), expected_dates=["2024-01-02", "2024-01-03"])
        self.assertTrue(result["local_raw_reconciliation_passed"])
        self.assertEqual(result["summary"]["adj_close_equals_close_rows"], 2)
        self.assertEqual(result["summary"]["adjusted_true_rows"], 0)
        self.assertFalse(result["execution_accounting_source_verified"])
        self.assertIn("corporate_action_history_not_audited", result["remaining_requirements"])

    def test_price_mismatch_missing_raw_and_duplicate_keys_fail(self):
        for mode in ("price", "missing", "duplicate", "extra"):
            with self.subTest(mode=mode):
                bars, raw = prices()
                if mode == "price":
                    bars.loc[0, "close"] = 20
                elif mode == "missing":
                    raw = raw.iloc[:1]
                elif mode == "duplicate":
                    bars = pd.concat([bars, bars.iloc[:1]], ignore_index=True)
                else:
                    raw = pd.concat([raw, raw.iloc[:1].assign(symbol="159915.SZ")], ignore_index=True)
                result = audit_price_frames(bars, raw, expected_dates=["2024-01-02", "2024-01-03"])
                self.assertFalse(result["local_raw_reconciliation_passed"])

    def test_equal_invalid_prices_and_wrong_asset_mapping_fail(self):
        for mode in ("nan", "zero", "asset", "source", "adjusted_label"):
            with self.subTest(mode=mode):
                bars, raw = prices()
                if mode in {"nan", "zero"}:
                    bars.loc[0, "close"] = raw.loc[0, "close"] = float("nan") if mode == "nan" else 0
                elif mode == "asset":
                    bars.loc[0, "asset_id"] = "CN_ETF_XSHE_510300"
                elif mode == "source":
                    bars.loc[0, "source"] = "fixture"
                else:
                    bars["adjusted"] = bars.adjusted.astype(object)
                    bars.loc[0, "adjusted"] = "False"
                self.assertFalse(audit_price_frames(bars, raw,
                    expected_dates=["2024-01-02", "2024-01-03"])["local_raw_reconciliation_passed"])

    def test_missing_whole_market_session_fails_even_when_raw_and_processed_match(self):
        result = audit_price_frames(*prices(), expected_dates=["2024-01-02", "2024-01-03", "2024-01-04"])
        self.assertEqual(result["summary"]["missing_sessions"], ["2024-01-04"])
        self.assertFalse(result["local_raw_reconciliation_passed"])

    def test_applied_adjustment_is_described_without_inferring_source_completeness(self):
        bars, raw = prices()
        bars["adjusted"] = True
        bars["adj_close"] = [9, 9]
        result = audit_price_frames(bars, raw, expected_dates=["2024-01-02", "2024-01-03"])
        self.assertTrue(result["local_raw_reconciliation_passed"])
        self.assertEqual(result["summary"]["adj_close_differs_from_close_rows"], 1)
        self.assertFalse(result["execution_accounting_source_verified"])

    def test_end_to_end_audit_never_reads_unselected_holdout_partition(self):
        from quant_robot.storage.dataset_store import DatasetStore
        from quant_robot.data.cn_trading_calendar import build_cn_trading_calendar, write_cn_trading_calendar
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars, raw = prices()
            bars["date"] = pd.to_datetime(bars.date).dt.date
            raw["date"] = pd.to_datetime(raw.date).dt.date
            store = DatasetStore(root / "authority")
            store.write_frame(bars, "processed/bars", {"frequency": "1d", "market": "CN_ETF", "year": "2024"})
            for session, rows in raw.groupby("date"):
                store.write_frame(rows, "raw/tushare/fund_daily", {"trade_date": session.strftime("%Y%m%d")})
            (root / "authority/manifest.json").write_text(json.dumps({"completed": {
                "CN_ETF:daily:20240102": {"rows": 1}, "CN_ETF:daily:20240103": {"rows": 1}}}))
            bad = root / "authority/processed/bars/frequency=1d/market=CN_ETF/year=2026"
            bad.mkdir()
            (bad / "part-00000.parquet").write_bytes(b"must never read holdout")
            exchange = pd.DataFrame({"date": ["2024-01-02", "2024-01-03"], "is_open": [1, 1]})
            calendar, manifest = build_cn_trading_calendar({"SSE": exchange, "SZSE": exchange},
                start_date="2024-01-02", end_date="2024-01-03")
            write_cn_trading_calendar(root / "calendar", calendar, manifest)
            result = run_execution_price_audit(data_root=root / "authority", start_date="2024-01-02",
                end_date="2024-01-03", calendar_path=root / "calendar/cn_trading_calendar.csv",
                calendar_manifest_path=root / "calendar/cn_trading_calendar_manifest.json")
            self.assertTrue(result["local_raw_reconciliation_passed"], result["blockers"])
            self.assertEqual(len(result["input_files"]), 9)
            self.assertTrue(all("year=2026" not in x["path"] for x in result["input_files"]))
            with self.assertRaisesRegex(ValueError, "calendar.*cover"):
                run_execution_price_audit(data_root=root / "authority", start_date="2024-01-02",
                    end_date="2024-01-04", calendar_path=root / "calendar/cn_trading_calendar.csv",
                    calendar_manifest_path=root / "calendar/cn_trading_calendar_manifest.json")
            store.write_frame(raw, "raw/tushare/fund_daily", {"trade_date": "20240102"})
            with self.assertRaisesRegex(ValueError, "partition.*date"):
                run_execution_price_audit(data_root=root / "authority", start_date="2024-01-02",
                    end_date="2024-01-03", calendar_path=root / "calendar/cn_trading_calendar.csv",
                    calendar_manifest_path=root / "calendar/cn_trading_calendar_manifest.json")
            with self.assertRaisesRegex(ValueError, "holdout"):
                run_execution_price_audit(data_root=root / "authority", start_date="2024-01-02",
                    end_date="2026-01-01", calendar_path=root / "calendar/cn_trading_calendar.csv",
                    calendar_manifest_path=root / "calendar/cn_trading_calendar_manifest.json")

    def test_partial_window_csv_is_rejected_before_price_values_are_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            prices()[0].to_csv(path / "part-00000.csv", index=False)
            original = pd.read_csv
            def read(file, **kwargs):
                self.assertEqual(kwargs["usecols"], ["date"], "out-of-scope price values were requested")
                return original(file, **kwargs)
            with patch("pandas.read_csv", side_effect=read), self.assertRaisesRegex(ValueError, "CSV.*window"):
                _read_partition(path, BAR_COLUMNS, date(2024, 1, 2), date(2024, 1, 2), {})

    def test_partial_parquet_window_projects_only_allowed_prices(self):
        import pyarrow.dataset as ds
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            bars, _ = prices()
            bars["date"] = pd.to_datetime(bars.date).dt.date
            bars.to_parquet(path / "part-00000.parquet", index=False)
            original = ds.dataset
            observed = []
            class ProjectedDataset:
                def __init__(self, *args, **kwargs):
                    self.inner = original(*args, **kwargs)
                def to_table(self, *, columns, filter):
                    self_filter = filter
                    table = self.inner.to_table(columns=columns, filter=self_filter)
                    observed.extend(table["date"].to_pylist())
                    return table
            with patch("pyarrow.dataset.dataset", side_effect=ProjectedDataset):
                frames = _read_partition(path, BAR_COLUMNS, date(2024, 1, 2), date(2024, 1, 2), {})
            self.assertEqual(observed, [date(2024, 1, 2)])
            self.assertEqual(sum(len(frame) for frame in frames), 1)
