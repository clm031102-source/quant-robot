from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

import pandas as pd

from quant_robot.data.ingest.manifest import IngestManifest
from quant_robot.data.sources.tushare_mapping import ETF_SHARE_SIZE_COLUMNS
from quant_robot.storage.dataset_store import DatasetStore


class TushareEtfShareSizeAdapter(Protocol):
    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        ...

    def fetch_etf_share_size_by_trade_date(self, trade_date: str, exchange: str = "") -> pd.DataFrame:
        ...


def run_tushare_etf_share_size_ingest(
    adapter: TushareEtfShareSizeAdapter,
    start_date: str,
    end_date: str,
    output_dir: str | Path,
    resume: bool = True,
    market: str = "CN_ETF",
    exchanges: tuple[str, ...] = ("SSE", "SZSE"),
) -> dict[str, object]:
    market = market.upper()
    if market != "CN_ETF":
        raise ValueError(f"Unsupported Tushare ETF share-size market: {market}")
    output_path = Path(output_dir)
    store = DatasetStore(output_path)
    manifest = IngestManifest(output_path / "manifest.json")
    downloaded: list[str] = []
    skipped: list[str] = []
    reused_raw: list[str] = []
    raw_frames_by_key: dict[str, pd.DataFrame] = {}
    downloaded_rows_by_key: dict[str, int] = {}
    raw_dataset = _raw_dataset()

    trade_dates = _trade_dates(adapter, start_date, end_date)
    exchange_dates = [(exchange, trade_date) for trade_date in trade_dates for exchange in exchanges]
    for exchange, trade_date in exchange_dates:
        key = _manifest_key(exchange, trade_date)
        exchange_date = _exchange_date_text(exchange, trade_date)
        if resume and manifest.is_completed(key):
            skipped.append(exchange_date)
            continue
        if resume and store.exists(raw_dataset, {"exchange": exchange, "trade_date": trade_date}):
            skipped.append(exchange_date)
            reused_raw.append(exchange_date)
            continue
        raw = adapter.fetch_etf_share_size_by_trade_date(trade_date, exchange=exchange)
        store.write_frame(raw, raw_dataset, {"exchange": exchange, "trade_date": trade_date})
        downloaded.append(exchange_date)
        downloaded_rows_by_key[key] = len(raw)
        raw_frames_by_key[key] = raw

    try:
        raw_for_processing = _load_raw_frames(store, exchange_dates, raw_frames_by_key)
        processed = _normalize_etf_share_size(raw_for_processing, market)
        if not processed.empty:
            _validate_etf_share_size(processed)
            _write_processed_by_year(store, processed, market)
        report = _quality_report(processed, market)
    except Exception as exc:
        for exchange_date in downloaded + reused_raw:
            exchange, trade_date = exchange_date.split(":", 1)
            manifest.mark_failed(_manifest_key(exchange, trade_date), reason=str(exc))
        manifest.save()
        raise

    for exchange_date in reused_raw:
        exchange, trade_date = exchange_date.split(":", 1)
        key = _manifest_key(exchange, trade_date)
        downloaded_rows_by_key[key] = len(store.read_frame(raw_dataset, {"exchange": exchange, "trade_date": trade_date}))
    for exchange_date in downloaded:
        exchange, trade_date = exchange_date.split(":", 1)
        key = _manifest_key(exchange, trade_date)
        manifest.mark_completed(key, rows=downloaded_rows_by_key[key])
    for exchange_date in reused_raw:
        exchange, trade_date = exchange_date.split(":", 1)
        key = _manifest_key(exchange, trade_date)
        manifest.mark_completed(key, rows=downloaded_rows_by_key[key])
    manifest.save()
    (output_path / "etf_share_size_quality_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {
        "source": "tushare",
        "dataset": "etf_share_size",
        "market": market,
        "exchanges": list(exchanges),
        "downloaded_exchange_trade_dates": downloaded,
        "skipped_exchange_trade_dates": skipped,
        "reused_raw_exchange_trade_dates": reused_raw,
        "processed_rows": int(len(processed)),
        "quality_report": report,
    }


def _trade_dates(adapter: TushareEtfShareSizeAdapter, start_date: str, end_date: str) -> list[str]:
    calendar = adapter.fetch_trade_calendar(start_date, end_date)
    dates = pd.to_datetime(calendar["date"]).dt.strftime("%Y%m%d")
    return list(dates)


def _manifest_key(exchange: str, trade_date: str) -> str:
    return f"etf_share_size:{exchange}:{trade_date}"


def _exchange_date_text(exchange: str, trade_date: str) -> str:
    return f"{exchange}:{trade_date}"


def _raw_dataset() -> str:
    return "raw/tushare/etf_share_size"


