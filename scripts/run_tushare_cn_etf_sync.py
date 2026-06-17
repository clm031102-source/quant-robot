from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.adapters.tushare_adapter import TushareAdapter  # noqa: E402
from quant_robot.data.readiness import check_tushare_readiness  # noqa: E402
from quant_robot.ops.tushare_cn_etf_sync import (  # noqa: E402
    build_tushare_cn_etf_sync_up_to_date_pack,
    build_tushare_cn_etf_sync_readiness_blocked_pack,
    run_tushare_cn_etf_sync,
    write_tushare_cn_etf_sync_pack,
)
from quant_robot.storage.processed_bars import load_processed_bars  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("data/processed/tushare_etf_full")
DEFAULT_REPORT_DIR = Path("data/reports/tushare_cn_etf_sync")
DEFAULT_FULL_HISTORY_START_DATE = "2005-01-01"
AUTO_START_TOKENS = {"auto", "earliest", "full-history", "full_history"}
INCREMENTAL_START_TOKENS = {"incremental", "since-last", "since_last", "resume"}
LATEST_END_TOKENS = {"latest", "latest-trade-date", "latest_trade_date", "latest-completed-trade-date"}


def run_tushare_cn_etf_sync_cli(
    *,
    source: str = "tushare",
    start_date: str = "2005-01-01",
    end_date: str,
    as_of: str | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    execute: bool = False,
    readiness: dict[str, Any] | None = None,
    full_history_start_date: str = DEFAULT_FULL_HISTORY_START_DATE,
    latest_today: str | date | None = None,
    latest_lookback_days: int = 45,
    min_rotation_history_rows: int = 20,
    min_rotation_median_amount: float = 0.0,
    max_rotation_zero_volume_ratio: float = 0.0,
    rotation_extreme_return_threshold: float = 0.5,
) -> dict[str, object]:
    readiness_pack = readiness if readiness is not None else _readiness_for_source(source)
    if execute and source == "tushare" and not bool(readiness_pack.get("ready", False)):
        window = resolve_cn_etf_sync_window(
            None,
            start_date=start_date,
            end_date=end_date,
            as_of=as_of,
            output_dir=Path(output_dir),
            full_history_start_date=full_history_start_date,
            latest_today=latest_today,
            latest_lookback_days=latest_lookback_days,
            allow_provider=False,
        )
        pack = build_tushare_cn_etf_sync_readiness_blocked_pack(
            source=source,
            output_dir=Path(output_dir),
            report_dir=Path(report_dir),
            start_date=str(window["start_date"]),
            end_date=str(window["end_date"]),
            as_of=str(window["as_of"]),
            readiness=readiness_pack,
            date_resolution=window["date_resolution"],
        )
        write_tushare_cn_etf_sync_pack(report_dir, pack)
        return pack
    adapter = _adapter_for_source(source)
    window = resolve_cn_etf_sync_window(
        adapter,
        start_date=start_date,
        end_date=end_date,
        as_of=as_of,
        output_dir=Path(output_dir),
        full_history_start_date=full_history_start_date,
        latest_today=latest_today,
        latest_lookback_days=latest_lookback_days,
        allow_provider=execute or source == "tushare-fixture",
    )
    if execute and _date_after(str(window["start_date"]), str(window["end_date"])):
        pack = build_tushare_cn_etf_sync_up_to_date_pack(
            source=source,
            output_dir=Path(output_dir),
            report_dir=Path(report_dir),
            start_date=str(window["start_date"]),
            end_date=str(window["end_date"]),
            as_of=str(window["as_of"]),
            date_resolution=window["date_resolution"],
        )
        write_tushare_cn_etf_sync_pack(report_dir, pack)
        return pack
    return run_tushare_cn_etf_sync(
        adapter=adapter,
        start_date=str(window["start_date"]),
        end_date=str(window["end_date"]),
        as_of=str(window["as_of"]),
        output_dir=Path(output_dir),
        report_dir=Path(report_dir),
        source=source,
        execute=execute,
        date_resolution=window["date_resolution"],
        min_rotation_history_rows=min_rotation_history_rows,
        min_rotation_median_amount=min_rotation_median_amount,
        max_rotation_zero_volume_ratio=max_rotation_zero_volume_ratio,
        rotation_extreme_return_threshold=rotation_extreme_return_threshold,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync the Tushare-first CN_ETF universe and fund_daily bars.")
    parser.add_argument("--source", choices=["tushare", "tushare-fixture"], default="tushare")
    parser.add_argument("--start-date", default="2005-01-01")
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--as-of")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--full-history-start-date", default=DEFAULT_FULL_HISTORY_START_DATE)
    parser.add_argument("--latest-lookback-days", default=45, type=int)
    parser.add_argument("--min-rotation-history-rows", default=20, type=int)
    parser.add_argument("--min-rotation-median-amount", default=0.0, type=float)
    parser.add_argument("--max-rotation-zero-volume-ratio", default=0.0, type=float)
    parser.add_argument("--rotation-extreme-return-threshold", default=0.5, type=float)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    pack = run_tushare_cn_etf_sync_cli(
        source=args.source,
        start_date=args.start_date,
        end_date=args.end_date,
        as_of=args.as_of,
        output_dir=Path(args.output_dir),
        report_dir=Path(args.report_dir),
        execute=args.execute,
        full_history_start_date=args.full_history_start_date,
        latest_lookback_days=args.latest_lookback_days,
        min_rotation_history_rows=args.min_rotation_history_rows,
        min_rotation_median_amount=args.min_rotation_median_amount,
        max_rotation_zero_volume_ratio=args.max_rotation_zero_volume_ratio,
        rotation_extreme_return_threshold=args.rotation_extreme_return_threshold,
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "status": pack["status"],
                "source": pack["source"],
                "primary_market": pack["primary_market"],
                "universe": pack["universe"],
                "ingest": {
                    "processed_rows": pack.get("ingest", {}).get("processed_rows", 0)
                    if isinstance(pack.get("ingest"), dict)
                    else 0
                },
                "etf_share_size": {
                    "processed_rows": pack.get("etf_share_size", {}).get("processed_rows", 0)
                    if isinstance(pack.get("etf_share_size"), dict)
                    else 0
                },
                "fund_portfolio_baskets": {
                    "processed_rows": pack.get("fund_portfolio_baskets", {}).get("processed_rows", 0)
                    if isinstance(pack.get("fund_portfolio_baskets"), dict)
                    else 0
                },
                "rotation_membership": pack.get("rotation_membership", {})
                if isinstance(pack.get("rotation_membership"), dict)
                else {},
                "survivorship_policy": pack.get("survivorship_policy", {})
                if isinstance(pack.get("survivorship_policy"), dict)
                else {},
                "date_resolution": pack.get("date_resolution", {})
                if isinstance(pack.get("date_resolution"), dict)
                else {},
                "report_dir": str(Path(args.report_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _adapter_for_source(source: str) -> object:
    if source == "tushare-fixture":
        return _FixtureTushareCnEtfAdapter()
    return TushareAdapter()


def _readiness_for_source(source: str) -> dict[str, Any]:
    if source == "tushare-fixture":
        return {"source": source, "ready": True, "missing": []}
    return check_tushare_readiness()


def resolve_cn_etf_sync_window(
    adapter: object | None,
    *,
    start_date: str,
    end_date: str,
    as_of: str | None = None,
    output_dir: str | Path | None = None,
    full_history_start_date: str = DEFAULT_FULL_HISTORY_START_DATE,
    latest_today: str | date | None = None,
    latest_lookback_days: int = 45,
    allow_provider: bool = True,
) -> dict[str, object]:
    resolved_start, start_info = _resolve_start_date(start_date, full_history_start_date, output_dir=output_dir)
    resolved_end, end_method = _resolve_end_date(
        adapter,
        end_date=end_date,
        latest_today=latest_today,
        latest_lookback_days=latest_lookback_days,
        allow_provider=allow_provider,
    )
    resolved_as_of, as_of_method = (
        _resolve_end_date(
            adapter,
            end_date=as_of,
            latest_today=latest_today,
            latest_lookback_days=latest_lookback_days,
            allow_provider=allow_provider,
        )
        if as_of is not None
        else (resolved_end, "same_as_end_date")
    )
    return {
        "start_date": resolved_start,
        "end_date": resolved_end,
        "as_of": resolved_as_of,
        "date_resolution": {
            "start_date": {"requested": start_date, "resolved": resolved_start, **start_info},
            "end_date": {"requested": end_date, "resolved": resolved_end, "method": end_method},
            "as_of": {"requested": as_of, "resolved": resolved_as_of, "method": as_of_method},
            "incremental": {
                key: value
                for key, value in start_info.items()
                if key in {"last_processed_date", "next_start_date", "existing_rows"}
            },
        },
    }


def _resolve_start_date(
    value: str,
    full_history_start_date: str,
    *,
    output_dir: str | Path | None = None,
) -> tuple[str, dict[str, object]]:
    if _is_token(value, AUTO_START_TOKENS):
        return _date_text(full_history_start_date), {"method": "full_history_start_date"}
    if _is_token(value, INCREMENTAL_START_TOKENS):
        last = _last_processed_bar_date(output_dir)
        if last is None:
            return _date_text(full_history_start_date), {"method": "full_history_start_date_no_existing_processed_bars"}
        next_start = (pd.to_datetime(last).date() + timedelta(days=1)).isoformat()
        return (
            next_start,
            {
                "method": "incremental_after_last_processed_bar",
                "last_processed_date": last,
                "next_start_date": next_start,
            },
        )
    return _date_text(value), {"method": "explicit"}


def _resolve_end_date(
    adapter: object | None,
    *,
    end_date: str | None,
    latest_today: str | date | None,
    latest_lookback_days: int,
    allow_provider: bool,
) -> tuple[str, str]:
    if end_date is None:
        cutoff = _latest_cutoff_date(latest_today)
        return cutoff.isoformat(), "local_cutoff_default"
    if not _is_token(end_date, LATEST_END_TOKENS):
        return _date_text(end_date), "explicit"
    cutoff = _latest_cutoff_date(latest_today)
    if not allow_provider or adapter is None:
        return cutoff.isoformat(), "local_cutoff_provider_unavailable"
    latest = _latest_completed_trade_date(adapter, cutoff=cutoff, lookback_days=latest_lookback_days)
    return latest, "tushare_trade_calendar_latest_open"


def _latest_completed_trade_date(adapter: object, *, cutoff: date, lookback_days: int) -> str:
    start = cutoff - timedelta(days=max(int(lookback_days), 1))
    calendar = adapter.fetch_trade_calendar(start.isoformat(), cutoff.isoformat())
    if calendar.empty:
        raise ValueError("Tushare trade calendar returned no open dates for latest resolution")
    dates = pd.to_datetime(calendar["date"], errors="coerce").dropna().dt.date
    dates = dates[dates <= cutoff]
    if dates.empty:
        raise ValueError("Tushare trade calendar has no completed open date on or before cutoff")
    return max(dates).isoformat()


def _latest_cutoff_date(value: str | date | None) -> date:
    if value is not None:
        return pd.to_datetime(value).date()
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    if now.hour < 18:
        return now.date() - timedelta(days=1)
    return now.date()


def _is_token(value: str | None, tokens: set[str]) -> bool:
    return str(value or "").strip().lower() in tokens


def _date_text(value: str | date) -> str:
    return pd.to_datetime(value).date().isoformat()


def _date_after(left: str, right: str) -> bool:
    return pd.to_datetime(left).date() > pd.to_datetime(right).date()


def _last_processed_bar_date(output_dir: str | Path | None) -> str | None:
    if output_dir is None:
        return None
    try:
        bars = load_processed_bars(output_dir, "CN_ETF")
    except FileNotFoundError:
        return None
    if bars.empty or "date" not in bars.columns:
        return None
    dates = pd.to_datetime(bars["date"], errors="coerce").dropna().dt.date
    if dates.empty:
        return None
    return max(dates).isoformat()


class _FixtureTushareCnEtfAdapter:
    def fetch_fund_basic(self, market: str = "E", status: str = "L") -> pd.DataFrame:
        return pd.DataFrame(
            {
                "symbol": ["510300.SH", "159915.SZ", "501001.SH"],
                "name": ["CSI 300 ETF", "ChiNext ETF", "Listed LOF"],
                "fund_type": ["Equity", "Equity", "Mixed"],
                "type": ["ETF", "ETF", "LOF"],
                "market": [market, market, market],
                "status": ["L", "L", "L"],
                "list_date": [
                    pd.Timestamp("2012-06-01").date(),
                    pd.Timestamp("2015-01-01").date(),
                    pd.Timestamp("2016-01-01").date(),
                ],
                "delist_date": [pd.NaT, pd.NaT, pd.NaT],
                "is_active": [True, True, True],
                "is_exchange_traded": [True, True, True],
                "is_etf": [True, True, False],
            }
        )

    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        dates = pd.date_range(start_date, end_date, freq="D")
        return pd.DataFrame({"exchange": "SSE", "date": dates.date, "is_open": 1})

    def fetch_etf_daily_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        date = pd.to_datetime(trade_date, format="%Y%m%d")
        close = 4.0 + (date.day % 10) * 0.02
        return pd.DataFrame(
            {
                "symbol": ["510300.SH", "159915.SZ"],
                "date": [date.date(), date.date()],
                "open": [close * 0.99, close * 0.79],
                "high": [close * 1.02, close * 0.82],
                "low": [close * 0.98, close * 0.78],
                "close": [close, close * 0.8],
                "volume": [100000.0, 200000.0],
                "amount": [close * 100000.0, close * 0.8 * 200000.0],
            }
        )

    def fetch_etf_share_size_by_trade_date(self, trade_date: str, exchange: str = "") -> pd.DataFrame:
        date = pd.to_datetime(trade_date, format="%Y%m%d")
        day_offset = max(date.day - 2, 0)
        if exchange == "SSE":
            return pd.DataFrame(
                {
                    "symbol": ["510300.SH"],
                    "date": [date.date()],
                    "name": ["CSI 300 ETF"],
                    "total_share": [10_000_000.0 + day_offset * 100_000.0],
                    "total_size": [40_000_000.0 + day_offset * 800_000.0],
                    "nav": [4.0],
                    "close": [4.04],
                    "exchange": ["SSE"],
                }
            )
        return pd.DataFrame(
            {
                "symbol": ["159915.SZ"],
                "date": [date.date()],
                "name": ["ChiNext ETF"],
                "total_share": [20_000_000.0 + day_offset * 200_000.0],
                "total_size": [40_000_000.0 + day_offset * 400_000.0],
                "nav": [2.0],
                "close": [1.98],
                "exchange": ["SZSE"],
            }
        )

    def fetch_fund_portfolio(self, ts_code: str, start_date: str = "", end_date: str = "") -> pd.DataFrame:
        if ts_code == "510300.SH":
            return pd.DataFrame(
                {
                    "fund_symbol": ["510300.SH", "510300.SH"],
                    "known_date": [pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-01-02").date()],
                    "period_end_date": [pd.Timestamp("2023-12-31").date(), pd.Timestamp("2023-12-31").date()],
                    "stock_symbol": ["600519.SH", "000001.SZ"],
                    "mkv": [60.0, 40.0],
                    "amount": [1.0, 2.0],
                    "stk_mkv_ratio": [6.0, 4.0],
                    "stk_float_ratio": [0.1, 0.2],
                }
            )
        if ts_code == "159915.SZ":
            return pd.DataFrame(
                {
                    "fund_symbol": ["159915.SZ"],
                    "known_date": [pd.Timestamp("2024-01-02").date()],
                    "period_end_date": [pd.Timestamp("2023-12-31").date()],
                    "stock_symbol": ["300750.SZ"],
                    "mkv": [100.0],
                    "amount": [3.0],
                    "stk_mkv_ratio": [10.0],
                    "stk_float_ratio": [0.3],
                }
            )
        return pd.DataFrame()


if __name__ == "__main__":
    main()
