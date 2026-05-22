from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.data.ingest.manifest import IngestManifest
from quant_robot.data.normalize import normalize_ohlcv
from quant_robot.data.quality import validate_market_data
from quant_robot.data.quality_report import build_quality_report
from quant_robot.storage.dataset_store import DatasetStore


class TushareDailyAdapter(Protocol):
    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        ...

    def fetch_daily_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        ...


def run_tushare_daily_ingest(
    adapter: TushareDailyAdapter,
    start_date: str,
    end_date: str,
    output_dir: str | Path,
    resume: bool = True,
) -> dict[str, object]:
    output_path = Path(output_dir)
    store = DatasetStore(output_path)
    manifest = IngestManifest(output_path / "manifest.json")
    downloaded: list[str] = []
    skipped: list[str] = []
    raw_frames = []

    for trade_date in _trade_dates(adapter, start_date, end_date):
        key = f"daily:{trade_date}"
        if resume and manifest.is_completed(key):
            skipped.append(trade_date)
            continue
        raw = adapter.fetch_daily_by_trade_date(trade_date)
        store.write_frame(raw, "raw/tushare/daily", {"trade_date": trade_date})
        manifest.mark_completed(key, rows=len(raw))
        downloaded.append(trade_date)
        raw_frames.append(raw)
    manifest.save()

    raw_for_processing = _load_raw_frames(store, downloaded, raw_frames)
    processed = _normalize_tushare_daily(raw_for_processing)
    if not processed.empty:
        validate_market_data(processed)
        for year, group in processed.groupby(pd.to_datetime(processed["date"]).dt.year):
            store.write_frame(group, "processed/bars", {"frequency": "1d", "market": "CN", "year": str(year)})
    report = build_quality_report(processed) if not processed.empty else _empty_report()
    (output_path / "quality_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "source": "tushare",
        "market": "CN",
        "downloaded_trade_dates": downloaded,
        "skipped_trade_dates": skipped,
        "processed_rows": int(len(processed)),
        "quality_report": report,
    }


def _trade_dates(adapter: TushareDailyAdapter, start_date: str, end_date: str) -> list[str]:
    calendar = adapter.fetch_trade_calendar(start_date, end_date)
    dates = pd.to_datetime(calendar["date"]).dt.strftime("%Y%m%d")
    return list(dates)


def _load_raw_frames(store: DatasetStore, downloaded: list[str], raw_frames: list[pd.DataFrame]) -> pd.DataFrame:
    frames = list(raw_frames)
    if not frames:
        for trade_date in downloaded:
            frames.append(store.read_frame("raw/tushare/daily", {"trade_date": trade_date}))
    if not frames:
        return pd.DataFrame(columns=["symbol", "date", "open", "high", "low", "close", "volume", "amount"])
    return pd.concat(frames, ignore_index=True)


def _normalize_tushare_daily(raw: pd.DataFrame) -> pd.DataFrame:
    pieces = []
    for symbol, group in raw.groupby("symbol", sort=True):
        asset = _asset_from_tushare_symbol(symbol)
        pieces.append(normalize_ohlcv(group, asset, source="tushare", frequency="1d"))
    if not pieces:
        return pd.DataFrame()
    return pd.concat(pieces, ignore_index=True).sort_values(["asset_id", "timestamp"]).reset_index(drop=True)


def _asset_from_tushare_symbol(symbol: str) -> Asset:
    code, suffix = symbol.split(".")
    exchange = "XSHE" if suffix.upper() == "SZ" else "XSHG"
    return Asset(
        asset_id=f"CN_{exchange}_{code}",
        symbol=symbol,
        market="CN",
        exchange=exchange,
        asset_type="stock",
        currency="CNY",
        timezone="Asia/Shanghai",
        calendar=exchange,
    )


def _empty_report() -> dict[str, object]:
    return {
        "rows": 0,
        "assets": 0,
        "markets": [],
        "start_date": None,
        "end_date": None,
        "duplicate_bars": 0,
        "zero_volume_rows": 0,
        "missing_date_rows": 0,
        "coverage_by_asset": [],
    }
