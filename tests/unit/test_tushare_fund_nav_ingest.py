import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd

from quant_robot.data.ingest.tushare_fund_nav import (
    CANONICAL_COLUMNS,
    TushareFundNavIngestResult,
    build_tushare_fund_nav_request_plan,
    canonicalize_tushare_fund_nav,
    run_tushare_fund_nav_ingest,
)


class TushareFundNavIngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sessions = pd.to_datetime(
            [
                "2020-01-02",
                "2020-01-03",
                "2020-01-06",
                "2020-01-07",
                "2020-01-08",
            ]
        )

    def test_build_request_plan_clips_each_asset_to_its_lifetime(self):
        universe = pd.DataFrame(
            {
                "etf_code": ["510300.SH", "159901.SZ", "510999.SH"],
                "market_exchange": ["SSE", "SZSE", "SSE"],
                "list_date": ["2012-05-28", "2004-12-10", "2025-01-01"],
                "delist_date": [None, "2021-06-30", None],
            }
        )

        result = build_tushare_fund_nav_request_plan(
            universe,
            start_date="2020-01-02",
            end_date="2024-06-28",
        )

        self.assertEqual(result["symbol"].tolist(), ["159901.SZ", "510300.SH"])
        by_symbol = result.set_index("symbol")
        self.assertEqual(str(by_symbol.loc["159901.SZ", "request_end"]), "2021-06-30")
        self.assertEqual(str(by_symbol.loc["510300.SH", "request_start"]), "2020-01-02")
        self.assertEqual(by_symbol.loc["510300.SH", "asset_id"], "CN_ETF_XSHG_510300")

    def test_build_request_plan_rejects_invalid_exchange_suffix(self):
        universe = pd.DataFrame(
            {
                "etf_code": ["510300.SZ"],
                "market_exchange": ["SSE"],
                "list_date": ["2012-05-28"],
                "delist_date": [None],
            }
        )

        with self.assertRaisesRegex(ValueError, "exchange"):
            build_tushare_fund_nav_request_plan(
                universe,
                start_date="2020-01-02",
                end_date="2024-06-28",
            )

    def test_canonicalize_prefers_latest_announced_revision(self):
        raw = pd.DataFrame(
            {
                "symbol": ["510300.SH", "510300.SH"],
                "nav_date": ["2020-01-02", "2020-01-02"],
                "ann_date": ["2020-01-03", "2020-01-06"],
                "unit_nav": [4.0, 4.1],
                "update_flag": [0.0, 1.0],
            }
        )

        result = canonicalize_tushare_fund_nav(raw, self.sessions)

        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result.loc[0, "unit_nav"], 4.1)
        self.assertEqual(str(result.loc[0, "known_from"]), "2020-01-07")
        self.assertTrue(bool(result.loc[0, "is_pit_usable"]))

    def test_canonicalize_prefers_higher_update_flag_on_same_announcement(self):
        raw = pd.DataFrame(
            {
                "symbol": ["159901.SZ", "159901.SZ"],
                "nav_date": ["2020-01-02", "2020-01-02"],
                "ann_date": ["2020-01-03", "2020-01-03"],
                "unit_nav": [1.0, 1.01],
                "update_flag": [0.0, 1.0],
            }
        )

        result = canonicalize_tushare_fund_nav(raw, self.sessions)

        self.assertAlmostEqual(result.loc[0, "unit_nav"], 1.01)

    def test_canonicalize_rejects_unresolved_value_conflict(self):
        raw = pd.DataFrame(
            {
                "symbol": ["510300.SH", "510300.SH"],
                "nav_date": ["2020-01-02", "2020-01-02"],
                "ann_date": ["2020-01-03", "2020-01-03"],
                "unit_nav": [4.0, 4.1],
                "update_flag": [1.0, 1.0],
            }
        )

        with self.assertRaisesRegex(ValueError, "conflicting"):
            canonicalize_tushare_fund_nav(raw, self.sessions)

    def test_canonicalize_uses_first_official_session_strictly_after_both_dates(self):
        raw = pd.DataFrame(
            {
                "symbol": ["510300.SH"],
                "nav_date": ["2020-01-02"],
                "ann_date": ["2020-01-03"],
                "unit_nav": [4.0],
                "update_flag": [0.0],
            }
        )

        result = canonicalize_tushare_fund_nav(raw, self.sessions)

        self.assertEqual(str(result.loc[0, "known_from"]), "2020-01-06")

    def test_canonicalize_keeps_invalid_announcement_lag_as_unusable(self):
        raw = pd.DataFrame(
            {
                "symbol": ["510300.SH"],
                "nav_date": ["2020-01-03"],
                "ann_date": ["2020-01-02"],
                "unit_nav": [4.0],
                "update_flag": [0.0],
            }
        )

        result = canonicalize_tushare_fund_nav(raw, self.sessions)

        self.assertTrue(pd.isna(result.loc[0, "known_from"]))
        self.assertFalse(bool(result.loc[0, "is_pit_usable"]))

    def test_canonicalize_does_not_guess_when_no_later_session_exists(self):
        raw = pd.DataFrame(
            {
                "symbol": ["510300.SH"],
                "nav_date": ["2020-01-08"],
                "ann_date": ["2020-01-08"],
                "unit_nav": [4.0],
                "update_flag": [0.0],
            }
        )

        result = canonicalize_tushare_fund_nav(raw, self.sessions)

        self.assertTrue(pd.isna(result.loc[0, "known_from"]))
        self.assertFalse(bool(result.loc[0, "is_pit_usable"]))

    def test_canonicalize_has_only_source_fields(self):
        raw = pd.DataFrame(
            {
                "symbol": ["510300.SH"],
                "nav_date": ["2020-01-02"],
                "ann_date": ["2020-01-03"],
                "unit_nav": [4.0],
            }
        )

        result = canonicalize_tushare_fund_nav(raw, self.sessions)

        self.assertEqual(list(result.columns), CANONICAL_COLUMNS)
        forbidden_tokens = ("return", "label", "signal", "score", "rank", "portfolio")
        self.assertFalse(any(token in column for column in result.columns for token in forbidden_tokens))

    def test_canonicalize_does_not_dispatch_one_python_call_per_asset_date(self):
        dates = pd.date_range("2020-01-02", periods=20, freq="B")
        rows = []
        for index in range(10):
            symbol = f"{510000 + index:06d}.SH"
            for date in dates:
                rows.append(
                    {
                        "symbol": symbol,
                        "nav_date": date,
                        "ann_date": date,
                        "unit_nav": 1.0,
                        "update_flag": 1.0,
                    }
                )
        raw = pd.DataFrame(rows)
        sessions = pd.date_range("2020-01-02", periods=21, freq="B")

        with patch(
            "quant_robot.data.ingest.tushare_fund_nav._select_revision",
            side_effect=AssertionError("per-group Python revision dispatch"),
            create=True,
        ):
            result = canonicalize_tushare_fund_nav(raw, sessions)

        self.assertEqual(len(result), len(raw))

    def test_ingest_is_resumable_and_preserves_stable_hashes(self):
        class FakeAdapter:
            def __init__(self):
                self.calls = []

            def fetch_fund_nav(self, ts_code, start_date="", end_date="", market="E"):
                self.calls.append((ts_code, start_date, end_date, market))
                return _provider_frame(ts_code)

        universe = _target_universe(["510300.SH"])
        first_adapter = FakeAdapter()
        with TemporaryDirectory() as directory:
            first = run_tushare_fund_nav_ingest(
                adapter=first_adapter,
                target_universe=universe,
                trading_sessions=self.sessions,
                output_dir=directory,
                start_date="2020-01-02",
                end_date="2020-01-03",
                request_sleep_seconds=0.0,
            )
            first_manifest = json.loads(Path(first.manifest_path).read_text(encoding="utf-8"))
            second_adapter = FakeAdapter()
            second = run_tushare_fund_nav_ingest(
                adapter=second_adapter,
                target_universe=universe,
                trading_sessions=self.sessions,
                output_dir=directory,
                start_date="2020-01-02",
                end_date="2020-01-03",
                request_sleep_seconds=0.0,
            )
            second_manifest = json.loads(Path(second.manifest_path).read_text(encoding="utf-8"))

            self.assertIsInstance(first, TushareFundNavIngestResult)
            self.assertEqual(len(first_adapter.calls), 1)
            self.assertEqual(second_adapter.calls, [])
            self.assertEqual(first.summary["request_summary"]["completed"], 1)
            self.assertEqual(second.summary["request_summary"]["resumed"], 1)
            self.assertEqual(
                first_manifest["requests"]["510300.SH"]["response_sha256"],
                second_manifest["requests"]["510300.SH"]["response_sha256"],
            )
            self.assertTrue(Path(first.canonical_path).exists())

    def test_ingest_records_deterministic_empty_as_terminal(self):
        class EmptyAdapter:
            def fetch_fund_nav(self, ts_code, start_date="", end_date="", market="E"):
                return pd.DataFrame()

        with TemporaryDirectory() as directory:
            result = run_tushare_fund_nav_ingest(
                adapter=EmptyAdapter(),
                target_universe=_target_universe(["159901.SZ"]),
                trading_sessions=self.sessions,
                output_dir=directory,
                start_date="2020-01-02",
                end_date="2020-01-03",
                request_sleep_seconds=0.0,
            )
            manifest_text = Path(result.manifest_path).read_text(encoding="utf-8")

        self.assertEqual(result.summary["request_summary"]["empty"], 1)
        self.assertIn('"status": "empty"', manifest_text)

    def test_ingest_records_failure_without_leaking_exception_secret(self):
        class FailingAdapter:
            def fetch_fund_nav(self, ts_code, start_date="", end_date="", market="E"):
                raise RuntimeError("provider rejected token=super-secret-value")

        with TemporaryDirectory() as directory:
            result = run_tushare_fund_nav_ingest(
                adapter=FailingAdapter(),
                target_universe=_target_universe(["510300.SH"]),
                trading_sessions=self.sessions,
                output_dir=directory,
                start_date="2020-01-02",
                end_date="2020-01-03",
                request_sleep_seconds=0.0,
            )
            manifest_text = Path(result.manifest_path).read_text(encoding="utf-8")

        self.assertEqual(result.summary["request_summary"]["failed"], 1)
        self.assertIn('"status": "failed"', manifest_text)
        self.assertNotIn("super-secret-value", manifest_text)
        self.assertNotIn("token=", manifest_text)

    def test_ingest_has_a_terminal_state_for_every_request(self):
        class MixedAdapter:
            def fetch_fund_nav(self, ts_code, start_date="", end_date="", market="E"):
                if ts_code == "159901.SZ":
                    return pd.DataFrame()
                return _provider_frame(ts_code)

        with TemporaryDirectory() as directory:
            result = run_tushare_fund_nav_ingest(
                adapter=MixedAdapter(),
                target_universe=_target_universe(["159901.SZ", "510300.SH"]),
                trading_sessions=self.sessions,
                output_dir=directory,
                start_date="2020-01-02",
                end_date="2020-01-03",
                request_sleep_seconds=0.0,
            )

        summary = result.summary["request_summary"]
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["completed"] + summary["empty"] + summary["failed"], 2)


def _target_universe(symbols):
    return pd.DataFrame(
        {
            "etf_code": symbols,
            "market_exchange": ["SSE" if symbol.endswith(".SH") else "SZSE" for symbol in symbols],
            "list_date": ["2010-01-01"] * len(symbols),
            "delist_date": [None] * len(symbols),
        }
    )


def _provider_frame(symbol):
    return pd.DataFrame(
        {
            "symbol": [symbol],
            "ann_date": [pd.Timestamp("2020-01-03").date()],
            "nav_date": [pd.Timestamp("2020-01-02").date()],
            "unit_nav": [4.0],
            "accum_nav": [4.1],
            "accum_div": [0.1],
            "net_asset": [100.0],
            "total_netasset": [200.0],
            "adj_nav": [4.0],
            "update_flag": [1.0],
        }
    )


if __name__ == "__main__":
    unittest.main()
