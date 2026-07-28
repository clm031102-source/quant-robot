from __future__ import annotations

import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.adapters.public_cn_etf_fund_structure import FetchedFrame
from quant_robot.data.cn_trading_calendar import (
    build_cn_trading_calendar,
    write_cn_trading_calendar,
)
from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_cn_etf_fund_structure_source_readiness import (
    _load_and_validate_config,
    run_cn_etf_fund_structure_source_readiness_cli,
)


class _FixtureAdapter:
    def __init__(self) -> None:
        self.lock = threading.Lock()

    def fetch_sse_share_date(self, trade_date: str) -> FetchedFrame:
        return FetchedFrame(
            frame=_share_rows([trade_date], suffix="SH"),
            response_sha256="1" * 64,
            request_url=f"https://sse.fixture/{trade_date}",
            source="sse_official_etf_scale",
        )

    def fetch_szse_share_window(self, start_date: str, end_date: str) -> FetchedFrame:
        dates = [
            value
            for value in ("2024-01-02", "2024-01-03", "2024-01-04")
            if start_date <= value <= end_date
        ]
        return FetchedFrame(
            frame=_share_rows(dates, suffix="SZ"),
            response_sha256="2" * 64,
            request_url=f"https://szse.fixture/{start_date}/{end_date}",
            source="szse_official_fund_scale",
        )

    def fetch_eastmoney_nav_symbol(
        self,
        symbol: str,
        *,
        start_date: str,
        end_date: str,
    ) -> FetchedFrame:
        dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]).date
        return FetchedFrame(
            frame=pd.DataFrame(
                {
                    "date": dates,
                    "asset_id": [_asset_id(symbol)] * 3,
                    "symbol": [symbol] * 3,
                    "exchange": ["SSE" if symbol.endswith(".SH") else "SZSE"] * 3,
                    "nav": [1.0] * 3,
                    "nav_source": ["eastmoney_fund_detail_history"] * 3,
                }
            ),
            response_sha256="3" * 64,
            request_url=f"https://nav.fixture/{symbol}",
            source="eastmoney_fund_detail_history",
        )


class RunCnEtfFundStructureSourceReadinessTests(unittest.TestCase):
    def test_end_to_end_fixture_executes_ingest_and_writes_ready_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bar_root = root / "bars"
            _write_bars(bar_root)
            config_path = _fixture_config(root, bar_root)

            result = run_cn_etf_fund_structure_source_readiness_cli(
                config_path=config_path,
                execute=True,
                adapter=_FixtureAdapter(),
            )

            self.assertEqual(result["status"], "ready_for_fund_structure_preregistration")
            self.assertTrue(result["gate"]["cleared"])
            self.assertEqual(result["summary"]["share_assets"], 60)
            self.assertEqual(result["summary"]["analysis_sessions"], 3)
            self.assertEqual(result["ingest_result"]["request_summary"]["failed"], 0)
            for path in result["artifacts"].values():
                self.assertTrue(Path(path).exists(), path)
            self.assertFalse(result["factor_generation_allowed"])
            self.assertFalse(result["final_holdout_allowed"])
            self.assertFalse(result["live_boundary_allowed"])
            result_json = Path(result["artifacts"]["json"])
            first_hash = hashlib.sha256(result_json.read_bytes()).hexdigest()

            repeated = run_cn_etf_fund_structure_source_readiness_cli(
                config_path=config_path,
                execute=False,
            )
            second_hash = hashlib.sha256(Path(repeated["artifacts"]["json"]).read_bytes()).hexdigest()
            self.assertEqual(first_hash, second_hash)

    def test_config_rejects_threshold_and_boundary_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = _fixture_config(root, root / "bars")
            payload = json.loads(config_path.read_text(encoding="utf-8"))

            payload["thresholds"]["minimum_nav_intersection_coverage"] = 0.6
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "frozen readiness thresholds"):
                _load_and_validate_config(config_path)

            payload["thresholds"]["minimum_nav_intersection_coverage"] = 0.7
            payload["boundaries"]["factor_generation_allowed"] = True
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must be false"):
                _load_and_validate_config(config_path)

    def test_config_rejects_analysis_or_probe_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = _fixture_config(root, root / "bars")
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["analysis"]["end_date"] = "2025-01-01"
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "frozen analysis boundary"):
                _load_and_validate_config(config_path)

            payload["analysis"]["end_date"] = "2024-06-28"
            payload["tushare_probe"]["status"] = "ready"
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "permission denial"):
                _load_and_validate_config(config_path)


