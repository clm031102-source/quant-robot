from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.data.adapters.public_cn_etf_fund_structure import FetchedFrame
from quant_robot.data.ingest.public_cn_etf_fund_structure import (
    build_public_source_request_plan,
    normalize_public_cn_etf_fund_structure,
    run_public_cn_etf_fund_structure_ingest,
    _load_manifest,
    _save_manifest,
)
from quant_robot.storage.etf_share_size import load_etf_share_size_inputs


class _FakeAdapter:
    def __init__(self) -> None:
        self.sse_calls: list[str] = []
        self.szse_calls: list[tuple[str, str]] = []
        self.nav_calls: list[str] = []

    def fetch_sse_share_date(self, trade_date: str) -> FetchedFrame:
        self.sse_calls.append(trade_date)
        return FetchedFrame(
            frame=_share_frame(trade_date, "510300.SH", 100.0 + len(self.sse_calls)),
            response_sha256=f"{len(self.sse_calls):064x}",
            request_url=f"https://sse.test/{trade_date}",
            source="sse_official_etf_scale",
        )

    def fetch_szse_share_window(self, start_date: str, end_date: str) -> FetchedFrame:
        self.szse_calls.append((start_date, end_date))
        dates = pd.date_range(start_date, end_date, freq="B")
        frame = pd.concat(
            [_share_frame(day.date().isoformat(), "159919.SZ", 200.0 + idx) for idx, day in enumerate(dates)],
            ignore_index=True,
        )
        return FetchedFrame(
            frame=frame,
            response_sha256=f"{100 + len(self.szse_calls):064x}",
            request_url=f"https://szse.test/{start_date}/{end_date}",
            source="szse_official_fund_scale",
        )

    def fetch_eastmoney_nav_symbol(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
    ) -> FetchedFrame:
        self.nav_calls.append(symbol)
        dates = pd.date_range(start_date, end_date, freq="B")
        frame = pd.DataFrame(
            {
                "date": dates.date,
                "asset_id": [_asset_id(symbol)] * len(dates),
                "symbol": [symbol] * len(dates),
                "exchange": ["SSE" if symbol.endswith(".SH") else "SZSE"] * len(dates),
                "nav": [2.0] * len(dates),
                "nav_source": ["eastmoney_fund_detail_history"] * len(dates),
            }
        )
        return FetchedFrame(
            frame=frame,
            response_sha256=f"{200 + len(self.nav_calls):064x}",
            request_url=f"https://nav.test/{symbol}",
            source="eastmoney_fund_detail_history",
        )


