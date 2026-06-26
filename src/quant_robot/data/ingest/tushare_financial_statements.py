from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

import pandas as pd

from quant_robot.data.ingest.manifest import IngestManifest
from quant_robot.data.sources.tushare_mapping import (
    BALANCE_SHEET_COLUMNS,
    CASHFLOW_STATEMENT_COLUMNS,
    FINANCIAL_STATEMENT_COLUMNS,
    INCOME_STATEMENT_COLUMNS,
    STATEMENT_KEY_COLUMNS,
)
from quant_robot.storage.dataset_store import DatasetStore


class TushareFinancialStatementAdapter(Protocol):
    def fetch_income_statement(self, period: str, ts_code: str = "") -> pd.DataFrame:
        ...

    def fetch_balance_sheet(self, period: str, ts_code: str = "") -> pd.DataFrame:
        ...

    def fetch_cashflow_statement(self, period: str, ts_code: str = "") -> pd.DataFrame:
        ...


ENDPOINT_COLUMNS = {
    "income": INCOME_STATEMENT_COLUMNS,
    "balancesheet": BALANCE_SHEET_COLUMNS,
    "cashflow": CASHFLOW_STATEMENT_COLUMNS,
}

REQUIRED_COLUMN_GROUPS = {
    "accounting_accrual_quality": ["netprofit", "n_cashflow_act", "total_assets"],
    "asset_growth_quality": ["total_assets", "total_liab", "total_cur_assets", "total_cur_liab"],
}


def run_tushare_financial_statement_ingest(
    adapter: TushareFinancialStatementAdapter,
    periods: list[str],
    output_dir: str | Path,
    resume: bool = True,
    market: str = "CN",
    ts_codes: list[str] | None = None,
    empty_response_policy: str = "fail",
) -> dict[str, object]:
    market = market.upper()
    if market != "CN":
        raise ValueError(f"Unsupported Tushare financial-statement market: {market}")
    if empty_response_policy not in {"fail", "record"}:
        raise ValueError(f"Unsupported empty_response_policy: {empty_response_policy}")
    normalized_ts_codes = _normalize_ts_codes(ts_codes)
    if not normalized_ts_codes:
        raise ValueError("Tushare financial-statement ingest requires an explicit ts_codes list")

    output_path = Path(output_dir)
    store = DatasetStore(output_path)
    manifest = IngestManifest(output_path / "manifest.json")
    normalized_periods = [_date_to_tushare(period) for period in periods]
    requests = [(ts_code, period) for period in normalized_periods for ts_code in normalized_ts_codes]
    downloaded: list[tuple[str, str, str]] = []
    skipped: list[tuple[str, str, str]] = []
    raw_frames_by_request: dict[tuple[str, str, str], pd.DataFrame] = {}
    downloaded_rows_by_request: dict[tuple[str, str, str], int] = {}
    empty_requests: list[tuple[str, str, str]] = []

    for ts_code, period in requests:
        for endpoint in ENDPOINT_COLUMNS:
            key = _manifest_key(endpoint, period, ts_code)
            request = (endpoint, ts_code, period)
            if resume and manifest.is_completed(key) and _raw_partition_exists(store, endpoint, period, ts_code):
                skipped.append(request)
                if _manifest_completed_rows(manifest, key) == 0:
                    empty_requests.append(request)
                continue
            raw = _fetch_endpoint(adapter, endpoint, period, ts_code)
            if raw.empty:
                if empty_response_policy == "fail":
                    _mark_empty_raw_response(manifest, key, endpoint, period, ts_code)
                empty_requests.append(request)
            store.write_frame(raw, _raw_dataset(endpoint), _raw_partitions(period, ts_code))
            downloaded.append(request)
            downloaded_rows_by_request[request] = len(raw)
            raw_frames_by_request[request] = raw

    try:
        raw_by_endpoint = {
            endpoint: _load_endpoint_frames(store, endpoint, requests, raw_frames_by_request)
            for endpoint in ENDPOINT_COLUMNS
        }
        processed = _normalize_financial_statement_inputs(raw_by_endpoint, market)
        if not processed.empty:
            _validate_financial_statement_inputs(processed)
            _write_processed_by_ann_year(store, processed, market)
        report = _quality_report(processed, market)
    except Exception as exc:
        for endpoint, ts_code, period in downloaded:
            manifest.mark_failed(_manifest_key(endpoint, period, ts_code), reason=str(exc))
        manifest.save()
        raise

    for endpoint, ts_code, period in downloaded:
        request = (endpoint, ts_code, period)
        manifest.mark_completed(
            _manifest_key(endpoint, period, ts_code),
            rows=downloaded_rows_by_request[request],
        )
    manifest.save()
    (output_path / "financial_statement_quality_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    return {
        "source": "tushare",
        "dataset": "financial_statement",
        "market": market,
        "downloaded_periods": _unique_periods(downloaded),
        "skipped_periods": _unique_periods(skipped),
        "downloaded_requests": [_request_label(endpoint, ts_code, period) for endpoint, ts_code, period in downloaded],
        "skipped_requests": [_request_label(endpoint, ts_code, period) for endpoint, ts_code, period in skipped],
        "empty_requests": [_request_label(endpoint, ts_code, period) for endpoint, ts_code, period in empty_requests],
        "processed_rows": int(len(processed)),
        "quality_report": report,
        "summary": report["summary"],
    }


