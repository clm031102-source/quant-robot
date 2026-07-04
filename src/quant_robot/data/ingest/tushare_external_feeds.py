from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Protocol

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore


class TushareExternalFeedAdapter(Protocol):
    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        ...

    def fetch_margin_detail_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        ...

    def fetch_hk_hold_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        ...

    def fetch_moneyflow_hsgt_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        ...

    def fetch_index_daily(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        ...

    def fetch_index_dailybasic(self, ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        ...

    def fetch_index_weight(self, index_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        ...

    def fetch_shibor_by_date(self, date: str) -> pd.DataFrame:
        ...

    def fetch_shibor_lpr(self) -> pd.DataFrame:
        ...


MARGIN_DETAIL_VALUE_COLUMNS = ["rzye", "rqye", "rzmre", "rqyl", "rzche", "rqchl", "rqmcl", "rzrqye"]
HK_HOLD_VALUE_COLUMNS = ["hold_vol", "hold_ratio"]
HSGT_FLOW_VALUE_COLUMNS = ["hgt", "sgt", "north_money", "south_money"]
INDEX_STATE_VALUE_COLUMNS = ["close", "pct_chg", "amount", "turnover_rate", "turnover_rate_f", "pe", "pe_ttm", "pb"]
MACRO_RATE_VALUE_COLUMNS = ["shibor_on", "shibor_1w", "shibor_1m", "shibor_3m", "shibor_1y", "lpr_1y", "lpr_5y"]
LPR_MIN_PLAUSIBLE_RATE = 0.0
LPR_MAX_PLAUSIBLE_RATE = 20.0
ProgressCallback = Callable[[dict[str, object]], None]


def run_tushare_external_feed_ingest(
    adapter: TushareExternalFeedAdapter,
    start_date: str,
    end_date: str,
    output_dir: str | Path,
    *,
    execute_write_processed: bool = False,
    market: str = "CN",
    index_symbol: str = "000001.SH",
    lpr_cache_path: str | Path | None = None,
    progress_callback: ProgressCallback | None = None,
    empty_calendar_retries: int = 2,
) -> dict[str, object]:
    market = market.upper()
    if market != "CN":
        raise ValueError(f"Unsupported Tushare external feed market: {market}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    store = DatasetStore(output_path)
    calendar_dates = _calendar_dates(
        adapter,
        start_date,
        end_date,
        empty_calendar_retries=empty_calendar_retries,
        progress_callback=progress_callback,
    )
    trade_dates = _trade_dates_in_window(calendar_dates, start_date, end_date)
    next_trade_date = _next_trade_date_map(calendar_dates)
    trade_date_keys = [_date_to_tushare(date) for date in trade_dates]

    feeds = {
        "external_margin_detail": _normalize_margin_detail(
            _concat(
                _fetch_per_trade_date_frames(
                    "margin_detail",
                    trade_date_keys,
                    adapter.fetch_margin_detail_by_trade_date,
                    progress_callback,
                )
            ),
            next_trade_date,
            market,
        ),
        "external_hk_hold": _normalize_hk_hold(
            _concat(
                _fetch_per_trade_date_frames(
                    "hk_hold",
                    trade_date_keys,
                    adapter.fetch_hk_hold_by_trade_date,
                    progress_callback,
                )
            ),
            next_trade_date,
            market,
        ),
        "external_hsgt_flow": _normalize_hsgt_flow(
            _concat(
                _fetch_per_trade_date_frames(
                    "moneyflow_hsgt",
                    trade_date_keys,
                    adapter.fetch_moneyflow_hsgt_by_trade_date,
                    progress_callback,
                )
            ),
            next_trade_date,
            market,
        ),
        "external_index_state": _normalize_index_state(
            _fetch_range_frame(
                "index_daily",
                lambda: adapter.fetch_index_daily(index_symbol, start_date, end_date),
                progress_callback,
                start_date=start_date,
                end_date=end_date,
            ),
            _fetch_range_frame(
                "index_dailybasic",
                lambda: adapter.fetch_index_dailybasic(index_symbol, start_date, end_date),
                progress_callback,
                start_date=start_date,
                end_date=end_date,
            ),
            next_trade_date,
            market,
        ),
    }
    macro_frame, macro_warnings = _normalize_macro_rates(
        _concat(
            _fetch_per_trade_date_frames(
                "shibor",
                trade_date_keys,
                adapter.fetch_shibor_by_date,
                progress_callback,
            )
        ),
        _load_or_fetch_lpr(
            adapter,
            output_path if lpr_cache_path is None else Path(lpr_cache_path),
            progress_callback=progress_callback,
        ),
        next_trade_date,
        market,
    )
    feeds["external_macro_rates"] = macro_frame

    feed_quality = {
        "external_margin_detail": _feed_quality(
            feeds["external_margin_detail"],
            key_columns=["symbol", "date"],
            entity_column="symbol",
            value_columns=MARGIN_DETAIL_VALUE_COLUMNS,
        ),
        "external_hk_hold": _feed_quality(
            feeds["external_hk_hold"],
            key_columns=["symbol", "date"],
            entity_column="symbol",
            value_columns=HK_HOLD_VALUE_COLUMNS,
        ),
        "external_hsgt_flow": _feed_quality(
            feeds["external_hsgt_flow"],
            key_columns=["date"],
            value_columns=HSGT_FLOW_VALUE_COLUMNS,
        ),
        "external_index_state": _feed_quality(
            feeds["external_index_state"],
            key_columns=["index_symbol", "date"],
            entity_column="index_symbol",
            value_columns=INDEX_STATE_VALUE_COLUMNS,
        ),
        "external_macro_rates": _feed_quality(
            feeds["external_macro_rates"],
            key_columns=["date"],
            value_columns=MACRO_RATE_VALUE_COLUMNS,
            warnings=macro_warnings,
        ),
    }

    if execute_write_processed:
        for dataset, frame in feeds.items():
            _write_processed_by_year(store, dataset, frame, market, _dedupe_keys_for_dataset(dataset))

    summary = _summary(feed_quality)
    report = {
        "source": "tushare",
        "market": market,
        "start_date": _date_iso(pd.to_datetime(start_date).date()),
        "end_date": _date_iso(pd.to_datetime(end_date).date()),
        "processed_writes_enabled": bool(execute_write_processed),
        "summary": summary,
        "feed_quality": feed_quality,
        "safety": "research-to-review only; no broker, account, order, or live-trading access",
    }
    (output_path / "external_feed_ingestion_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report


def _fetch_per_trade_date_frames(
    endpoint: str,
    trade_date_keys: list[str],
    fetch: Callable[[str], pd.DataFrame],
    progress_callback: ProgressCallback | None,
) -> list[pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    total = len(trade_date_keys)
    for index, trade_date in enumerate(trade_date_keys, start=1):
        _emit_progress(
            progress_callback,
            endpoint=endpoint,
            status="start",
            trade_date=trade_date,
            index=index,
            total=total,
        )
        try:
            frame = fetch(trade_date)
        except Exception as exc:
            _emit_progress(
                progress_callback,
                endpoint=endpoint,
                status="fail",
                trade_date=trade_date,
                index=index,
                total=total,
                error=type(exc).__name__,
            )
            raise
        frames.append(frame)
        _emit_progress(
            progress_callback,
            endpoint=endpoint,
            status="done",
            trade_date=trade_date,
            index=index,
            total=total,
            rows=int(len(frame)) if frame is not None else 0,
        )
    return frames


def _fetch_range_frame(
    endpoint: str,
    fetch: Callable[[], pd.DataFrame],
    progress_callback: ProgressCallback | None,
    **labels: object,
) -> pd.DataFrame:
    _emit_progress(progress_callback, endpoint=endpoint, status="start", **labels)
    try:
        frame = fetch()
    except Exception as exc:
        _emit_progress(progress_callback, endpoint=endpoint, status="fail", error=type(exc).__name__, **labels)
        raise
    _emit_progress(progress_callback, endpoint=endpoint, status="done", rows=int(len(frame)), **labels)
    return frame


def _emit_progress(progress_callback: ProgressCallback | None, **event: object) -> None:
    if progress_callback is None:
        return
    progress_callback({"timestamp": pd.Timestamp.now(tz="UTC").isoformat(), **event})


def _calendar_dates(
    adapter: TushareExternalFeedAdapter,
    start_date: str,
    end_date: str,
    *,
    empty_calendar_retries: int = 2,
    progress_callback: ProgressCallback | None = None,
) -> list[pd.Timestamp]:
    padded_end = (pd.to_datetime(end_date) + pd.Timedelta(days=14)).date().isoformat()
    max_attempts = max(1, empty_calendar_retries + 1)
    for attempt in range(1, max_attempts + 1):
        calendar = adapter.fetch_trade_calendar(start_date, padded_end)
        if "date" not in calendar.columns:
            raise ValueError("Tushare trade calendar response is missing date")
        dates = pd.to_datetime(calendar["date"]).dropna().sort_values().drop_duplicates()
        if not dates.empty:
            if attempt > 1:
                _emit_progress(
                    progress_callback,
                    endpoint="trade_calendar",
                    status="empty_retry_recovered",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    rows=int(len(dates)),
                )
            return [pd.Timestamp(value).normalize() for value in dates]
        if attempt < max_attempts:
            _emit_progress(
                progress_callback,
                endpoint="trade_calendar",
                status="empty_retry",
                attempt=attempt,
                max_attempts=max_attempts,
            )
    raise ValueError("Tushare trade calendar response has no open trade dates")


def _trade_dates_in_window(calendar_dates: list[pd.Timestamp], start_date: str, end_date: str) -> list[pd.Timestamp]:
    start = pd.Timestamp(start_date).normalize()
    end = pd.Timestamp(end_date).normalize()
    return [date for date in calendar_dates if start <= date <= end]


def _next_trade_date_map(calendar_dates: list[pd.Timestamp]) -> dict[object, object]:
    result: dict[object, object] = {}
    for index, date in enumerate(calendar_dates[:-1]):
        result[date.date()] = calendar_dates[index + 1].date()
    return result


def _normalize_margin_detail(raw: pd.DataFrame, next_trade_date: dict[object, object], market: str) -> pd.DataFrame:
    columns = ["date", "available_date", "asset_id", "symbol", "market", "source", "ingested_at"] + MARGIN_DETAIL_VALUE_COLUMNS
    if raw.empty:
        return pd.DataFrame(columns=columns)
    source = raw.copy()
    mapped = pd.DataFrame(
        {
            "symbol": _symbol(source),
            "date": _date(source),
        }
    )
    for column in MARGIN_DETAIL_VALUE_COLUMNS:
        mapped[column] = _numeric(source, column)
    return _with_common_columns(mapped, columns, next_trade_date, market, "tushare_margin_detail")


def _normalize_hk_hold(raw: pd.DataFrame, next_trade_date: dict[object, object], market: str) -> pd.DataFrame:
    columns = [
        "date",
        "available_date",
        "asset_id",
        "symbol",
        "market",
        "source",
        "ingested_at",
        "exchange",
        *HK_HOLD_VALUE_COLUMNS,
    ]
    if raw.empty:
        return pd.DataFrame(columns=columns)
    source = raw.copy()
    mapped = pd.DataFrame(
        {
            "symbol": _symbol(source),
            "date": _date(source),
            "exchange": _text(source, "exchange"),
            "hold_vol": _numeric(source, "vol", fallback="hold_vol"),
            "hold_ratio": _numeric(source, "ratio", fallback="hold_ratio"),
        }
    )
    mapped, dropped_non_cn_symbol_count = _drop_non_cn_stock_symbols(mapped)
    output = _with_common_columns(mapped, columns, next_trade_date, market, "tushare_hk_hold")
    output.attrs["dropped_non_cn_symbol_count"] = dropped_non_cn_symbol_count
    return output


def _normalize_hsgt_flow(raw: pd.DataFrame, next_trade_date: dict[object, object], market: str) -> pd.DataFrame:
    columns = ["date", "available_date", "market", "source", "ingested_at"] + HSGT_FLOW_VALUE_COLUMNS
    if raw.empty:
        return pd.DataFrame(columns=columns)
    source = raw.copy()
    mapped = pd.DataFrame({"date": _date(source)})
    for column in HSGT_FLOW_VALUE_COLUMNS:
        mapped[column] = _numeric(source, column)
    return _with_common_columns(mapped, columns, next_trade_date, market, "tushare_moneyflow_hsgt")


def _normalize_index_state(
    index_daily: pd.DataFrame,
    index_dailybasic: pd.DataFrame,
    next_trade_date: dict[object, object],
    market: str,
) -> pd.DataFrame:
    columns = ["date", "available_date", "index_symbol", "market", "source", "ingested_at"] + INDEX_STATE_VALUE_COLUMNS
    if index_daily.empty and index_dailybasic.empty:
        return pd.DataFrame(columns=columns)
    daily = _normalize_index_daily_part(index_daily)
    basic = _normalize_index_dailybasic_part(index_dailybasic)
    if daily.empty:
        merged = basic
    elif basic.empty:
        merged = daily
    else:
        merged = daily.merge(basic, on=["index_symbol", "date"], how="outer")
    return _with_common_columns(merged, columns, next_trade_date, market, "tushare_index_state")


def _normalize_index_daily_part(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=["index_symbol", "date", "close", "pct_chg", "amount"])
    source = raw.copy()
    return pd.DataFrame(
        {
            "index_symbol": _symbol(source),
            "date": _date(source),
            "close": _numeric(source, "close"),
            "pct_chg": _numeric(source, "pct_chg"),
            "amount": _numeric(source, "amount"),
        }
    )


def _normalize_index_dailybasic_part(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=["index_symbol", "date", "turnover_rate", "turnover_rate_f", "pe", "pe_ttm", "pb"])
    source = raw.copy()
    mapped = pd.DataFrame({"index_symbol": _symbol(source), "date": _date(source)})
    for column in ["turnover_rate", "turnover_rate_f", "pe", "pe_ttm", "pb"]:
        mapped[column] = _numeric(source, column)
    return mapped


def _normalize_macro_rates(
    shibor: pd.DataFrame,
    lpr: pd.DataFrame,
    next_trade_date: dict[object, object],
    market: str,
) -> tuple[pd.DataFrame, list[str]]:
    columns = ["date", "available_date", "market", "source", "ingested_at"] + MACRO_RATE_VALUE_COLUMNS
    warnings: list[str] = []
    if shibor.empty:
        return pd.DataFrame(columns=columns), ["shibor_missing"]
    shibor_frame = _normalize_shibor(shibor)
    if lpr.empty:
        warnings.append("lpr_missing_or_rate_limited")
        shibor_frame["lpr_1y"] = pd.NA
        shibor_frame["lpr_5y"] = pd.NA
        return _with_common_columns(shibor_frame, columns, next_trade_date, market, "tushare_macro_rates"), warnings
    lpr_frame = lpr.copy()
    lpr_frame["date_ord"] = pd.to_datetime(lpr_frame["date"]).map(lambda value: value.date().toordinal())
    shibor_frame["date_ord"] = pd.to_datetime(shibor_frame["date"]).map(lambda value: value.date().toordinal())
    merged = pd.merge_asof(
        shibor_frame.sort_values("date_ord"),
        lpr_frame[["date_ord", "lpr_1y", "lpr_5y"]].sort_values("date_ord"),
        on="date_ord",
        direction="backward",
    )
    merged = merged.drop(columns=["date_ord"])
    return _with_common_columns(merged, columns, next_trade_date, market, "tushare_macro_rates"), warnings


def _normalize_shibor(raw: pd.DataFrame) -> pd.DataFrame:
    source = raw.copy()
    return pd.DataFrame(
        {
            "date": _date(source),
            "shibor_on": _numeric(source, "on", fallback="shibor_on"),
            "shibor_1w": _numeric(source, "1w", fallback="shibor_1w"),
            "shibor_1m": _numeric(source, "1m", fallback="shibor_1m"),
            "shibor_3m": _numeric(source, "3m", fallback="shibor_3m"),
            "shibor_1y": _numeric(source, "1y", fallback="shibor_1y"),
        }
    )


def _load_or_fetch_lpr(
    adapter: TushareExternalFeedAdapter,
    output_or_cache_path: Path,
    *,
    progress_callback: ProgressCallback | None = None,
) -> pd.DataFrame:
    cache_path = output_or_cache_path if output_or_cache_path.suffix == ".json" else output_or_cache_path / "external_lpr_cache.json"
    if cache_path.exists():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        cached_frame = pd.DataFrame(cached.get("rows", []))
        if _has_non_missing_lpr_values(cached_frame):
            _emit_progress(progress_callback, endpoint="shibor_lpr", status="cache_hit")
            return cached_frame
        _emit_progress(
            progress_callback,
            endpoint="shibor_lpr",
            status="cache_refresh",
            warning="lpr_cache_empty_or_missing_values",
        )
    _emit_progress(progress_callback, endpoint="shibor_lpr", status="start")
    try:
        normalized = _normalize_lpr(adapter.fetch_shibor_lpr())
    except Exception:
        _emit_progress(progress_callback, endpoint="shibor_lpr", status="warn", warning="lpr_missing_or_rate_limited")
        return pd.DataFrame(columns=["date", "lpr_1y", "lpr_5y"])
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_rows = normalized.copy()
    if "date" in cache_rows.columns:
        cache_rows["date"] = pd.to_datetime(cache_rows["date"]).dt.date.astype(str)
    cache_path.write_text(
        json.dumps({"rows": cache_rows.to_dict(orient="records")}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _emit_progress(progress_callback, endpoint="shibor_lpr", status="done", rows=int(len(normalized)))
    return normalized


def _has_non_missing_lpr_values(frame: pd.DataFrame) -> bool:
    required = {"date", "lpr_1y", "lpr_5y"}
    if frame.empty or not required.issubset(frame.columns):
        return False
    lpr_1y = pd.to_numeric(frame["lpr_1y"], errors="coerce")
    lpr_5y = pd.to_numeric(frame["lpr_5y"], errors="coerce")
    dates = pd.to_datetime(frame["date"], errors="coerce")
    plausible = (
        dates.notna()
        & lpr_1y.between(LPR_MIN_PLAUSIBLE_RATE, LPR_MAX_PLAUSIBLE_RATE, inclusive="neither")
        & lpr_5y.between(LPR_MIN_PLAUSIBLE_RATE, LPR_MAX_PLAUSIBLE_RATE, inclusive="neither")
    )
    return bool(plausible.any())


def _normalize_lpr(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=["date", "lpr_1y", "lpr_5y"])
    source = raw.copy()
    return pd.DataFrame(
        {
            "date": _date(source),
            "lpr_1y": _numeric(source, "1y", fallback="lpr_1y"),
            "lpr_5y": _numeric(source, "5y", fallback="lpr_5y"),
        }
    ).sort_values("date").reset_index(drop=True)


def _with_common_columns(
    frame: pd.DataFrame,
    columns: list[str],
    next_trade_date: dict[object, object],
    market: str,
    source_name: str,
) -> pd.DataFrame:
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"]).dt.date
    output["available_date"] = output["date"].map(next_trade_date)
    output["market"] = market
    output["source"] = source_name
    output["ingested_at"] = pd.Timestamp.now(tz="UTC")
    if "symbol" in output.columns and "asset_id" in columns:
        output["asset_id"] = output["symbol"].map(_asset_id_from_tushare_symbol)
    for column in columns:
        if column not in output.columns:
            output[column] = pd.NA
    return output[columns].sort_values([column for column in ["symbol", "index_symbol", "date"] if column in columns]).reset_index(drop=True)


def _feed_quality(
    frame: pd.DataFrame,
    *,
    key_columns: list[str],
    value_columns: list[str],
    entity_column: str | None = None,
    warnings: list[str] | None = None,
) -> dict[str, object]:
    warnings = list(warnings or [])
    if frame.empty:
        return {
            "status": "warn",
            "warnings": warnings + ["empty_feed"],
            "rows": 0,
            "date_min": None,
            "date_max": None,
            "available_date_min": None,
            "available_date_max": None,
            "entities": 0,
            "duplicate_key_count": 0,
            "lag_violation_count": 0,
            "missing_available_date_count": 0,
            "dropped_non_cn_symbol_count": int(frame.attrs.get("dropped_non_cn_symbol_count", 0)),
            "missing_by_column": {},
            "coverage_by_year": {},
        }
    dates = pd.to_datetime(frame["date"])
    available = pd.to_datetime(frame["available_date"])
    duplicate_count = int(frame.duplicated(key_columns).sum())
    missing_available_date_count = int(available.isna().sum())
    lag_violation_count = int((available.notna() & (available <= dates)).sum())
    missing_by_column = {
        column: int(frame[column].isna().sum())
        for column in value_columns
        if column in frame.columns and int(frame[column].isna().sum()) > 0
    }
    status = "pass"
    if duplicate_count or lag_violation_count or missing_available_date_count:
        status = "fail"
    elif warnings:
        status = "warn"
    return {
        "status": status,
        "warnings": warnings,
        "rows": int(len(frame)),
        "date_min": dates.min().date().isoformat(),
        "date_max": dates.max().date().isoformat(),
        "available_date_min": _nullable_date_min(available),
        "available_date_max": _nullable_date_max(available),
        "entities": int(frame[entity_column].nunique()) if entity_column else None,
        "duplicate_key_count": duplicate_count,
        "lag_violation_count": lag_violation_count,
        "missing_available_date_count": missing_available_date_count,
        "dropped_non_cn_symbol_count": int(frame.attrs.get("dropped_non_cn_symbol_count", 0)),
        "missing_by_column": missing_by_column,
        "coverage_by_year": {str(year): int(count) for year, count in dates.dt.year.value_counts().sort_index().items()},
    }


def _summary(feed_quality: dict[str, dict[str, object]]) -> dict[str, int]:
    statuses = [str(value["status"]) for value in feed_quality.values()]
    return {
        "feed_count": len(feed_quality),
        "pass_count": statuses.count("pass"),
        "warn_count": statuses.count("warn"),
        "fail_count": statuses.count("fail"),
    }


def _nullable_date_min(values: pd.Series) -> str | None:
    clean = values.dropna()
    if clean.empty:
        return None
    return clean.min().date().isoformat()


def _nullable_date_max(values: pd.Series) -> str | None:
    clean = values.dropna()
    if clean.empty:
        return None
    return clean.max().date().isoformat()


def _write_processed_by_year(
    store: DatasetStore,
    dataset: str,
    frame: pd.DataFrame,
    market: str,
    dedupe_keys: list[str],
) -> None:
    if frame.empty:
        return
    dates = pd.to_datetime(frame["date"])
    for year, group in frame.groupby(dates.dt.year):
        partitions = {"frequency": "1d", "market": market, "year": str(year)}
        merged = group
        if store.exists(f"processed/{dataset}", partitions):
            existing = store.read_frame(f"processed/{dataset}", partitions)
            merged = pd.concat([existing, group], ignore_index=True)
            merged = merged.drop_duplicates(dedupe_keys, keep="last")
        store.write_frame(merged, f"processed/{dataset}", partitions)


def _dedupe_keys_for_dataset(dataset: str) -> list[str]:
    if dataset in {"external_margin_detail", "external_hk_hold"}:
        return ["symbol", "date"]
    if dataset == "external_index_state":
        return ["index_symbol", "date"]
    return ["date"]


def _concat(frames: list[pd.DataFrame]) -> pd.DataFrame:
    usable = [frame for frame in frames if frame is not None and not frame.empty]
    if not usable:
        return pd.DataFrame()
    return pd.concat(usable, ignore_index=True)


def _symbol(frame: pd.DataFrame) -> pd.Series:
    if "ts_code" in frame.columns:
        return frame["ts_code"].astype(str)
    if "symbol" in frame.columns:
        return frame["symbol"].astype(str)
    if "index_symbol" in frame.columns:
        return frame["index_symbol"].astype(str)
    raise ValueError("External feed frame is missing symbol/ts_code")


def _date(frame: pd.DataFrame) -> pd.Series:
    for column in ["trade_date", "date"]:
        if column in frame.columns:
            return _parse_dates(frame[column])
    raise ValueError("External feed frame is missing date/trade_date")


def _parse_dates(values: pd.Series) -> pd.Series:
    text = values.astype(str)
    digit_mask = text.str.fullmatch(r"\d{8}")
    parsed = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    if digit_mask.any():
        parsed.loc[digit_mask] = pd.to_datetime(text.loc[digit_mask], format="%Y%m%d")
    if (~digit_mask).any():
        parsed.loc[~digit_mask] = pd.to_datetime(values.loc[~digit_mask])
    return parsed.dt.date


def _numeric(frame: pd.DataFrame, column: str, fallback: str | None = None) -> pd.Series:
    actual = column if column in frame.columns else fallback
    if actual and actual in frame.columns:
        return pd.to_numeric(frame[actual], errors="coerce")
    return pd.Series([pd.NA] * len(frame), index=frame.index)


def _text(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([""] * len(frame), index=frame.index)
    return frame[column].fillna("").astype(str)


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


def _drop_non_cn_stock_symbols(frame: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    if frame.empty or "symbol" not in frame.columns:
        return frame, 0
    symbol_text = frame["symbol"].astype(str).str.upper()
    mask = symbol_text.str.endswith((".SZ", ".SH", ".BJ"))
    dropped = int((~mask).sum())
    return frame.loc[mask].reset_index(drop=True), dropped


def _date_to_tushare(value: pd.Timestamp) -> str:
    return pd.Timestamp(value).strftime("%Y%m%d")


def _date_iso(value: object) -> str:
    return pd.Timestamp(value).date().isoformat()