class PublicCnEtfFundStructureIngestTests(unittest.TestCase):
    def test_manifest_allows_only_szse_window_rechunk_without_losing_other_sources(self) -> None:
        base_scope = {
            "analysis_start": "2024-01-02",
            "analysis_end": "2024-06-28",
            "symbols": ["159919.SZ", "510300.SH"],
            "analysis_sessions": ["2024-01-02", "2024-01-03"],
        }
        first_plan = {
            **base_scope,
            "szse_windows": [{"start_date": "2024-01-02", "end_date": "2024-06-28"}],
        }
        second_plan = {
            **base_scope,
            "szse_windows": [
                {"start_date": "2024-01-02", "end_date": "2024-03-31"},
                {"start_date": "2024-04-01", "end_date": "2024-06-28"},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "manifest.json")
            manifest = _load_manifest(path, first_plan)
            manifest["requests"] = {
                "sse:2024-01-02": {"kind": "sse_share", "status": "completed"},
                "nav:510300.SH": {"kind": "eastmoney_nav", "status": "completed"},
                "szse:old": {"kind": "szse_share", "status": "completed"},
            }
            _save_manifest(path, manifest)

            migrated = _load_manifest(path, second_plan)

            self.assertEqual(migrated["scope"]["szse_windows"], second_plan["szse_windows"])
            self.assertIn("sse:2024-01-02", migrated["requests"])
            self.assertIn("nav:510300.SH", migrated["requests"])
            self.assertNotIn("szse:old", migrated["requests"])
            self.assertEqual(migrated["migrations"][-1]["kind"], "szse_window_rechunk")

    def test_manifest_write_retries_transient_windows_replace_denial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "manifest.json")
            with (
                patch(
                    "quant_robot.data.ingest.public_cn_etf_fund_structure.atomic_write_json",
                    side_effect=[PermissionError("busy"), None],
                ) as writer,
                patch("quant_robot.data.ingest.public_cn_etf_fund_structure.time.sleep") as sleeper,
            ):
                _save_manifest(path, {"schema_version": 1}, max_attempts=3, retry_delay_seconds=0.1)

            self.assertEqual(writer.call_count, 2)
            sleeper.assert_called_once_with(0.1)

    def test_request_plan_uses_only_analysis_sessions_and_observed_symbols(self) -> None:
        bars = _bars()

        plan = build_public_source_request_plan(
            bars,
            start_date="2024-01-02",
            end_date="2024-01-04",
            szse_window_days=2,
        )

        self.assertEqual(plan["analysis_sessions"], ["2024-01-02", "2024-01-03", "2024-01-04"])
        self.assertEqual(plan["symbols"], ["159919.SZ", "510300.SH"])
        self.assertEqual(
            plan["szse_windows"],
            [
                {"start_date": "2024-01-02", "end_date": "2024-01-03"},
                {"start_date": "2024-01-04", "end_date": "2024-01-04"},
            ],
        )

    def test_normalization_lags_known_from_and_derives_scale_and_premium(self) -> None:
        bars = _bars()
        shares = pd.concat(
            [
                _share_frame("2024-01-02", "510300.SH", 100.0),
                _share_frame("2024-01-02", "159919.SZ", 200.0),
            ],
            ignore_index=True,
        )
        nav = pd.DataFrame(
            {
                "date": [pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-01-02").date()],
                "asset_id": [_asset_id("510300.SH"), _asset_id("159919.SZ")],
                "symbol": ["510300.SH", "159919.SZ"],
                "exchange": ["SSE", "SZSE"],
                "nav": [2.0, 4.0],
                "nav_source": ["eastmoney_fund_detail_history"] * 2,
            }
        )

        result = normalize_public_cn_etf_fund_structure(
            shares=shares,
            nav=nav,
            bars=bars,
            start_date="2024-01-02",
            end_date="2024-01-04",
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(set(str(value) for value in result["known_from"]), {"2024-01-03"})
        sh = result.set_index("symbol").loc["510300.SH"]
        self.assertAlmostEqual(sh["total_size"], 200.0)
        self.assertAlmostEqual(sh["nav_premium_discount"], 10.0 / 2.0 - 1.0)
        self.assertEqual(sh["close_source"], "tushare_fund_daily")

    def test_normalization_rejects_duplicate_bars_and_missing_next_session(self) -> None:
        bars = _bars()
        shares = _share_frame("2024-01-02", "510300.SH", 100.0)
        nav = pd.DataFrame(columns=["date", "asset_id", "symbol", "exchange", "nav", "nav_source"])
        with self.assertRaisesRegex(ValueError, "duplicate bar"):
            normalize_public_cn_etf_fund_structure(
                shares=shares,
                nav=nav,
                bars=pd.concat([bars, bars.iloc[[0]]], ignore_index=True),
                start_date="2024-01-02",
                end_date="2024-01-04",
            )

        with self.assertRaisesRegex(ValueError, "next observed session"):
            normalize_public_cn_etf_fund_structure(
                shares=_share_frame("2024-01-04", "510300.SH", 100.0),
                nav=nav,
                bars=bars[bars["date"] <= pd.Timestamp("2024-01-04").date()],
                start_date="2024-01-02",
                end_date="2024-01-04",
            )

        lagged = normalize_public_cn_etf_fund_structure(
            shares=_share_frame("2024-01-04", "510300.SH", 100.0),
            nav=nav,
            bars=bars[bars["date"] <= pd.Timestamp("2024-01-04").date()],
            start_date="2024-01-02",
            end_date="2024-01-04",
            trading_sessions=["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
        )
        self.assertEqual(str(lagged.loc[0, "known_from"]), "2024-01-05")

    def test_live_orchestration_is_resumable_and_writes_canonical_partitions(self) -> None:
        adapter = _FakeAdapter()
        with tempfile.TemporaryDirectory() as tmp:
            result = run_public_cn_etf_fund_structure_ingest(
                adapter=adapter,
                bars=_bars(),
                start_date="2024-01-02",
                end_date="2024-01-04",
                output_dir=tmp,
                szse_window_days=183,
                max_workers=1,
            )
            first_calls = (list(adapter.sse_calls), list(adapter.szse_calls), list(adapter.nav_calls))

            resumed = run_public_cn_etf_fund_structure_ingest(
                adapter=adapter,
                bars=_bars(),
                start_date="2024-01-02",
                end_date="2024-01-04",
                output_dir=tmp,
                szse_window_days=183,
                max_workers=1,
            )

            self.assertEqual(adapter.sse_calls, first_calls[0])
            self.assertEqual(adapter.szse_calls, first_calls[1])
            self.assertEqual(adapter.nav_calls, first_calls[2])
            self.assertEqual(result["processed_rows"], resumed["processed_rows"])
            self.assertEqual(result["request_summary"]["failed"], 0)
            self.assertGreater(result["processed_rows"], 0)
            processed = load_etf_share_size_inputs(tmp, "CN_ETF")
            self.assertEqual(len(processed), result["processed_rows"])
            self.assertTrue((pd.to_datetime(processed["known_from"]) > pd.to_datetime(processed["date"])).all())
            manifest = json.loads(Path(tmp, "public_source_manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(all(row["status"] == "completed" for row in manifest["requests"].values()))

    def test_orchestration_does_not_emit_rows_after_analysis_end(self) -> None:
        adapter = _FakeAdapter()
        with tempfile.TemporaryDirectory() as tmp:
            result = run_public_cn_etf_fund_structure_ingest(
                adapter=adapter,
                bars=_bars(include_holdout=True),
                start_date="2024-01-02",
                end_date="2024-01-04",
                output_dir=tmp,
                max_workers=1,
            )
            processed = load_etf_share_size_inputs(tmp, "CN_ETF")
            self.assertLessEqual(pd.to_datetime(processed["date"]).max(), pd.Timestamp("2024-01-04"))
            self.assertEqual(result["analysis_end"], "2024-01-04")
            self.assertFalse(result["final_holdout_read"])


def _share_frame(date: str, symbol: str, total_share: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [pd.Timestamp(date).date()],
            "asset_id": [_asset_id(symbol)],
            "symbol": [symbol],
            "exchange": ["SSE" if symbol.endswith(".SH") else "SZSE"],
            "total_share": [total_share],
            "share_source": [
                "sse_official_etf_scale" if symbol.endswith(".SH") else "szse_official_fund_scale"
            ],
        }
    )


def _bars(include_holdout: bool = False) -> pd.DataFrame:
    dates = list(pd.date_range("2024-01-02", "2024-01-05", freq="B"))
    if include_holdout:
        dates.append(pd.Timestamp("2026-01-05"))
    rows = []
    for date_idx, date in enumerate(dates):
        for symbol, close in [("510300.SH", 10.0), ("159919.SZ", 20.0)]:
            rows.append(
                {
                    "date": date.date(),
                    "asset_id": _asset_id(symbol),
                    "symbol": symbol,
                    "market": "CN_ETF",
                    "close": close + date_idx,
                    "source": "tushare",
                }
            )
    return pd.DataFrame(rows)


def _asset_id(symbol: str) -> str:
    code, suffix = symbol.split(".")
    return f"CN_ETF_{'XSHG' if suffix == 'SH' else 'XSHE'}_{code}"


if __name__ == "__main__":
    unittest.main()