def _date_to_tushare(value: str) -> str:
    return str(value).replace("-", "")


def _normalize_ts_codes(ts_codes: list[str] | None) -> list[str]:
    normalized: list[str] = []
    seen = set()
    for symbol in ts_codes or []:
        value = str(symbol).strip().upper()
        if not value or value in seen:
            continue
        normalized.append(value)
        seen.add(value)
    return normalized


def _fetch_endpoint(
    adapter: TushareFinancialStatementAdapter,
    endpoint: str,
    period: str,
    ts_code: str,
) -> pd.DataFrame:
    if endpoint == "income":
        return adapter.fetch_income_statement(ts_code=ts_code, period=period)
    if endpoint == "balancesheet":
        return adapter.fetch_balance_sheet(ts_code=ts_code, period=period)
    if endpoint == "cashflow":
        return adapter.fetch_cashflow_statement(ts_code=ts_code, period=period)
    raise ValueError(f"Unsupported financial statement endpoint: {endpoint}")


def _manifest_key(endpoint: str, period: str, ts_code: str) -> str:
    return f"{endpoint}:{ts_code}:{period}"


def _raw_dataset(endpoint: str) -> str:
    return f"raw/tushare/{endpoint}"


def _raw_partitions(period: str, ts_code: str) -> dict[str, str]:
    return {"period": period, "ts_code": ts_code}


def _raw_partition_exists(store: DatasetStore, endpoint: str, period: str, ts_code: str) -> bool:
    return store.exists(_raw_dataset(endpoint), _raw_partitions(period, ts_code))


def _manifest_completed_rows(manifest: IngestManifest, key: str) -> int | None:
    row = manifest.data.get("completed", {}).get(key, {})
    if not isinstance(row, dict) or "rows" not in row:
        return None
    return int(row["rows"])


def _mark_empty_raw_response(
    manifest: IngestManifest,
    key: str,
    endpoint: str,
    period: str,
    ts_code: str,
) -> None:
    reason = f"empty raw response for {endpoint} statement {ts_code} period {period}"
    manifest.mark_failed(key, reason=reason)
    manifest.save()
    raise RuntimeError(reason)


def _load_endpoint_frames(
    store: DatasetStore,
    endpoint: str,
    requests: list[tuple[str, str]],
    raw_frames_by_request: dict[tuple[str, str, str], pd.DataFrame],
) -> pd.DataFrame:
    frames = []
    for ts_code, period in requests:
        request = (endpoint, ts_code, period)
        partitions = _raw_partitions(period, ts_code)
        if request in raw_frames_by_request:
            frames.append(raw_frames_by_request[request])
        elif store.exists(_raw_dataset(endpoint), partitions):
            frames.append(store.read_frame(_raw_dataset(endpoint), partitions))
    if not frames:
        return pd.DataFrame(columns=ENDPOINT_COLUMNS[endpoint])
    return pd.concat(frames, ignore_index=True)


def _normalize_financial_statement_inputs(raw_by_endpoint: dict[str, pd.DataFrame], market: str) -> pd.DataFrame:
    income = _coerce_statement_frame(raw_by_endpoint.get("income", pd.DataFrame()), INCOME_STATEMENT_COLUMNS)
    balance = _coerce_statement_frame(raw_by_endpoint.get("balancesheet", pd.DataFrame()), BALANCE_SHEET_COLUMNS)
    cashflow = _coerce_statement_frame(raw_by_endpoint.get("cashflow", pd.DataFrame()), CASHFLOW_STATEMENT_COLUMNS)
    merged = income.merge(balance, on=STATEMENT_KEY_COLUMNS, how="outer")
    merged = merged.merge(cashflow, on=STATEMENT_KEY_COLUMNS, how="outer")
    if merged.empty:
        return _empty_processed_frame()
    merged = merged.drop_duplicates(STATEMENT_KEY_COLUMNS, keep="last").copy()
    merged["date"] = merged["ann_date"]
    merged["asset_id"] = merged["symbol"].map(_asset_id_from_tushare_symbol)
    merged["market"] = market
    merged["source"] = "tushare_financial_statement"
    merged["ingested_at"] = pd.Timestamp.now(tz="UTC")
    ordered = ["date", "asset_id", "symbol", "market", "source", "ingested_at"] + [
        column for column in FINANCIAL_STATEMENT_COLUMNS if column != "symbol"
    ]
    for column in ordered:
        if column not in merged.columns:
            merged[column] = pd.NA
    return merged[ordered].sort_values(["asset_id", "end_date", "ann_date"]).reset_index(drop=True)


