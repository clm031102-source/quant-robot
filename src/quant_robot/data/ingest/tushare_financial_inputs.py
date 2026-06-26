from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

import pandas as pd

from quant_robot.data.ingest.manifest import IngestManifest
from quant_robot.data.sources.tushare_mapping import FINA_INDICATOR_COLUMNS
from quant_robot.storage.dataset_store import DatasetStore


class TushareFinaIndicatorAdapter(Protocol):
    def fetch_fina_indicator(self, period: str, ts_code: str = "") -> pd.DataFrame:
        ...


def run_tushare_fina_indicator_ingest(
    adapter: TushareFinaIndicatorAdapter,
    periods: list[str],
    output_dir: str | Path,
    resume: bool = True,
    market: str = "CN",
    ts_codes: list[str] | None = None,
    empty_response_policy: str = "fail",
) -> dict[str, object]:
    market = market.upper()
    if market != "CN":
        raise ValueError(f"Unsupported Tushare financial-input market: {market}")
    if empty_response_policy not in {"fail", "record"}:
        raise ValueError(f"Unsupported empty_response_policy: {empty_response_policy}")
    output_path = Path(output_dir)
    store = DatasetStore(output_path)
    manifest = IngestManifest(output_path / "manifest.json")
    normalized_periods = [_date_to_tushare(period) for period in periods]
    normalized_ts_codes = ts_codes or [""]
    requests = [(ts_code, period) for period in normalized_periods for ts_code in normalized_ts_codes]
    downloaded: list[tuple[str, str]] = []
    skipped: list[tuple[str, str]] = []
    raw_frames_by_request: dict[tuple[str, str], pd.DataFrame] = {}
    downloaded_rows_by_request: dict[tuple[str, str], int] = {}
    empty_requests: list[tuple[str, str]] = []

    for ts_code, period in requests:
        key = _manifest_key(period, ts_code)
        if resume and manifest.is_completed(key) and _raw_partition_exists(store, _raw_dataset(), period, ts_code):
            skipped.append((ts_code, period))
            if _manifest_completed_rows(manifest, key) == 0:
                empty_requests.append((ts_code, period))
            continue
        raw = adapter.fetch_fina_indicator(ts_code=ts_code, period=period)
        if raw.empty:
            if empty_response_policy == "fail":
                _mark_empty_raw_response(manifest, key, period)
            empty_requests.append((ts_code, period))
        store.write_frame(raw, _raw_dataset(), _raw_partitions(period, ts_code))
        downloaded.append((ts_code, period))
        downloaded_rows_by_request[(ts_code, period)] = len(raw)
        raw_frames_by_request[(ts_code, period)] = raw

    try:
        raw_for_processing = _load_raw_frames(store, requests, raw_frames_by_request)
        processed = _normalize_fina_indicator(raw_for_processing, market)
        if not processed.empty:
            _validate_financial_inputs(processed)
            _write_processed_by_ann_year(store, processed, market)
        report = _quality_report(processed, market)
    except Exception as exc:
        for ts_code, period in downloaded:
            manifest.mark_failed(_manifest_key(period, ts_code), reason=str(exc))
        manifest.save()
        raise

    for ts_code, period in downloaded:
        manifest.mark_completed(_manifest_key(period, ts_code), rows=downloaded_rows_by_request[(ts_code, period)])
    manifest.save()
    (output_path / "financial_input_quality_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {
        "source": "tushare",
        "dataset": "fina_indicator",
        "market": market,
        "downloaded_periods": _unique_periods(downloaded),
        "skipped_periods": _unique_periods(skipped),
        "downloaded_requests": [_request_label(ts_code, period) for ts_code, period in downloaded],
        "skipped_requests": [_request_label(ts_code, period) for ts_code, period in skipped],
        "empty_requests": [_request_label(ts_code, period) for ts_code, period in empty_requests],
        "processed_rows": int(len(processed)),
        "quality_report": report,
    }


def _date_to_tushare(value: str) -> str:
    return str(value).replace("-", "")


def _manifest_key(period: str, ts_code: str = "") -> str:
    return f"fina_indicator:{ts_code}:{period}" if ts_code else f"fina_indicator:{period}"


def _raw_dataset() -> str:
    return "raw/tushare/fina_indicator"


def _raw_partition_has_rows(store: DatasetStore, dataset: str, period: str, ts_code: str = "") -> bool:
    partitions = _raw_partitions(period, ts_code)
    if not store.exists(dataset, partitions):
        return False
    try:
        return len(store.read_frame(dataset, partitions)) > 0
    except FileNotFoundError:
        return False


def _raw_partition_exists(store: DatasetStore, dataset: str, period: str, ts_code: str = "") -> bool:
    return store.exists(dataset, _raw_partitions(period, ts_code))


def _manifest_completed_rows(manifest: IngestManifest, key: str) -> int | None:
    row = manifest.data.get("completed", {}).get(key, {})
    if not isinstance(row, dict) or "rows" not in row:
        return None
    return int(row["rows"])


def _mark_empty_raw_response(manifest: IngestManifest, key: str, period: str) -> None:
    reason = f"empty raw response for financial period {period}"
    manifest.mark_failed(key, reason=reason)
    manifest.save()
    raise RuntimeError(reason)


