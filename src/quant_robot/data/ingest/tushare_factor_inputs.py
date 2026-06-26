from __future__ import annotations

import json
from pathlib import Path
from time import sleep
from typing import Protocol

import pandas as pd

from quant_robot.data.ingest.manifest import IngestManifest
from quant_robot.data.sources.tushare_mapping import DAILY_BASIC_COLUMNS
from quant_robot.storage.dataset_store import DatasetStore


class TushareDailyBasicAdapter(Protocol):
    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        ...

    def fetch_daily_basic_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        ...


def run_tushare_daily_basic_ingest(
    adapter: TushareDailyBasicAdapter,
    start_date: str,
    end_date: str,
    output_dir: str | Path,
    resume: bool = True,
    market: str = "CN",
    empty_response_retries: int = 3,
    empty_response_retry_sleep_seconds: float = 1.0,
) -> dict[str, object]:
    market = market.upper()
    if market != "CN":
        raise ValueError(f"Unsupported Tushare factor-input market: {market}")
    output_path = Path(output_dir)
    store = DatasetStore(output_path)
    manifest = IngestManifest(output_path / "manifest.json")
    downloaded: list[str] = []
    skipped: list[str] = []
    raw_frames_by_date: dict[str, pd.DataFrame] = {}
    downloaded_rows_by_date: dict[str, int] = {}

    trade_dates = _trade_dates(adapter, start_date, end_date)
    for trade_date in trade_dates:
        key = _manifest_key(trade_date)
        if resume and manifest.is_completed(key) and _raw_partition_has_rows(store, _raw_dataset(), trade_date):
            skipped.append(trade_date)
            continue
        raw = _fetch_non_empty_daily_basic(
            adapter,
            trade_date,
            empty_response_retries=empty_response_retries,
            retry_sleep_seconds=empty_response_retry_sleep_seconds,
        )
        if raw.empty:
            _mark_empty_raw_response(manifest, key, trade_date)
        store.write_frame(raw, _raw_dataset(), {"trade_date": trade_date})
        downloaded.append(trade_date)
        downloaded_rows_by_date[trade_date] = len(raw)
        raw_frames_by_date[trade_date] = raw

    try:
        raw_for_processing = _load_raw_frames(store, trade_dates, raw_frames_by_date)
        processed = _normalize_daily_basic(raw_for_processing, market)
        if not processed.empty:
            _validate_factor_inputs(processed)
            _write_processed_by_year(store, processed, market)
        report = _quality_report(processed)
    except Exception as exc:
        for trade_date in downloaded:
            manifest.mark_failed(_manifest_key(trade_date), reason=str(exc))
        manifest.save()
        raise

    for trade_date in downloaded:
        manifest.mark_completed(_manifest_key(trade_date), rows=downloaded_rows_by_date[trade_date])
    manifest.save()
    (output_path / "factor_input_quality_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {
        "source": "tushare",
        "dataset": "daily_basic",
        "market": market,
        "downloaded_trade_dates": downloaded,
        "skipped_trade_dates": skipped,
        "processed_rows": int(len(processed)),
        "quality_report": report,
    }


def _trade_dates(adapter: TushareDailyBasicAdapter, start_date: str, end_date: str) -> list[str]:
    calendar = adapter.fetch_trade_calendar(start_date, end_date)
    dates = pd.to_datetime(calendar["date"]).dt.strftime("%Y%m%d")
    return list(dates)


def _fetch_non_empty_daily_basic(
    adapter: TushareDailyBasicAdapter,
    trade_date: str,
    *,
    empty_response_retries: int,
    retry_sleep_seconds: float,
) -> pd.DataFrame:
    attempts = max(int(empty_response_retries), 0) + 1
    raw = pd.DataFrame()
    for attempt in range(attempts):
        raw = adapter.fetch_daily_basic_by_trade_date(trade_date)
        if not raw.empty:
            return raw
        if attempt < attempts - 1 and retry_sleep_seconds > 0.0:
            sleep(float(retry_sleep_seconds))
    return raw


def _manifest_key(trade_date: str) -> str:
    return f"daily_basic:{trade_date}"


def _raw_dataset() -> str:
    return "raw/tushare/daily_basic"


def _raw_partition_has_rows(store: DatasetStore, dataset: str, trade_date: str) -> bool:
    partitions = {"trade_date": trade_date}
    if not store.exists(dataset, partitions):
        return False
    try:
        return len(store.read_frame(dataset, partitions)) > 0
    except FileNotFoundError:
        return False