def _coerce_statement_frame(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=columns)
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Tushare statement inputs are missing columns: {', '.join(missing)}")
    coerced = frame[columns].drop_duplicates(columns, keep="last").copy()
    for column in ["ann_date", "end_date"]:
        coerced[column] = pd.to_datetime(coerced[column]).dt.date
    return coerced


def _empty_processed_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["date", "asset_id", "symbol", "market", "source", "ingested_at"]
        + [column for column in FINANCIAL_STATEMENT_COLUMNS if column != "symbol"]
    )


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


def _validate_financial_statement_inputs(frame: pd.DataFrame) -> None:
    required = ["date", "ann_date", "end_date", "asset_id", "symbol", "market", "source"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Financial statement inputs are missing columns: {', '.join(missing)}")
    if frame["asset_id"].isna().any():
        raise ValueError("Financial statement inputs contain missing asset_id values")
    if frame["ann_date"].isna().any():
        raise ValueError("Financial statement inputs contain missing ann_date values")
    if frame["end_date"].isna().any():
        raise ValueError("Financial statement inputs contain missing end_date values")


def _write_processed_by_ann_year(store: DatasetStore, processed: pd.DataFrame, market: str) -> None:
    for year, group in processed.groupby(pd.to_datetime(processed["ann_date"]).dt.year):
        partitions = {"frequency": "1q", "market": market, "year": str(year)}
        merged = group
        if store.exists("processed/financial_statement_inputs", partitions):
            existing = _coerce_processed_types(store.read_frame("processed/financial_statement_inputs", partitions))
            merged = pd.concat([existing, group], ignore_index=True)
            merged = merged.drop_duplicates(["asset_id", "ann_date", "end_date", "report_type", "source"], keep="last")
            merged = merged.sort_values(["asset_id", "end_date", "ann_date"]).reset_index(drop=True)
        _validate_financial_statement_inputs(merged)
        store.write_frame(merged, "processed/financial_statement_inputs", partitions)


def _coerce_processed_types(frame: pd.DataFrame) -> pd.DataFrame:
    coerced = frame.copy()
    for column in ["date", "ann_date", "end_date"]:
        if column in coerced.columns:
            coerced[column] = pd.to_datetime(coerced[column]).dt.date
    if "ingested_at" in coerced.columns:
        coerced["ingested_at"] = pd.to_datetime(coerced["ingested_at"], utc=True)
    return coerced


def _quality_report(frame: pd.DataFrame, market: str) -> dict[str, object]:
    groups = _required_column_group_report(frame)
    blockers = [
        f"missing_required_financial_column_group:{group['group_id']}"
        for group in groups
        if not group["passes"]
    ]
    summary = {
        "passes": not blockers,
        "blockers": blockers,
        "rows": int(len(frame)),
        "assets": int(frame["asset_id"].nunique()) if not frame.empty else 0,
        "market": market,
        "required_column_group_count": len(groups),
        "required_column_groups_passing": int(sum(1 for group in groups if group["passes"])),
        "duplicate_rows": int(frame.duplicated(["asset_id", "ann_date", "end_date", "report_type", "source"]).sum())
        if not frame.empty
        else 0,
        "missing_asset_id_rows": int(frame["asset_id"].isna().sum()) if not frame.empty else 0,
    }
    if frame.empty:
        summary.update({"ann_date_start": None, "ann_date_end": None, "report_period_start": None, "report_period_end": None})
    else:
        ann_dates = pd.to_datetime(frame["ann_date"])
        end_dates = pd.to_datetime(frame["end_date"])
        summary.update(
            {
                "ann_date_start": ann_dates.min().date().isoformat(),
                "ann_date_end": ann_dates.max().date().isoformat(),
                "report_period_start": end_dates.min().date().isoformat(),
                "report_period_end": end_dates.max().date().isoformat(),
            }
        )
    return {
        "summary": summary,
        "required_column_groups": groups,
        "required_column_groups_policy": REQUIRED_COLUMN_GROUPS,
    }


def _required_column_group_report(frame: pd.DataFrame) -> list[dict[str, object]]:
    reports: list[dict[str, object]] = []
    for group_id, columns in REQUIRED_COLUMN_GROUPS.items():
        missing_columns = [column for column in columns if column not in frame.columns]
        all_present = not missing_columns
        non_null_columns = [
            column
            for column in columns
            if column in frame.columns and (not frame.empty and int(frame[column].notna().sum()) > 0)
        ]
        passes = all_present and len(non_null_columns) == len(columns)
        reports.append(
            {
                "group_id": group_id,
                "required_columns": columns,
                "passes": passes,
                "missing_columns": missing_columns,
                "non_null_columns": non_null_columns,
            }
        )
    return reports


def _unique_periods(requests: list[tuple[str, str, str]]) -> list[str]:
    periods: list[str] = []
    for _, _, period in requests:
        if period not in periods:
            periods.append(period)
    return periods


def _request_label(endpoint: str, ts_code: str, period: str) -> str:
    return f"{endpoint}:{ts_code}:{period}"