def _fixture_config(root: Path, bar_root: Path) -> Path:
    source = Path("configs/cn_etf_fund_structure_source_readiness_20260728.json")
    payload = json.loads(source.read_text(encoding="utf-8"))
    calendar_path, calendar_manifest_path = _write_calendar(root)
    payload["analysis"]["bar_root"] = str(bar_root)
    payload["analysis"]["trading_calendar_path"] = str(calendar_path)
    payload["analysis"]["trading_calendar_manifest_path"] = str(calendar_manifest_path)
    payload["outputs"]["data_dir"] = str(root / "processed")
    payload["outputs"]["report_dir"] = str(root / "reports")
    config_path = root / "config.json"
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return config_path


def _write_calendar(root: Path) -> tuple[Path, Path]:
    dates = ["2024-01-02", "2024-01-03", "2024-01-04", "2024-07-01"]
    exchange_frames = {
        exchange: pd.DataFrame(
            {
                "date": dates,
                "is_open": [1] * len(dates),
                "exchange": [exchange] * len(dates),
            }
        )
        for exchange in ("SSE", "SZSE")
    }
    calendar, manifest = build_cn_trading_calendar(
        exchange_frames,
        start_date="2024-01-02",
        end_date="2024-07-01",
    )
    paths = write_cn_trading_calendar(root / "calendar", calendar, manifest)
    return Path(paths["calendar_path"]), Path(paths["manifest_path"])


def _write_bars(root: Path) -> None:
    dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-07-01"])
    rows = []
    for date_idx, date in enumerate(dates):
        for suffix, base in (("SH", 510000), ("SZ", 159000)):
            for idx in range(30):
                code = f"{base + idx:06d}"
                symbol = f"{code}.{suffix}"
                rows.append(
                    {
                        "date": date.date(),
                        "timestamp": pd.Timestamp(date, tz="Asia/Shanghai"),
                        "asset_id": _asset_id(symbol),
                        "symbol": symbol,
                        "market": "CN_ETF",
                        "frequency": "1d",
                        "close": 1.0 + idx / 100 + date_idx / 1000,
                        "source": "tushare_fund_daily",
                    }
                )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/bars",
        {"frequency": "1d", "market": "CN_ETF", "year": "2024"},
    )


def _share_rows(dates: list[str], *, suffix: str) -> pd.DataFrame:
    base = 510000 if suffix == "SH" else 159000
    exchange = "SSE" if suffix == "SH" else "SZSE"
    source = "sse_official_etf_scale" if suffix == "SH" else "szse_official_fund_scale"
    rows = []
    for date in dates:
        for idx in range(30):
            code = f"{base + idx:06d}"
            symbol = f"{code}.{suffix}"
            rows.append(
                {
                    "date": pd.Timestamp(date).date(),
                    "asset_id": _asset_id(symbol),
                    "symbol": symbol,
                    "exchange": exchange,
                    "total_share": 1_000_000.0 + idx,
                    "share_source": source,
                }
            )
    return pd.DataFrame(
        rows,
        columns=["date", "asset_id", "symbol", "exchange", "total_share", "share_source"],
    )


def _asset_id(symbol: str) -> str:
    code, suffix = symbol.split(".")
    return f"CN_ETF_{'XSHG' if suffix == 'SH' else 'XSHE'}_{code}"


if __name__ == "__main__":
    unittest.main()
