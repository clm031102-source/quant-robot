from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Protocol, Sequence

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore


class TushareForecastExpressEventAdapter(Protocol):
    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        ...

    def fetch_event_endpoint(self, endpoint: str, **kwargs: object) -> pd.DataFrame:
        ...


ProgressCallback = Callable[[dict[str, object]], None]

FORECAST_VALUE_COLUMNS = [
    "p_change_min",
    "p_change_max",
    "p_change_mid",
    "net_profit_min",
    "net_profit_max",
    "net_profit_mid",
]
EXPRESS_VALUE_COLUMNS = ["yoy_net_profit", "diluted_roe", "total_revenue"]
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"


def run_tushare_forecast_express_event_cache(
    adapter: TushareForecastExpressEventAdapter,
    start_date: str,
    end_date: str,
    output_dir: str | Path,
    *,
    processed_output_dir: str | Path | None = None,
    execute_write_processed: bool = False,
    market: str = "CN",
    endpoints: Sequence[str] = ("forecast", "express"),
    progress_callback: ProgressCallback | None = None,
    empty_calendar_retries: int = 2,
) -> dict[str, object]:
    market = market.upper()
    if market != "CN":
        raise ValueError(f"Unsupported Tushare forecast/express event market: {market}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    processed_path = Path(processed_output_dir) if processed_output_dir else output_path
    if execute_write_processed:
        processed_path.mkdir(parents=True, exist_ok=True)
    store = DatasetStore(processed_path)

    calendar_dates = _calendar_dates(
        adapter,
        start_date,
        end_date,
        empty_calendar_retries=empty_calendar_retries,
        progress_callback=progress_callback,
    )
    windows = _month_windows(start_date, end_date)
    fetch_failures: list[dict[str, object]] = []
    endpoint_set = {str(endpoint).strip() for endpoint in endpoints if str(endpoint).strip()}

    raw_forecast = (
        _fetch_endpoint_windows(adapter, "forecast", windows, progress_callback, fetch_failures)
        if "forecast" in endpoint_set
        else pd.DataFrame()
    )
    raw_express = (
        _fetch_endpoint_windows(adapter, "express", windows, progress_callback, fetch_failures)
        if "express" in endpoint_set
        else pd.DataFrame()
    )

    forecast = _normalize_forecast(raw_forecast, calendar_dates, market)
    express = _normalize_express(raw_express, calendar_dates, market)
    fetch_failures_by_endpoint = _fetch_failure_counts(fetch_failures)
    feed_quality: dict[str, dict[str, object]] = {}
    if "forecast" in endpoint_set:
        feed_quality["event_forecast"] = _event_feed_quality(
            forecast,
            key_columns=["symbol", "event_date", "end_date"],
            value_columns=FORECAST_VALUE_COLUMNS,
            fetch_failure_count=fetch_failures_by_endpoint.get("forecast", 0),
        )
    if "express" in endpoint_set:
        feed_quality["event_express"] = _event_feed_quality(
            express,
            key_columns=["symbol", "event_date", "end_date"],
            value_columns=EXPRESS_VALUE_COLUMNS,
            fetch_failure_count=fetch_failures_by_endpoint.get("express", 0),
        )

    if execute_write_processed:
        if "forecast" in endpoint_set:
            _write_processed_by_year(
                store,
                "processed/event_forecast",
                forecast,
                market,
                ["symbol", "event_date", "end_date"],
            )
        if "express" in endpoint_set:
            _write_processed_by_year(
                store,
                "processed/event_express",
                express,
                market,
                ["symbol", "event_date", "end_date"],
            )
        _write_coverage_manifest(
            store,
            start_date=start_date,
            end_date=end_date,
            market=market,
            forecast_rows=len(forecast),
            express_rows=len(express),
        )

    result: dict[str, object] = {
        "source": "tushare",
        "market": market,
        "start_date": _date_iso(start_date),
        "end_date": _date_iso(end_date),
        "query_mode": "monthly_range_with_forecast_ann_date_fallback",
        "query_windows": [
            {"start_date": _date_to_tushare(start), "end_date": _date_to_tushare(end)}
            for start, end in windows
        ],
        "processed_output_dir": str(processed_path),
        "processed_writes_enabled": bool(execute_write_processed),
        "summary": _summary(feed_quality),
        "feed_quality": feed_quality,
        "fetch_failures": fetch_failures,
        "safety": SAFETY,
        "live_boundary_allowed": False,
    }
    (output_path / "forecast_express_event_cache_report.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result


def _fetch_endpoint_windows(
    adapter: TushareForecastExpressEventAdapter,
    endpoint: str,
    windows: Sequence[tuple[pd.Timestamp, pd.Timestamp]],
    progress_callback: ProgressCallback | None,
    fetch_failures: list[dict[str, object]],
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for start, end in windows:
        labels = {
            "endpoint": endpoint,
            "start_date": _date_to_tushare(start),
            "end_date": _date_to_tushare(end),
        }
        _emit_progress(progress_callback, status="start", **labels)
        try:
            frame = adapter.fetch_event_endpoint(
                endpoint,
                start_date=_date_to_tushare(start),
                end_date=_date_to_tushare(end),
            )
        except Exception as exc:  # pragma: no cover - exercised with live providers
            if endpoint == "forecast":
                fallback_frame, fallback_failures = _fetch_forecast_ann_date_window(
                    adapter,
                    start,
                    end,
                    progress_callback,
                )
                if not fallback_failures:
                    _emit_progress(
                        progress_callback,
                        endpoint=endpoint,
                        status="fallback_done",
                        rows=int(len(fallback_frame)),
                        fallback="ann_date",
                        start_date=_date_to_tushare(start),
                        end_date=_date_to_tushare(end),
                    )
                    if not fallback_frame.empty:
                        frames.append(fallback_frame)
                    continue
                fetch_failures.extend(fallback_failures)
                continue
            failure = {**labels, "status": "fail", "error": type(exc).__name__, "message": str(exc)}
            fetch_failures.append(failure)
            _emit_progress(progress_callback, **failure)
            continue
        rows = int(len(frame)) if frame is not None else 0
        _emit_progress(progress_callback, status="done", rows=rows, **labels)
        if frame is not None and not frame.empty:
            frames.append(frame.copy())
    return _concat(frames)


def _fetch_forecast_ann_date_window(
    adapter: TushareForecastExpressEventAdapter,
    start: pd.Timestamp,
    end: pd.Timestamp,
    progress_callback: ProgressCallback | None,
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    frames: list[pd.DataFrame] = []
    failures: list[dict[str, object]] = []
    for date_value in pd.date_range(start, end, freq="D"):
        ann_date = _date_to_tushare(date_value)
        _emit_progress(progress_callback, endpoint="forecast", status="fallback_start", ann_date=ann_date)
        try:
            frame = adapter.fetch_event_endpoint("forecast", ann_date=ann_date)
        except Exception as exc:  # pragma: no cover - exercised with live providers
            failure = {
                "endpoint": "forecast",
                "status": "fail",
                "ann_date": ann_date,
                "fallback": "ann_date",
                "error": type(exc).__name__,
                "message": str(exc),
            }
            failures.append(failure)
            _emit_progress(progress_callback, **failure)
            continue
        rows = int(len(frame)) if frame is not None else 0
        _emit_progress(progress_callback, endpoint="forecast", status="fallback_done", ann_date=ann_date, rows=rows)
        if frame is not None and not frame.empty:
            frames.append(frame.copy())
    return _concat(frames), failures


def _normalize_forecast(raw: pd.DataFrame, calendar_dates: list[pd.Timestamp], market: str) -> pd.DataFrame:
    columns = [
        "event_date",
        "available_date",
        "asset_id",
        "symbol",
        "market",
        "source",
        "ingested_at",
        "end_date",
        "forecast_type",
        *FORECAST_VALUE_COLUMNS,
        "source_event_count",
    ]
    if raw.empty:
        return pd.DataFrame(columns=columns)
    source = raw.copy()
    mapped = pd.DataFrame(
        {
            "symbol": _symbol(source),
            "event_date": _date(source, ["ann_date", "event_date", "date"]),
            "end_date": _optional_date(source, "end_date"),
            "forecast_type": _text(source, "type"),
            "p_change_min": _numeric(source, "p_change_min"),
            "p_change_max": _numeric(source, "p_change_max"),
            "net_profit_min": _numeric(source, "net_profit_min"),
            "net_profit_max": _numeric(source, "net_profit_max"),
        }
    )
    mapped["p_change_mid"] = (mapped["p_change_min"] + mapped["p_change_max"]) / 2.0
    mapped["net_profit_mid"] = (mapped["net_profit_min"] + mapped["net_profit_max"]) / 2.0
    common = _with_common_event_columns(mapped, columns, calendar_dates, market, "tushare_forecast")
    return _aggregate_event_rows(common, value_columns=FORECAST_VALUE_COLUMNS, text_columns=["forecast_type"])[columns]


def _normalize_express(raw: pd.DataFrame, calendar_dates: list[pd.Timestamp], market: str) -> pd.DataFrame:
    columns = [
        "event_date",
        "available_date",
        "asset_id",
        "symbol",
        "market",
        "source",
        "ingested_at",
        "end_date",
        *EXPRESS_VALUE_COLUMNS,
        "source_event_count",
    ]
    if raw.empty:
        return pd.DataFrame(columns=columns)
    source = raw.copy()
    mapped = pd.DataFrame(
        {
            "symbol": _symbol(source),
            "event_date": _date(source, ["ann_date", "event_date", "date"]),
            "end_date": _optional_date(source, "end_date"),
            "yoy_net_profit": _numeric(source, "yoy_net_profit", fallback="net_profit_yoy"),
            "diluted_roe": _numeric(source, "diluted_roe", fallback="roe_diluted"),
            "total_revenue": _numeric(source, "total_revenue", fallback="revenue"),
        }
    )
    common = _with_common_event_columns(mapped, columns, calendar_dates, market, "tushare_express")
    return _aggregate_event_rows(common, value_columns=EXPRESS_VALUE_COLUMNS)[columns]


def _with_common_event_columns(
    frame: pd.DataFrame,
    columns: list[str],
    calendar_dates: list[pd.Timestamp],
    market: str,
    source_name: str,
) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=columns)
    output = frame.dropna(subset=["symbol", "event_date"]).copy()
    output["symbol"] = output["symbol"].astype(str)
    output["asset_id"] = output["symbol"].map(_asset_id_from_tushare_symbol)
    output = output.dropna(subset=["asset_id"]).copy()
    output["available_date"] = output["event_date"].map(lambda value: _next_trade_after(calendar_dates, value))
    output["market"] = market
    output["source"] = source_name
    output["ingested_at"] = pd.Timestamp.now(tz="UTC")
    for column in columns:
        if column not in output.columns:
            output[column] = pd.NA
    return output[columns].sort_values(["event_date", "symbol", "end_date"]).reset_index(drop=True)


def _aggregate_event_rows(
    frame: pd.DataFrame,
    *,
    value_columns: Sequence[str],
    text_columns: Sequence[str] = (),
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    keys = ["symbol", "event_date", "end_date", "asset_id", "market", "available_date", "source"]
    aggregations: dict[str, object] = {column: (column, "mean") for column in value_columns}
    for column in text_columns:
        aggregations[column] = (column, _join_unique_text)
    aggregations["ingested_at"] = ("ingested_at", "max")
    aggregations["source_event_count"] = ("symbol", "size")
    return (
        frame.groupby(keys, as_index=False, dropna=False)
        .agg(**aggregations)
        .sort_values(["event_date", "symbol", "end_date"])
        .reset_index(drop=True)
    )


def _event_feed_quality(
    frame: pd.DataFrame,
    *,
    key_columns: Sequence[str],
    value_columns: Sequence[str],
    fetch_failure_count: int = 0,
) -> dict[str, object]:
    duplicate_key_count = int(frame.duplicated(list(key_columns)).sum()) if not frame.empty else 0
    missing_available_date_count = int(pd.to_datetime(frame.get("available_date"), errors="coerce").isna().sum()) if not frame.empty else 0
    non_null_value_rows = int(frame[list(value_columns)].notna().any(axis=1).sum()) if not frame.empty else 0
    status = "pass"
    if frame.empty or duplicate_key_count or missing_available_date_count or fetch_failure_count:
        status = "fail"
    return {
        "status": status,
        "rows": int(len(frame)),
        "unique_assets": int(frame["asset_id"].nunique()) if "asset_id" in frame else 0,
        "unique_event_dates": int(pd.to_datetime(frame["event_date"], errors="coerce").nunique()) if "event_date" in frame else 0,
        "date_min": _nullable_date_min(frame.get("event_date", pd.Series(dtype=object))),
        "date_max": _nullable_date_max(frame.get("event_date", pd.Series(dtype=object))),
        "available_date_min": _nullable_date_min(frame.get("available_date", pd.Series(dtype=object))),
        "available_date_max": _nullable_date_max(frame.get("available_date", pd.Series(dtype=object))),
        "duplicate_key_count": duplicate_key_count,
        "missing_available_date_count": missing_available_date_count,
        "non_null_value_rows": non_null_value_rows,
        "fetch_failure_count": int(fetch_failure_count),
    }


def _summary(feed_quality: dict[str, dict[str, object]]) -> dict[str, object]:
    total_rows = sum(int(item.get("rows", 0)) for item in feed_quality.values())
    fail_count = sum(1 for item in feed_quality.values() if item.get("status") != "pass")
    return {
        "endpoint_count": int(len(feed_quality)),
        "pass_count": int(len(feed_quality) - fail_count),
        "fail_count": int(fail_count),
        "total_rows": int(total_rows),
        "promotion_allowed": False,
        "portfolio_backtest_allowed": False,
        "next_required_gate": "round255_forecast_express_cache_coverage_then_orthogonal_event_prescreen",
    }


def _write_processed_by_year(
    store: DatasetStore,
    dataset: str,
    frame: pd.DataFrame,
    market: str,
    dedupe_keys: Sequence[str],
    *,
    date_column: str = "event_date",
) -> None:
    if frame.empty:
        return
    dates = pd.to_datetime(frame[date_column])
    for year, group in frame.groupby(dates.dt.year):
        partitions = {"frequency": "event", "market": market, "year": str(year)}
        merged = group
        if store.exists(dataset, partitions):
            existing = store.read_frame(dataset, partitions)
            merged = pd.concat([existing, group], ignore_index=True)
            merged = merged.drop_duplicates(list(dedupe_keys), keep="last")
        store.write_frame(merged, dataset, partitions)


def _write_coverage_manifest(
    store: DatasetStore,
    *,
    start_date: str,
    end_date: str,
    market: str,
    forecast_rows: int,
    express_rows: int,
) -> None:
    shard_id = f"{pd.Timestamp(start_date):%Y%m%d}_{pd.Timestamp(end_date):%Y%m%d}"
    frame = pd.DataFrame(
        {
            "feed": ["event_forecast", "event_express"],
            "start_date": [_date_iso(start_date)] * 2,
            "end_date": [_date_iso(end_date)] * 2,
            "market": [market] * 2,
            "source": ["tushare"] * 2,
            "rows": [int(forecast_rows), int(express_rows)],
            "shard_id": [shard_id] * 2,
            "ingested_at": [pd.Timestamp.now(tz="UTC")] * 2,
        }
    )
    store.write_frame(frame, "metadata/tushare_forecast_express_event_cache_coverage", {"market": market, "shard": shard_id})


def _calendar_dates(
    adapter: TushareForecastExpressEventAdapter,
    start_date: str,
    end_date: str,
    *,
    empty_calendar_retries: int,
    progress_callback: ProgressCallback | None,
) -> list[pd.Timestamp]:
    padded_end = (pd.to_datetime(end_date) + pd.Timedelta(days=14)).date().isoformat()
    max_attempts = max(1, empty_calendar_retries + 1)
    for attempt in range(1, max_attempts + 1):
        calendar = adapter.fetch_trade_calendar(start_date, padded_end)
        if "date" not in calendar.columns:
            raise ValueError("Tushare trade calendar response is missing date")
        dates = pd.to_datetime(calendar["date"]).dropna().sort_values().drop_duplicates()
        if not dates.empty:
            return [pd.Timestamp(value).normalize() for value in dates]
        if attempt < max_attempts:
            _emit_progress(progress_callback, endpoint="trade_calendar", status="empty_retry", attempt=attempt)
    raise ValueError("Tushare trade calendar response has no open trade dates")


def _month_windows(start_date: str, end_date: str) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    start = pd.Timestamp(start_date).normalize().replace(day=1)
    end = pd.Timestamp(end_date).normalize()
    windows: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    current = start
    while current <= end:
        month_end = current + pd.offsets.MonthEnd(0)
        windows.append((current, min(pd.Timestamp(month_end).normalize(), end)))
        current = (current + pd.offsets.MonthBegin(1)).normalize()
    return windows


def _next_trade_after(calendar_dates: list[pd.Timestamp], value: object) -> object:
    current = pd.Timestamp(value).normalize()
    for trade_date in calendar_dates:
        if trade_date > current:
            return trade_date.date()
    return pd.NaT


def _fetch_failure_counts(fetch_failures: Sequence[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for failure in fetch_failures:
        endpoint = str(failure.get("endpoint", ""))
        if endpoint:
            counts[endpoint] = counts.get(endpoint, 0) + 1
    return counts


def _concat(frames: Sequence[pd.DataFrame]) -> pd.DataFrame:
    usable = [frame for frame in frames if frame is not None and not frame.empty]
    if not usable:
        return pd.DataFrame()
    return pd.concat(usable, ignore_index=True).drop_duplicates().reset_index(drop=True)


def _symbol(frame: pd.DataFrame) -> pd.Series:
    if "ts_code" in frame.columns:
        return frame["ts_code"].astype(str)
    if "symbol" in frame.columns:
        return frame["symbol"].astype(str)
    raise ValueError("Forecast/express event frame is missing symbol/ts_code")


def _date(frame: pd.DataFrame, columns: Sequence[str]) -> pd.Series:
    for column in columns:
        if column in frame.columns:
            return _parse_dates(frame[column])
    raise ValueError(f"Forecast/express event frame is missing date columns: {', '.join(columns)}")


def _parse_dates(values: pd.Series) -> pd.Series:
    text = values.astype(str)
    digit_mask = text.str.fullmatch(r"\d{8}")
    parsed = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    if digit_mask.any():
        parsed.loc[digit_mask] = pd.to_datetime(text.loc[digit_mask], format="%Y%m%d")
    if (~digit_mask).any():
        parsed.loc[~digit_mask] = pd.to_datetime(values.loc[~digit_mask], errors="coerce")
    return parsed.dt.date


def _optional_date(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([pd.NaT] * len(frame), index=frame.index)
    return pd.to_datetime(frame[column], errors="coerce").dt.date


def _numeric(frame: pd.DataFrame, column: str, *, fallback: str | None = None) -> pd.Series:
    for name in (column, fallback):
        if name and name in frame.columns:
            return pd.to_numeric(frame[name], errors="coerce")
    return pd.Series([pd.NA] * len(frame), index=frame.index)


def _text(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([""] * len(frame), index=frame.index)
    return frame[column].fillna("").astype(str)


def _join_unique_text(values: pd.Series) -> str:
    unique = sorted({str(value) for value in values.dropna() if str(value)})
    return "|".join(unique)


def _asset_id_from_tushare_symbol(symbol: object) -> str | None:
    parts = str(symbol).split(".")
    if len(parts) != 2:
        return None
    code, suffix = parts
    exchange_by_suffix = {"SZ": "XSHE", "SH": "XSHG", "BJ": "XBEI"}
    exchange = exchange_by_suffix.get(suffix.upper())
    if exchange is None:
        return None
    return f"CN_{exchange}_{code}"


def _date_to_tushare(value: object) -> str:
    return pd.Timestamp(value).strftime("%Y%m%d")


def _date_iso(value: object) -> str:
    return pd.Timestamp(value).date().isoformat()


def _nullable_date_min(values: pd.Series) -> str | None:
    clean = pd.to_datetime(values, errors="coerce").dropna()
    if clean.empty:
        return None
    return clean.min().date().isoformat()


def _nullable_date_max(values: pd.Series) -> str | None:
    clean = pd.to_datetime(values, errors="coerce").dropna()
    if clean.empty:
        return None
    return clean.max().date().isoformat()


def _emit_progress(progress_callback: ProgressCallback | None, **event: object) -> None:
    if progress_callback is None:
        return
    progress_callback({"timestamp": pd.Timestamp.now(tz="UTC").isoformat(), **event})


def _sanitize(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    return value