def _mark_empty_raw_response(manifest: IngestManifest, key: str, trade_date: str) -> None:
    reason = f"empty raw response for open trade date {trade_date}"
    manifest.mark_failed(key, reason=reason)
    manifest.save()
    raise RuntimeError(reason)


def _load_raw_frames(
    store: DatasetStore,
    trade_dates: list[str],
    raw_frames_by_date: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    frames = []
    for trade_date in trade_dates:
        if trade_date in raw_frames_by_date:
            frames.append(raw_frames_by_date[trade_date])
        elif store.exists(_raw_dataset(), {"trade_date": trade_date}):
            frames.append(store.read_frame(_raw_dataset(), {"trade_date": trade_date}))
    if not frames:
        return pd.DataFrame(columns=DAILY_BASIC_COLUMNS)
    return pd.concat(frames, ignore_index=True)


def _normalize_daily_basic(raw: pd.DataFrame, market: str) -> pd.DataFrame:
    required = ["symbol", "date"]
    missing = [column for column in required if column not in raw.columns]
    if missing:
        raise ValueError(f"Tushare daily_basic factor inputs are missing columns: {', '.join(missing)}")
    source = raw.copy()
    source["date"] = pd.to_datetime(source["date"]).dt.date
    source["asset_id"] = source["symbol"].map(_asset_id_from_tushare_symbol)
    source["market"] = market
    source["source"] = "tushare"
    source["ingested_at"] = pd.Timestamp.now(tz="UTC")
    ordered = ["date", "asset_id", "symbol", "market", "source", "ingested_at"] + [
        column for column in DAILY_BASIC_COLUMNS if column not in {"symbol", "date"}
    ]
    return source[ordered].sort_values(["asset_id", "date"]).reset_index(drop=True)


def _asset_id_from_tushare_symbol(symbol: str) -> str:
    parts = str(symbol).split(".")
    if len(parts) != 2:
        raise ValueError(f"Unsupported Tushare symbol: {symbol}")
    code, suffix = parts
    exchange_by_suffix = {"SZ": "XSHE", "SH": "XSHG", "BJ": "XBEI"}
    try:
        exchange = exchange_by_suffix[suffix.upper()]
    except KeyError as exc:
        raise ValueError(f"Unsupported Tushare symbol suffix: {symbol}") from exc
    return f"CN_{exchange}_{code}"


def _validate_factor_inputs(frame: pd.DataFrame) -> None:
    required = ["date", "asset_id", "symbol", "market", "source"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Factor inputs are missing columns: {', '.join(missing)}")
    if frame["asset_id"].isna().any():
        raise ValueError("Factor inputs contain missing asset_id values")
    if frame["date"].isna().any():
        raise ValueError("Factor inputs contain missing dates")


def _write_processed_by_year(store: DatasetStore, processed: pd.DataFrame, market: str) -> None:
    for year, group in processed.groupby(pd.to_datetime(processed["date"]).dt.year):
        partitions = {"frequency": "1d", "market": market, "year": str(year)}
        merged = group
        if store.exists("processed/factor_inputs", partitions):
            existing = _coerce_processed_types(store.read_frame("processed/factor_inputs", partitions))
            merged = pd.concat([existing, group], ignore_index=True)
            merged = merged.drop_duplicates(["asset_id", "date", "source"], keep="last")
            merged = merged.sort_values(["asset_id", "date"]).reset_index(drop=True)
        _validate_factor_inputs(merged)
        store.write_frame(merged, "processed/factor_inputs", partitions)


def _coerce_processed_types(frame: pd.DataFrame) -> pd.DataFrame:
    coerced = frame.copy()
    if "date" in coerced.columns:
        coerced["date"] = pd.to_datetime(coerced["date"]).dt.date
    if "ingested_at" in coerced.columns:
        coerced["ingested_at"] = pd.to_datetime(coerced["ingested_at"], utc=True)
    return coerced


def _quality_report(frame: pd.DataFrame) -> dict[str, object]:
    if frame.empty:
        return {
            "rows": 0,
            "assets": 0,
            "market": "CN",
            "start_date": None,
            "end_date": None,
            "duplicate_rows": 0,
            "missing_asset_id_rows": 0,
            "missing_numeric_rows": 0,
            "missing_numeric_by_column": {},
        }
    numeric_columns = [column for column in DAILY_BASIC_COLUMNS if column not in {"symbol", "date"} and column in frame.columns]
    dates = pd.to_datetime(frame["date"])
    return {
        "rows": int(len(frame)),
        "assets": int(frame["asset_id"].nunique()),
        "market": "CN",
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
