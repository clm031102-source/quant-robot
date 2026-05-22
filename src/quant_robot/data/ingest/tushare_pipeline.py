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
    raw_frames_by_date: dict[str, pd.DataFrame] = {}
    downloaded_rows_by_date: dict[str, int] = {}

    trade_dates = _trade_dates(adapter, start_date, end_date)
    for trade_date in trade_dates:
        key = f"daily:{trade_date}"
        if resume and manifest.is_completed(key):
            skipped.append(trade_date)
            continue
        raw = adapter.fetch_daily_by_trade_date(trade_date)
        store.write_frame(raw, "raw/tushare/daily", {"trade_date": trade_date})
        downloaded.append(trade_date)
        downloaded_rows_by_date[trade_date] = len(raw)
        raw_frames_by_date[trade_date] = raw

    try:
        raw_for_processing = _load_raw_frames(store, trade_dates, raw_frames_by_date)
        raw_for_processing, adjusted = _attach_adjusted_close(adapter, raw_for_processing, start_date, end_date)
        processed = _normalize_tushare_daily(raw_for_processing)
        if not processed.empty:
            validate_market_data(processed)
            _write_processed_by_year(store, processed)
        expected_dates = [pd.to_datetime(date, format="%Y%m%d").date() for date in trade_dates]
        report = build_quality_report(processed, expected_dates=expected_dates) if not processed.empty else _empty_report()
    except Exception as exc:
        for trade_date in downloaded:
            manifest.mark_failed(f"daily:{trade_date}", reason=str(exc))
        manifest.save()
        raise
    for trade_date in downloaded:
        manifest.mark_completed(f"daily:{trade_date}", rows=downloaded_rows_by_date[trade_date])
    manifest.save()
    (output_path / "quality_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "source": "tushare",
        "market": "CN",
        "downloaded_trade_dates": downloaded,
        "skipped_trade_dates": skipped,
        "processed_rows": int(len(processed)),
        "adjusted": adjusted,
        "quality_report": report,
    }


def _trade_dates(adapter: TushareDailyAdapter, start_date: str, end_date: str) -> list[str]:
    calendar = adapter.fetch_trade_calendar(start_date, end_date)
    dates = pd.to_datetime(calendar["date"]).dt.strftime("%Y%m%d")
    return list(dates)


def _load_raw_frames(store: DatasetStore, trade_dates: list[str], raw_frames_by_date: dict[str, pd.DataFrame]) -> pd.DataFrame:
    frames = []
    for trade_date in trade_dates:
        if trade_date in raw_frames_by_date:
            frames.append(raw_frames_by_date[trade_date])
        elif store.exists("raw/tushare/daily", {"trade_date": trade_date}):
            frames.append(store.read_frame("raw/tushare/daily", {"trade_date": trade_date}))
    if not frames:
        return pd.DataFrame(columns=["symbol", "date", "open", "high", "low", "close", "volume", "amount"])
    return pd.concat(frames, ignore_index=True)


def _write_processed_by_year(store: DatasetStore, processed: pd.DataFrame) -> None:
    for year, group in processed.groupby(pd.to_datetime(processed["date"]).dt.year):
        partitions = {"frequency": "1d", "market": "CN", "year": str(year)}
        merged = group
        if store.exists("processed/bars", partitions):
            existing = _coerce_processed_types(store.read_frame("processed/bars", partitions))
            merged = pd.concat([existing, group], ignore_index=True)
            merged = merged.drop_duplicates(["asset_id", "timestamp", "frequency", "source"], keep="last")
            merged = merged.sort_values(["asset_id", "timestamp"]).reset_index(drop=True)
        validate_market_data(merged)
        store.write_frame(merged, "processed/bars", partitions)


def _coerce_processed_types(frame: pd.DataFrame) -> pd.DataFrame:
    coerced = frame.copy()
    if "timestamp" in coerced.columns:
        coerced["timestamp"] = pd.to_datetime(coerced["timestamp"], utc=True)
    if "date" in coerced.columns:
        coerced["date"] = pd.to_datetime(coerced["date"]).dt.date
    if "ingested_at" in coerced.columns:
        coerced["ingested_at"] = pd.to_datetime(coerced["ingested_at"], utc=True)
    return coerced


def _normalize_tushare_daily(raw: pd.DataFrame) -> pd.DataFrame:
    pieces = []
    for symbol, group in raw.groupby("symbol", sort=True):
        asset = _asset_from_tushare_symbol(symbol)
        pieces.append(normalize_ohlcv(group, asset, source="tushare", frequency="1d"))
    if not pieces:
        return pd.DataFrame()
    return pd.concat(pieces, ignore_index=True).sort_values(["asset_id", "timestamp"]).reset_index(drop=True)


def _attach_adjusted_close(
    adapter: TushareDailyAdapter,
    raw: pd.DataFrame,
    start_date: str,
    end_date: str,
) -> tuple[pd.DataFrame, bool]:
    if raw.empty or not hasattr(adapter, "fetch_adj_factor"):
        return raw, False
    adj_factor = adapter.fetch_adj_factor("", start_date, end_date)  # type: ignore[attr-defined]
    if adj_factor.empty:
        return raw, False
    source = raw.copy()
    source["date"] = pd.to_datetime(source["date"]).dt.date
    factors = adj_factor.copy()
    factors["date"] = pd.to_datetime(factors["date"]).dt.date
    merged = source.merge(factors, on=["symbol", "date"], how="left")
    if merged["adj_factor"].isna().all():
        return raw, False
    merged["adj_close"] = merged["close"] * merged["adj_factor"].fillna(1.0)
    return merged.drop(columns=["adj_factor"]), True


def _asset_from_tushare_symbol(symbol: str) -> Asset:
    code, suffix = symbol.split(".")
    exchange_by_suffix = {"SZ": "XSHE", "SH": "XSHG", "BJ": "XBEI"}
    try:
        exchange = exchange_by_suffix[suffix.upper()]
    except KeyError as exc:
        raise ValueError(f"Unsupported Tushare symbol suffix: {symbol}") from exc
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