def _load_raw_frames(
    store: DatasetStore,
    exchange_dates: list[tuple[str, str]],
    raw_frames_by_key: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    frames = []
    for exchange, trade_date in exchange_dates:
        key = _manifest_key(exchange, trade_date)
        if key in raw_frames_by_key:
            frames.append(raw_frames_by_key[key])
        elif store.exists(_raw_dataset(), {"exchange": exchange, "trade_date": trade_date}):
            frames.append(store.read_frame(_raw_dataset(), {"exchange": exchange, "trade_date": trade_date}))
    if not frames:
        return pd.DataFrame(columns=ETF_SHARE_SIZE_COLUMNS)
    return pd.concat(frames, ignore_index=True)


def _normalize_etf_share_size(raw: pd.DataFrame, market: str) -> pd.DataFrame:
    required = ETF_SHARE_SIZE_COLUMNS
    missing = [column for column in required if column not in raw.columns]
    if missing:
        raise ValueError(f"Tushare ETF share-size inputs are missing columns: {', '.join(missing)}")
    source = raw.copy()
    source["date"] = pd.to_datetime(source["date"]).dt.date
    source["asset_id"] = source["symbol"].map(_asset_id_from_tushare_symbol)
    source["market"] = market
    source["source"] = "tushare_etf_share_size"
    source["ingested_at"] = pd.Timestamp.now(tz="UTC")
    for column in ["total_share", "total_size", "nav", "close"]:
        source[column] = pd.to_numeric(source[column], errors="coerce")
    denominator = source["nav"].where(source["nav"] != 0.0)
    source["nav_premium_discount"] = source["close"] / denominator - 1.0
    source = source.sort_values(["asset_id", "date"]).reset_index(drop=True)
    grouped = source.groupby("asset_id", sort=False)
    source["share_change_1d"] = grouped["total_share"].pct_change(fill_method=None)
    source["size_change_1d"] = grouped["total_size"].pct_change(fill_method=None)
    ordered = [
        "date",
        "asset_id",
        "symbol",
        "market",
        "source",
        "ingested_at",
        "name",
        "exchange",
        "total_share",
        "total_size",
        "nav",
        "close",
        "share_change_1d",
        "size_change_1d",
        "nav_premium_discount",
    ]
    return source[ordered].sort_values(["asset_id", "date"]).reset_index(drop=True)


def _asset_id_from_tushare_symbol(symbol: str) -> str:
    parts = str(symbol).split(".")
    if len(parts) != 2:
        raise ValueError(f"Unsupported Tushare ETF symbol: {symbol}")
    code, suffix = parts
    exchange_by_suffix = {"SZ": "XSHE", "SH": "XSHG", "BJ": "XBEI"}
    try:
        exchange = exchange_by_suffix[suffix.upper()]
    except KeyError as exc:
        raise ValueError(f"Unsupported Tushare ETF symbol suffix: {symbol}") from exc
    return f"CN_ETF_{exchange}_{code}"


def _validate_etf_share_size(frame: pd.DataFrame) -> None:
    required = ["date", "asset_id", "symbol", "market", "source"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"ETF share-size inputs are missing columns: {', '.join(missing)}")
    if frame["asset_id"].isna().any():
        raise ValueError("ETF share-size inputs contain missing asset_id values")
    if frame["date"].isna().any():
        raise ValueError("ETF share-size inputs contain missing dates")


def _write_processed_by_year(store: DatasetStore, processed: pd.DataFrame, market: str) -> None:
    for year, group in processed.groupby(pd.to_datetime(processed["date"]).dt.year):
        partitions = {"frequency": "1d", "market": market, "year": str(year)}
        merged = group
        if store.exists("processed/etf_share_size", partitions):
            existing = _coerce_processed_types(store.read_frame("processed/etf_share_size", partitions))
            merged = pd.concat([existing, group], ignore_index=True)
            merged = merged.drop_duplicates(["asset_id", "date", "source"], keep="last")
            merged = merged.sort_values(["asset_id", "date"]).reset_index(drop=True)
        _validate_etf_share_size(merged)
        store.write_frame(merged, "processed/etf_share_size", partitions)


def _coerce_processed_types(frame: pd.DataFrame) -> pd.DataFrame:
    coerced = frame.copy()
    if "date" in coerced.columns:
        coerced["date"] = pd.to_datetime(coerced["date"]).dt.date
    if "ingested_at" in coerced.columns:
        coerced["ingested_at"] = pd.to_datetime(coerced["ingested_at"], utc=True)
    return coerced


def _quality_report(frame: pd.DataFrame, market: str) -> dict[str, object]:
    if frame.empty:
        return {
            "rows": 0,
            "assets": 0,
            "market": market,
            "start_date": None,
            "end_date": None,
            "duplicate_rows": 0,
            "missing_asset_id_rows": 0,
            "missing_numeric_rows": 0,
            "missing_numeric_by_column": {},
        }
    numeric_columns = [
        column
        for column in ["total_share", "total_size", "nav", "close", "share_change_1d", "size_change_1d", "nav_premium_discount"]
        if column in frame.columns
    ]
    dates = pd.to_datetime(frame["date"])
    return {
        "rows": int(len(frame)),
        "assets": int(frame["asset_id"].nunique()),
        "market": market,
        "start_date": dates.min().date().isoformat(),
        "end_date": dates.max().date().isoformat(),
        "duplicate_rows": int(frame.duplicated(["asset_id", "date", "source"]).sum()),
        "missing_asset_id_rows": int(frame["asset_id"].isna().sum()),
        "missing_numeric_rows": int(frame[numeric_columns].isna().sum().sum()) if numeric_columns else 0,
        "missing_numeric_by_column": _missing_numeric_by_column(frame, numeric_columns),
    }


def _missing_numeric_by_column(frame: pd.DataFrame, numeric_columns: list[str]) -> dict[str, int]:
    return {
        column: int(frame[column].isna().sum())
        for column in numeric_columns
        if int(frame[column].isna().sum()) > 0
    }