def _load_raw_frames(
    store: DatasetStore,
    requests: list[tuple[str, str]],
    raw_frames_by_request: dict[tuple[str, str], pd.DataFrame],
) -> pd.DataFrame:
    frames = []
    for ts_code, period in requests:
        request = (ts_code, period)
        partitions = _raw_partitions(period, ts_code)
        if request in raw_frames_by_request:
            frames.append(raw_frames_by_request[request])
        elif store.exists(_raw_dataset(), partitions):
            frames.append(store.read_frame(_raw_dataset(), partitions))
    if not frames:
        return pd.DataFrame(columns=FINA_INDICATOR_COLUMNS)
    return pd.concat(frames, ignore_index=True)


def _raw_partitions(period: str, ts_code: str = "") -> dict[str, str]:
    partitions = {"period": period}
    if ts_code:
        partitions["ts_code"] = ts_code
    return partitions


def _unique_periods(requests: list[tuple[str, str]]) -> list[str]:
    periods: list[str] = []
    for _, period in requests:
        if period not in periods:
            periods.append(period)
    return periods


def _request_label(ts_code: str, period: str) -> str:
    return f"{ts_code}:{period}" if ts_code else period


def _normalize_fina_indicator(raw: pd.DataFrame, market: str) -> pd.DataFrame:
    required = FINA_INDICATOR_COLUMNS
    missing = [column for column in required if column not in raw.columns]
    if missing:
        raise ValueError(f"Tushare fina_indicator inputs are missing columns: {', '.join(missing)}")
    source = raw.drop_duplicates(FINA_INDICATOR_COLUMNS, keep="last").copy()
    source["ann_date"] = pd.to_datetime(source["ann_date"]).dt.date
    source["end_date"] = pd.to_datetime(source["end_date"]).dt.date
    source = source.drop_duplicates(["symbol", "ann_date", "end_date"], keep="last").copy()
    source["date"] = source["ann_date"]
    source["asset_id"] = source["symbol"].map(_asset_id_from_tushare_symbol)
    source["market"] = market
    source["source"] = "tushare_fina_indicator"
    source["ingested_at"] = pd.Timestamp.now(tz="UTC")
    ordered = ["date", "asset_id", "symbol", "market", "source", "ingested_at"] + [
        column for column in FINA_INDICATOR_COLUMNS if column != "symbol"
    ]
    return source[ordered].sort_values(["asset_id", "end_date", "ann_date"]).reset_index(drop=True)


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


def _validate_financial_inputs(frame: pd.DataFrame) -> None:
    required = ["date", "ann_date", "end_date", "asset_id", "symbol", "market", "source"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Financial inputs are missing columns: {', '.join(missing)}")
    if frame["asset_id"].isna().any():
        raise ValueError("Financial inputs contain missing asset_id values")
    if frame["ann_date"].isna().any():
        raise ValueError("Financial inputs contain missing ann_date values")
    if frame["end_date"].isna().any():
        raise ValueError("Financial inputs contain missing end_date values")


def _write_processed_by_ann_year(store: DatasetStore, processed: pd.DataFrame, market: str) -> None:
    for year, group in processed.groupby(pd.to_datetime(processed["ann_date"]).dt.year):
        partitions = {"frequency": "1q", "market": market, "year": str(year)}
        merged = group
        if store.exists("processed/fina_indicator_inputs", partitions):
            existing = _coerce_processed_types(store.read_frame("processed/fina_indicator_inputs", partitions))
            merged = pd.concat([existing, group], ignore_index=True)
            merged = merged.drop_duplicates(["asset_id", "ann_date", "end_date", "source"], keep="last")
            merged = merged.sort_values(["asset_id", "end_date", "ann_date"]).reset_index(drop=True)
        _validate_financial_inputs(merged)
        store.write_frame(merged, "processed/fina_indicator_inputs", partitions)


def _coerce_processed_types(frame: pd.DataFrame) -> pd.DataFrame:
    coerced = frame.copy()
    for column in ["date", "ann_date", "end_date"]:
        if column in coerced.columns:
            coerced[column] = pd.to_datetime(coerced[column]).dt.date
    if "ingested_at" in coerced.columns:
        coerced["ingested_at"] = pd.to_datetime(coerced["ingested_at"], utc=True)
    return coerced


def _quality_report(frame: pd.DataFrame, market: str) -> dict[str, object]:
    if frame.empty:
        return {
            "rows": 0,
            "assets": 0,
            "market": market,
            "ann_date_start": None,
            "ann_date_end": None,
            "report_period_start": None,
            "report_period_end": None,
            "duplicate_rows": 0,
            "missing_asset_id_rows": 0,
            "missing_numeric_rows": 0,
            "missing_numeric_by_column": {},
        }
    numeric_columns = [column for column in FINA_INDICATOR_COLUMNS if column not in {"symbol", "ann_date", "end_date"}]
    ann_dates = pd.to_datetime(frame["ann_date"])
    end_dates = pd.to_datetime(frame["end_date"])
    return {
        "rows": int(len(frame)),
        "assets": int(frame["asset_id"].nunique()),
        "market": market,
        "ann_date_start": ann_dates.min().date().isoformat(),
        "ann_date_end": ann_dates.max().date().isoformat(),
        "report_period_start": end_dates.min().date().isoformat(),
        "report_period_end": end_dates.max().date().isoformat(),
        "duplicate_rows": int(frame.duplicated(["asset_id", "ann_date", "end_date", "source"]).sum()),
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
