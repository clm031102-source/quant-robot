from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, Sequence

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore


class TushareTradeabilityFeedAdapter(Protocol):
    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        ...

    def fetch_stk_limit_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        ...

    def fetch_suspend_d_by_date(self, trade_date: str) -> pd.DataFrame:
        ...

    def fetch_namechange(self, start_date: str, end_date: str) -> pd.DataFrame:
        ...

    def fetch_stock_basic(self, list_status: str = "L") -> pd.DataFrame:
        ...


LIMIT_VALUE_COLUMNS = ["up_limit", "down_limit"]
SUSPENSION_VALUE_COLUMNS = ["suspend_timing", "suspend_type", "resume_date", "suspend_reason", "reason_type"]
NAMECHANGE_VALUE_COLUMNS = ["name", "start_date", "end_date", "ann_date", "change_reason", "is_st_name"]
STOCK_STATUS_VALUES = ["L", "P", "D"]


def run_tushare_tradeability_feed_ingest(
    adapter: TushareTradeabilityFeedAdapter,
    start_date: str,
    end_date: str,
    output_dir: str | Path,
    *,
    processed_output_dir: str | Path | None = None,
    execute_write_processed: bool = False,
    market: str = "CN",
    stock_statuses: Sequence[str] = STOCK_STATUS_VALUES,
    snapshot: str | None = None,
) -> dict[str, object]:
    market = market.upper()
    if market != "CN":
        raise ValueError(f"Unsupported Tushare tradeability feed market: {market}")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    processed_path = Path(processed_output_dir) if processed_output_dir else output_path
    if execute_write_processed:
        processed_path.mkdir(parents=True, exist_ok=True)
    store = DatasetStore(processed_path)

    calendar_dates = _calendar_dates(adapter, start_date, end_date)
    trade_dates = _trade_dates_in_window(calendar_dates, start_date, end_date)
    next_trade_date = _next_trade_date_map(calendar_dates)
    trade_date_keys = [_date_to_tushare(value) for value in trade_dates]

    limit = _normalize_stk_limit(
        _concat([adapter.fetch_stk_limit_by_trade_date(trade_date) for trade_date in trade_date_keys]),
        next_trade_date,
        market,
    )
    suspension = _normalize_suspension(
        _concat([adapter.fetch_suspend_d_by_date(trade_date) for trade_date in trade_date_keys]),
        next_trade_date,
        market,
    )
    namechange = _normalize_namechange(
        adapter.fetch_namechange(start_date, end_date),
        calendar_dates,
        market,
    )
    stock_basic_by_status = _fetch_stock_basic_statuses(adapter, stock_statuses)
    stock_basic_all = _concat(list(stock_basic_by_status.values()))

    feed_quality = {
        "tradeability_stk_limit": _dated_feed_quality(
            limit,
            key_columns=["symbol", "date"],
            value_columns=LIMIT_VALUE_COLUMNS,
        ),
        "tradeability_suspension": _dated_feed_quality(
            suspension,
            key_columns=["symbol", "date"],
            value_columns=SUSPENSION_VALUE_COLUMNS,
        ),
        "tradeability_namechange": _dated_feed_quality(
            namechange,
            key_columns=["symbol", "start_date", "name"],
            value_columns=NAMECHANGE_VALUE_COLUMNS,
            date_column="ann_date",
            extra={"st_name_rows": int(namechange["is_st_name"].sum()) if "is_st_name" in namechange.columns else 0},
        ),
        "stock_basic_status": _stock_basic_quality(stock_basic_all, stock_statuses),
    }

    if execute_write_processed:
        _write_processed_by_year(store, "processed/tradeability_stk_limit", limit, market, ["symbol", "date"])
        _write_processed_by_year(store, "processed/tradeability_suspension", suspension, market, ["symbol", "date"])
        _write_processed_by_year(store, "processed/tradeability_namechange", namechange, market, ["symbol", "start_date", "name"], date_column="start_date")
        _write_stock_basic_statuses(store, stock_basic_by_status, snapshot=snapshot or pd.Timestamp.today().date().isoformat())
        _write_tradeability_coverage_manifest(
            store,
            start_date=start_date,
            end_date=end_date,
            market=market,
            snapshot=snapshot or pd.Timestamp.today().date().isoformat(),
        )

    report = {
        "source": "tushare",
        "market": market,
        "start_date": _date_iso(start_date),
        "end_date": _date_iso(end_date),
        "processed_output_dir": str(processed_path),
        "processed_writes_enabled": bool(execute_write_processed),
        "coverage_manifest_written": bool(execute_write_processed),
        "summary": _summary(feed_quality),
        "feed_quality": feed_quality,
        "safety": "research-to-review only; no broker, account, order, or live-trading access",
    }
    (output_path / "tradeability_feed_ingestion_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report


def _normalize_stk_limit(raw: pd.DataFrame, next_trade_date: dict[object, object], market: str) -> pd.DataFrame:
    columns = ["date", "available_date", "asset_id", "symbol", "market", "source", "ingested_at"] + LIMIT_VALUE_COLUMNS
    if raw.empty:
        return pd.DataFrame(columns=columns)
    source = raw.copy()
    mapped = pd.DataFrame(
        {
            "symbol": _symbol(source),
            "date": _date(source, ["trade_date", "date"]),
            "up_limit": _numeric(source, "up_limit"),
            "down_limit": _numeric(source, "down_limit"),
        }
    )
    return _with_asset_date_common(mapped, columns, next_trade_date, market, "tushare_stk_limit")


def _normalize_suspension(raw: pd.DataFrame, next_trade_date: dict[object, object], market: str) -> pd.DataFrame:
    columns = ["date", "available_date", "asset_id", "symbol", "market", "source", "ingested_at"] + SUSPENSION_VALUE_COLUMNS
    if raw.empty:
        return pd.DataFrame(columns=columns)
    source = raw.copy()
    mapped = pd.DataFrame(
        {
            "symbol": _symbol(source),
            "date": _date(source, ["trade_date", "suspend_date", "date"]),
            "suspend_timing": _text(source, "suspend_timing"),
            "suspend_type": _text(source, "suspend_type"),
            "resume_date": _optional_date(source, "resume_date"),
            "suspend_reason": _text(source, "suspend_reason"),
            "reason_type": _text(source, "reason_type"),
        }
    )
    output = _with_asset_date_common(mapped, columns, next_trade_date, market, "tushare_suspend_d")
    return output.drop_duplicates(["symbol", "date"], keep="last").reset_index(drop=True)


def _normalize_namechange(raw: pd.DataFrame, calendar_dates: list[pd.Timestamp], market: str) -> pd.DataFrame:
    columns = [
        "date",
        "available_date",
        "asset_id",
        "symbol",
        "market",
        "source",
        "ingested_at",
        *NAMECHANGE_VALUE_COLUMNS,
    ]
    if raw.empty:
        return pd.DataFrame(columns=columns)
    source = raw.copy()
    start = _date(source, ["start_date", "date"])
    ann = _date(source, ["ann_date", "start_date", "date"])
    name = _text(source, "name")
    mapped = pd.DataFrame(
        {
            "symbol": _symbol(source),
            "date": start,
            "name": name,
            "start_date": start,
            "end_date": _optional_date(source, "end_date"),
            "ann_date": ann,
            "change_reason": _text(source, "change_reason"),
            "is_st_name": _is_st_name(name),
        }
    )
    mapped["available_date"] = mapped["ann_date"].map(lambda value: _next_trade_after(calendar_dates, value))
    mapped["market"] = market
    mapped["source"] = "tushare_namechange"
    mapped["ingested_at"] = pd.Timestamp.now(tz="UTC")
    mapped["asset_id"] = mapped["symbol"].map(_asset_id_from_tushare_symbol)
    output = mapped[columns].sort_values(["symbol", "start_date", "name"]).reset_index(drop=True)
    return output.drop_duplicates(["symbol", "start_date", "name"], keep="last").reset_index(drop=True)


def _fetch_stock_basic_statuses(
    adapter: TushareTradeabilityFeedAdapter,
    stock_statuses: Sequence[str],
) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for status in stock_statuses:
        list_status = str(status).upper()
        frame = adapter.fetch_stock_basic(list_status).copy()
        if "list_status" not in frame.columns:
            frame["list_status"] = list_status
        frames[list_status] = frame
    return frames


def _with_asset_date_common(
    frame: pd.DataFrame,
    columns: list[str],
    next_trade_date: dict[object, object],
    market: str,
    source_name: str,
) -> pd.DataFrame:
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"]).dt.date
    output["available_date"] = output["date"].map(next_trade_date)
    output["asset_id"] = output["symbol"].map(_asset_id_from_tushare_symbol)
    output["market"] = market
    output["source"] = source_name
    output["ingested_at"] = pd.Timestamp.now(tz="UTC")
    for column in columns:
        if column not in output.columns:
            output[column] = pd.NA
    return output[columns].sort_values(["symbol", "date"]).reset_index(drop=True)


def _dated_feed_quality(
    frame: pd.DataFrame,
    *,
    key_columns: list[str],
    value_columns: list[str],
    date_column: str = "date",
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    if frame.empty:
        return {
            "status": "warn",
            "warnings": ["empty_feed"],
            "rows": 0,
            "date_min": None,
            "date_max": None,
            "available_date_min": None,
            "available_date_max": None,
            "entities": 0,
            "duplicate_key_count": 0,
            "lag_violation_count": 0,
            "missing_available_date_count": 0,
            "missing_by_column": {},
            **(extra or {}),
        }
    dates = pd.to_datetime(frame[date_column])
    available = pd.to_datetime(frame["available_date"])
    duplicate_count = int(frame.duplicated(key_columns).sum())
    missing_available_date_count = int(available.isna().sum())
    lag_violation_count = int((available.notna() & (available <= dates)).sum())
    missing_by_column = {
        column: int(frame[column].isna().sum())
        for column in value_columns
        if column in frame.columns and int(frame[column].isna().sum()) > 0
    }
    status = "fail" if duplicate_count or missing_available_date_count or lag_violation_count else "pass"
    return {
        "status": status,
        "warnings": [],
        "rows": int(len(frame)),
        "date_min": dates.min().date().isoformat(),
        "date_max": dates.max().date().isoformat(),
        "available_date_min": _nullable_date_min(available),
        "available_date_max": _nullable_date_max(available),
        "entities": int(frame["symbol"].nunique()) if "symbol" in frame.columns else 0,
        "duplicate_key_count": duplicate_count,
        "lag_violation_count": lag_violation_count,
        "missing_available_date_count": missing_available_date_count,
        "missing_by_column": missing_by_column,
        **(extra or {}),
    }


def _stock_basic_quality(frame: pd.DataFrame, stock_statuses: Sequence[str]) -> dict[str, object]:
    expected = {str(status).upper() for status in stock_statuses}
    statuses = set(frame["list_status"].astype(str).str.upper()) if "list_status" in frame.columns else set()
    required = expected & {"L", "D"}
    optional = expected - required
    missing_required = sorted(required - statuses)
    missing_optional = sorted(optional - statuses)
    return {
        "status": "fail" if missing_required else "pass",
        "warnings": [f"missing_optional_status:{status}" for status in missing_optional],
        "rows": int(len(frame)),
        "entities": int(frame["symbol"].nunique()) if "symbol" in frame.columns else 0,
        "status_values": sorted(statuses),
        "missing_status_values": missing_required,
        "missing_optional_status_values": missing_optional,
        "delist_date_rows": int(frame["delist_date"].notna().sum()) if "delist_date" in frame.columns else 0,
    }


def _summary(feed_quality: dict[str, dict[str, object]]) -> dict[str, int]:
    statuses = [str(value["status"]) for value in feed_quality.values()]
    return {
        "feed_count": len(feed_quality),
        "pass_count": statuses.count("pass"),
        "warn_count": statuses.count("warn"),
        "fail_count": statuses.count("fail"),
    }


def _write_processed_by_year(
    store: DatasetStore,
    dataset: str,
    frame: pd.DataFrame,
    market: str,
    dedupe_keys: list[str],
    *,
    date_column: str = "date",
) -> None:
    if frame.empty:
        return
    dates = pd.to_datetime(frame[date_column])
    for year, group in frame.groupby(dates.dt.year):
        partitions = {"frequency": "1d", "market": market, "year": str(year)}
        merged = group
        if store.exists(dataset, partitions):
            existing = store.read_frame(dataset, partitions)
            merged = pd.concat([existing, group], ignore_index=True)
            merged = merged.drop_duplicates(dedupe_keys, keep="last")
        store.write_frame(merged, dataset, partitions)


def _write_stock_basic_statuses(store: DatasetStore, frames: dict[str, pd.DataFrame], *, snapshot: str) -> None:
    for status, frame in frames.items():
        store.write_frame(frame, "metadata/tushare_stock_basic", {"list_status": status, "snapshot": snapshot})


def _write_tradeability_coverage_manifest(
    store: DatasetStore,
    *,
    start_date: str,
    end_date: str,
    market: str,
    snapshot: str,
) -> None:
    shard_id = f"{pd.Timestamp(start_date):%Y%m%d}_{pd.Timestamp(end_date):%Y%m%d}"
    frame = pd.DataFrame(
        {
            "feed": [
                "tradeability_stk_limit",
                "tradeability_suspension",
                "tradeability_namechange",
                "stock_basic_status_snapshot",
            ],
            "start_date": [_date_iso(start_date)] * 4,
            "end_date": [_date_iso(end_date)] * 4,
            "market": [market] * 4,
            "source": ["tushare"] * 4,
            "snapshot": [snapshot] * 4,
            "shard_id": [shard_id] * 4,
            "ingested_at": [pd.Timestamp.now(tz="UTC")] * 4,
        }
    )
    store.write_frame(frame, "metadata/tushare_tradeability_feed_coverage", {"market": market, "shard": shard_id})


def _calendar_dates(adapter: TushareTradeabilityFeedAdapter, start_date: str, end_date: str) -> list[pd.Timestamp]:
    padded_end = (pd.to_datetime(end_date) + pd.Timedelta(days=14)).date().isoformat()
    calendar = adapter.fetch_trade_calendar(start_date, padded_end)
    if "date" not in calendar.columns:
        raise ValueError("Tushare trade calendar response is missing date")
    dates = pd.to_datetime(calendar["date"]).dropna().sort_values().drop_duplicates()
    if dates.empty:
        raise ValueError("Tushare trade calendar response has no open trade dates")
    return [pd.Timestamp(value).normalize() for value in dates]


def _trade_dates_in_window(calendar_dates: list[pd.Timestamp], start_date: str, end_date: str) -> list[pd.Timestamp]:
    start = pd.Timestamp(start_date).normalize()
    end = pd.Timestamp(end_date).normalize()
    return [value for value in calendar_dates if start <= value <= end]


def _next_trade_date_map(calendar_dates: list[pd.Timestamp]) -> dict[object, object]:
    return {
        value.date(): calendar_dates[index + 1].date()
        for index, value in enumerate(calendar_dates[:-1])
    }


def _next_trade_after(calendar_dates: list[pd.Timestamp], value: object) -> object:
    current = pd.Timestamp(value).normalize()
    for trade_date in calendar_dates:
        if trade_date > current:
            return trade_date.date()
    return pd.NaT


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
    raise ValueError("Tradeability feed frame is missing symbol/ts_code")


def _date(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    for column in columns:
        if column in frame.columns:
            return _parse_dates(frame[column])
    raise ValueError(f"Tradeability feed frame is missing date columns: {', '.join(columns)}")


def _parse_dates(values: pd.Series) -> pd.Series:
    text = values.astype(str)
    digit_mask = text.str.fullmatch(r"\d{8}")
    parsed = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    if digit_mask.any():
        parsed.loc[digit_mask] = pd.to_datetime(text.loc[digit_mask], format="%Y%m%d")
    if (~digit_mask).any():
        parsed.loc[~digit_mask] = pd.to_datetime(values.loc[~digit_mask])
    return parsed.dt.date


def _optional_date(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([pd.NaT] * len(frame), index=frame.index)
    return pd.to_datetime(frame[column], errors="coerce").dt.date


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column in frame.columns:
        return pd.to_numeric(frame[column], errors="coerce")
    return pd.Series([pd.NA] * len(frame), index=frame.index)


def _text(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([""] * len(frame), index=frame.index)
    return frame[column].fillna("").astype(str)


def _is_st_name(name: pd.Series) -> pd.Series:
    text = name.fillna("").astype(str).str.upper()
    return text.str.contains("ST", regex=False)


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


def _date_to_tushare(value: pd.Timestamp) -> str:
    return pd.Timestamp(value).strftime("%Y%m%d")


def _date_iso(value: object) -> str:
    return pd.Timestamp(value).date().isoformat()
