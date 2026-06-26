from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from time import sleep
from typing import Any, Callable, Protocol

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore


STAGE = "dragon_tiger_full_coverage_audit"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"
CALENDAR_MAX_ATTEMPTS = 3
CALENDAR_RETRY_SLEEP_SECONDS = 1.0
TOP_LIST_VALUE_COLUMNS = [
    "close",
    "pct_change",
    "turnover_rate",
    "amount",
    "l_sell",
    "l_buy",
    "l_amount",
    "net_amount",
    "net_rate",
    "amount_rate",
    "float_values",
]
TOP_INST_VALUE_COLUMNS = ["buy", "buy_rate", "sell", "sell_rate", "net_buy"]
TOP_LIST_REQUIRED_COLUMNS = ["trade_date", "ts_code"]
TOP_INST_REQUIRED_COLUMNS = ["trade_date", "ts_code"]


class DragonTigerAdapter(Protocol):
    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        ...

    def fetch_top_list_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        ...

    def fetch_top_inst_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        ...


ProgressCallback = Callable[[dict[str, object]], None]


def run_dragon_tiger_coverage_audit(
    adapter: DragonTigerAdapter,
    start_date: str,
    end_date: str,
    output_dir: str | Path,
    *,
    market: str = "CN",
    processed_root: str | Path | None = None,
    execute_write_processed: bool = False,
    min_non_empty_ratio: float = 0.8,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    market = market.upper()
    if market != "CN":
        raise ValueError(f"Unsupported Dragon-Tiger market: {market}")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    processed_path = Path(processed_root) if processed_root else output_path
    calendar_dates = _calendar_dates(adapter, start_date, end_date)
    trade_dates = _trade_dates_in_window(calendar_dates, start_date, end_date)
    next_trade_date = _next_trade_date_map(calendar_dates)
    trade_date_keys = [_date_to_tushare(day) for day in trade_dates]

    top_list_raw, top_list_requests = _fetch_endpoint_frames(
        "top_list",
        trade_date_keys,
        adapter.fetch_top_list_by_trade_date,
        progress_callback,
    )
    top_inst_raw, top_inst_requests = _fetch_endpoint_frames(
        "top_inst",
        trade_date_keys,
        adapter.fetch_top_inst_by_trade_date,
        progress_callback,
    )
    top_list, top_list_meta = _normalize_top_list(top_list_raw, next_trade_date, market)
    top_inst, top_inst_meta = _normalize_top_inst(top_inst_raw, next_trade_date, market)
    stock_day = _build_stock_day_aggregate(top_list, top_inst, market)

    endpoint_quality = {
        "top_list": _endpoint_quality(
            top_list,
            requests=top_list_requests,
            required_columns_missing=top_list_meta["missing_required_columns"],
            min_non_empty_ratio=min_non_empty_ratio,
            key_columns=["symbol", "date", "reason"],
            value_columns=TOP_LIST_VALUE_COLUMNS,
        ),
        "top_inst": _endpoint_quality(
            top_inst,
            requests=top_inst_requests,
            required_columns_missing=top_inst_meta["missing_required_columns"],
            min_non_empty_ratio=min_non_empty_ratio,
            key_columns=["symbol", "date", "exalter", "side", "reason"],
            value_columns=TOP_INST_VALUE_COLUMNS,
        ),
    }
    aggregate_quality = _aggregate_quality(stock_day)
    if execute_write_processed:
        store = DatasetStore(processed_path)
        _write_processed_by_year(store, "dragon_tiger_top_list", top_list, market, ["symbol", "date", "reason"])
        _write_processed_by_year(store, "dragon_tiger_top_inst", top_inst, market, ["symbol", "date", "exalter", "side", "reason"])
        _write_processed_by_year(store, "dragon_tiger_stock_day", stock_day, market, ["symbol", "date"])

    summary = _summary(endpoint_quality, aggregate_quality)
    report = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "source": "tushare",
        "market": market,
        "start_date": _iso_date(pd.Timestamp(start_date)),
        "end_date": _iso_date(pd.Timestamp(end_date)),
        "calendar_trade_dates": len(trade_dates),
        "processed_writes_enabled": bool(execute_write_processed),
        "processed_root": str(processed_path),
        "thresholds": {"min_non_empty_ratio": float(min_non_empty_ratio)},
        "summary": summary,
        "endpoint_quality": endpoint_quality,
        "aggregate_quality": aggregate_quality,
        "availability_policy": {
            "event_date_column": "trade_date",
            "available_date_rule": "first_trade_date_strictly_after_dragon_tiger_trade_date",
            "same_day_event_trading_allowed": False,
        },
        "promotion_policy": {
            "portfolio_backtest_allowed": False,
            "promotion_claim_allowed": False,
            "next_allowed_action": (
                "Run PIT event IC with industry/size neutralization only after this full coverage audit passes."
            ),
        },
        "safety": SAFETY,
    }
    _write_outputs(output_path, report, top_list, top_inst, stock_day)
    return report


def render_dragon_tiger_coverage_audit_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {}) or {}
    top_list = (report.get("endpoint_quality", {}) or {}).get("top_list", {}) or {}
    top_inst = (report.get("endpoint_quality", {}) or {}).get("top_inst", {}) or {}
    aggregate = report.get("aggregate_quality", {}) or {}
    lines = [
        "# Dragon-Tiger Full Coverage Audit",
        "",
        f"- Stage: {report.get('stage', STAGE)}",
        f"- Market: {report.get('market', '')}",
        f"- Window: {report.get('start_date', '')} to {report.get('end_date', '')}",
        f"- Calendar trade dates: {report.get('calendar_trade_dates', 0)}",
        f"- Status: {summary.get('status', '')}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Processed writes enabled: {report.get('processed_writes_enabled', False)}",
        f"- Promotion allowed: {report.get('promotion_policy', {}).get('promotion_claim_allowed', False)}",
        "",
        "## Endpoint Quality",
        "",
        "| Endpoint | Status | Requests | Non-empty dates | Rows | Empty dates | Errors | Lag violations | Missing available | Duplicate keys |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        _endpoint_markdown_row("top_list", top_list),
        _endpoint_markdown_row("top_inst", top_inst),
        "",
        "## Stock-Day Aggregate",
        "",
        f"- Status: {aggregate.get('status', '')}",
        f"- Rows: {aggregate.get('rows', 0)}",
        f"- Unique symbols: {aggregate.get('unique_symbols', 0)}",
        f"- Date range: {aggregate.get('date_min')} to {aggregate.get('date_max')}",
        f"- Lag violations: {aggregate.get('lag_violation_count', 0)}",
        f"- Missing available dates: {aggregate.get('missing_available_date_count', 0)}",
        "",
        "## Interpretation",
        "",
        "- This is data coverage and PIT timing evidence only.",
        "- It is not IC, Sharpe, total return, win-rate, walk-forward, or promotion evidence.",
        "- Same-day Dragon-Tiger disclosure trading remains blocked.",
    ]
    return "\n".join(lines) + "\n"


def _fetch_endpoint_frames(
    endpoint: str,
    trade_date_keys: list[str],
    fetch: Callable[[str], pd.DataFrame],
    progress_callback: ProgressCallback | None,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    frames: list[pd.DataFrame] = []
    requests: list[dict[str, Any]] = []
    total = len(trade_date_keys)
    for index, trade_date in enumerate(trade_date_keys, start=1):
        _emit_progress(progress_callback, endpoint=endpoint, status="start", trade_date=trade_date, index=index, total=total)
        try:
            frame = fetch(trade_date)
        except Exception as exc:
            requests.append({"trade_date": trade_date, "status": "error", "rows": 0, "error": type(exc).__name__})
            _emit_progress(
                progress_callback,
                endpoint=endpoint,
                status="error",
                trade_date=trade_date,
                index=index,
                total=total,
                error=type(exc).__name__,
            )
            continue
        rows = int(len(frame)) if frame is not None else 0
        requests.append({"trade_date": trade_date, "status": "ok", "rows": rows, "error": ""})
        if frame is not None and not frame.empty:
            frames.append(frame.copy())
        _emit_progress(progress_callback, endpoint=endpoint, status="done", trade_date=trade_date, index=index, total=total, rows=rows)
    if not frames:
        return pd.DataFrame(), requests
    return pd.concat(frames, ignore_index=True), requests


def _calendar_dates(adapter: DragonTigerAdapter, start_date: str, end_date: str) -> list[pd.Timestamp]:
    padded_end = (pd.Timestamp(end_date) + pd.Timedelta(days=14)).date().isoformat()
    for attempt in range(1, CALENDAR_MAX_ATTEMPTS + 1):
        calendar = adapter.fetch_trade_calendar(start_date, padded_end)
        if "date" not in calendar.columns:
            raise ValueError("Tushare trade calendar response is missing date")
        dates = pd.to_datetime(calendar["date"], errors="coerce").dropna().sort_values().drop_duplicates()
        if not dates.empty:
            return [pd.Timestamp(value).normalize() for value in dates]
        if attempt < CALENDAR_MAX_ATTEMPTS:
            sleep(CALENDAR_RETRY_SLEEP_SECONDS)
    raise ValueError(f"Tushare trade calendar response has no open trade dates after {CALENDAR_MAX_ATTEMPTS} attempts")


def _trade_dates_in_window(calendar_dates: list[pd.Timestamp], start_date: str, end_date: str) -> list[pd.Timestamp]:
    start = pd.Timestamp(start_date).normalize()
    end = pd.Timestamp(end_date).normalize()
    return [day for day in calendar_dates if start <= day <= end]


def _next_trade_date_map(calendar_dates: list[pd.Timestamp]) -> dict[object, object]:
    result: dict[object, object] = {}
    for index, day in enumerate(calendar_dates[:-1]):
        result[day.date()] = calendar_dates[index + 1].date()
    return result


def _normalize_top_list(raw: pd.DataFrame, next_trade_date: dict[object, object], market: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    columns = [
        "date",
        "available_date",
        "asset_id",
        "symbol",
        "market",
        "source",
        "ingested_at",
        "name",
        "reason",
        *TOP_LIST_VALUE_COLUMNS,
    ]
    missing_required = _missing_columns(raw, TOP_LIST_REQUIRED_COLUMNS)
    if raw.empty or missing_required:
        return pd.DataFrame(columns=columns), {"missing_required_columns": missing_required}
    source = raw.copy()
    mapped = pd.DataFrame(
        {
            "symbol": _symbol(source),
            "date": _date(source),
            "name": _text(source, "name"),
            "reason": _text(source, "reason"),
        }
    )
    for column in TOP_LIST_VALUE_COLUMNS:
        mapped[column] = _numeric(source, column)
    mapped, dropped = _drop_non_cn_stock_symbols(mapped)
    output = _with_common_columns(mapped, columns, next_trade_date, market, "tushare_top_list")
    output.attrs["dropped_non_cn_symbol_count"] = dropped
    return output, {"missing_required_columns": missing_required}


def _normalize_top_inst(raw: pd.DataFrame, next_trade_date: dict[object, object], market: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    columns = [
        "date",
        "available_date",
        "asset_id",
        "symbol",
        "market",
        "source",
        "ingested_at",
        "exalter",
        "side",
        "reason",
        *TOP_INST_VALUE_COLUMNS,
    ]
    missing_required = _missing_columns(raw, TOP_INST_REQUIRED_COLUMNS)
    if raw.empty or missing_required:
        return pd.DataFrame(columns=columns), {"missing_required_columns": missing_required}
    source = raw.copy()
    mapped = pd.DataFrame(
        {
            "symbol": _symbol(source),
            "date": _date(source),
            "exalter": _text(source, "exalter"),
            "side": _text(source, "side"),
            "reason": _text(source, "reason"),
        }
    )
    for column in TOP_INST_VALUE_COLUMNS:
        mapped[column] = _numeric(source, column)
    mapped, dropped = _drop_non_cn_stock_symbols(mapped)
    output = _with_common_columns(mapped, columns, next_trade_date, market, "tushare_top_inst")
    output.attrs["dropped_non_cn_symbol_count"] = dropped
    return output, {"missing_required_columns": missing_required}


def _build_stock_day_aggregate(top_list: pd.DataFrame, top_inst: pd.DataFrame, market: str) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []
    if not top_list.empty:
        list_frame = top_list.copy()
        grouped = list_frame.groupby(["symbol", "date", "available_date", "asset_id"], dropna=False)
        pieces.append(
            grouped.agg(
                top_list_event_count=("reason", "size"),
                top_list_reason_count=("reason", "nunique"),
                top_list_amount_sum=("amount", "sum"),
                top_list_net_amount_sum=("net_amount", "sum"),
                top_list_abs_pct_change_max=("pct_change", lambda value: float(pd.to_numeric(value, errors="coerce").abs().max())),
                top_list_amount_rate_max=("amount_rate", "max"),
            ).reset_index()
        )
    if not top_inst.empty:
        inst_frame = top_inst.copy()
        grouped = inst_frame.groupby(["symbol", "date", "available_date", "asset_id"], dropna=False)
        inst_agg = grouped.agg(
            top_inst_event_count=("exalter", "size"),
            top_inst_reason_count=("reason", "nunique"),
            top_inst_buy_sum=("buy", "sum"),
            top_inst_sell_sum=("sell", "sum"),
            top_inst_net_buy_sum=("net_buy", "sum"),
            top_inst_abs_net_buy_sum=("net_buy", lambda value: float(pd.to_numeric(value, errors="coerce").abs().sum())),
        ).reset_index()
        pieces.append(inst_agg)
    if not pieces:
        return pd.DataFrame(
            columns=[
                "date",
                "available_date",
                "asset_id",
                "symbol",
                "market",
                "source",
                "ingested_at",
            ]
        )
    merged = pieces[0]
    for piece in pieces[1:]:
        merged = merged.merge(piece, on=["symbol", "date", "available_date", "asset_id"], how="outer")
    for column in [
        "top_list_event_count",
        "top_list_reason_count",
        "top_list_amount_sum",
        "top_list_net_amount_sum",
        "top_list_abs_pct_change_max",
        "top_list_amount_rate_max",
        "top_inst_event_count",
        "top_inst_reason_count",
        "top_inst_buy_sum",
        "top_inst_sell_sum",
        "top_inst_net_buy_sum",
        "top_inst_abs_net_buy_sum",
    ]:
        if column not in merged.columns:
            merged[column] = 0
        merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(0)
    merged["market"] = market
    merged["source"] = "tushare_dragon_tiger_stock_day"
    merged["ingested_at"] = pd.Timestamp.now(tz="UTC")
    columns = [
        "date",
        "available_date",
        "asset_id",
        "symbol",
        "market",
        "source",
        "ingested_at",
        "top_list_event_count",
        "top_list_reason_count",
        "top_list_amount_sum",
        "top_list_net_amount_sum",
        "top_list_abs_pct_change_max",
        "top_list_amount_rate_max",
        "top_inst_event_count",
        "top_inst_reason_count",
        "top_inst_buy_sum",
        "top_inst_sell_sum",
        "top_inst_net_buy_sum",
        "top_inst_abs_net_buy_sum",
    ]
    return merged[columns].sort_values(["symbol", "date"]).reset_index(drop=True)


def _endpoint_quality(
    frame: pd.DataFrame,
    *,
    requests: list[dict[str, Any]],
    required_columns_missing: list[str],
    min_non_empty_ratio: float,
    key_columns: list[str],
    value_columns: list[str],
) -> dict[str, Any]:
    request_count = len(requests)
    request_error_count = sum(1 for row in requests if row.get("status") != "ok")
    non_empty_dates = sum(1 for row in requests if int(row.get("rows") or 0) > 0)
    empty_dates = [str(row.get("trade_date")) for row in requests if row.get("status") == "ok" and int(row.get("rows") or 0) == 0]
    non_empty_ratio = non_empty_dates / request_count if request_count else 0.0
    blockers: list[str] = []
    warnings: list[str] = []
    if request_error_count:
        blockers.append("request_errors_present")
    if required_columns_missing:
        blockers.append("required_columns_missing")
    if request_count and non_empty_ratio < min_non_empty_ratio:
        blockers.append("non_empty_date_ratio_below_threshold")
    if frame.empty:
        blockers.append("normalized_feed_empty")
        return {
            "status": "fail" if blockers else "warn",
            "rows": 0,
            "request_count": request_count,
            "request_error_count": request_error_count,
            "non_empty_dates": non_empty_dates,
            "empty_date_count": len(empty_dates),
            "empty_dates_sample": empty_dates[:20],
            "non_empty_ratio": non_empty_ratio,
            "missing_required_columns": required_columns_missing,
            "warnings": warnings,
            "blockers": _dedupe(blockers),
        }
    dates = pd.to_datetime(frame["date"], errors="coerce")
    available = pd.to_datetime(frame["available_date"], errors="coerce")
    duplicate_key_count = int(frame.duplicated(key_columns).sum())
    exact_duplicate_row_count = int(frame.duplicated().sum())
    missing_available_date_count = int(available.isna().sum())
    lag_violation_count = int((available.notna() & dates.notna() & (available <= dates)).sum())
    if missing_available_date_count:
        blockers.append("missing_available_date_rows")
    if lag_violation_count:
        blockers.append("available_date_not_strictly_after_trade_date")
    if duplicate_key_count:
        warnings.append("duplicate_stock_date_reason_keys_aggregated_later")
    status = "fail" if blockers else "warn" if warnings else "pass"
    return {
        "status": status,
        "rows": int(len(frame)),
        "request_count": request_count,
        "request_error_count": request_error_count,
        "non_empty_dates": non_empty_dates,
        "empty_date_count": len(empty_dates),
        "empty_dates_sample": empty_dates[:20],
        "non_empty_ratio": non_empty_ratio,
        "date_min": dates.min().date().isoformat(),
        "date_max": dates.max().date().isoformat(),
        "available_date_min": _nullable_date_min(available),
        "available_date_max": _nullable_date_max(available),
        "unique_symbols": int(frame["symbol"].nunique()),
        "duplicate_key_count": duplicate_key_count,
        "exact_duplicate_row_count": exact_duplicate_row_count,
        "missing_available_date_count": missing_available_date_count,
        "lag_violation_count": lag_violation_count,
        "dropped_non_cn_symbol_count": int(frame.attrs.get("dropped_non_cn_symbol_count", 0)),
        "missing_required_columns": required_columns_missing,
        "missing_by_column": _missing_by_column(frame, value_columns),
        "coverage_by_year": {str(year): int(count) for year, count in dates.dt.year.value_counts().sort_index().items()},
        "warnings": warnings,
        "blockers": _dedupe(blockers),
    }


def _aggregate_quality(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "status": "fail",
            "rows": 0,
            "unique_symbols": 0,
            "blockers": ["stock_day_aggregate_empty"],
            "missing_available_date_count": 0,
            "lag_violation_count": 0,
        }
    dates = pd.to_datetime(frame["date"], errors="coerce")
    available = pd.to_datetime(frame["available_date"], errors="coerce")
    missing_available = int(available.isna().sum())
    lag_violations = int((available.notna() & dates.notna() & (available <= dates)).sum())
    blockers = []
    if missing_available:
        blockers.append("aggregate_missing_available_date_rows")
    if lag_violations:
        blockers.append("aggregate_available_date_not_strictly_after_trade_date")
    return {
        "status": "fail" if blockers else "pass",
        "rows": int(len(frame)),
        "unique_symbols": int(frame["symbol"].nunique()),
        "date_min": dates.min().date().isoformat(),
        "date_max": dates.max().date().isoformat(),
        "available_date_min": _nullable_date_min(available),
        "available_date_max": _nullable_date_max(available),
        "missing_available_date_count": missing_available,
        "lag_violation_count": lag_violations,
        "blockers": blockers,
    }


def _summary(endpoint_quality: dict[str, dict[str, Any]], aggregate_quality: dict[str, Any]) -> dict[str, Any]:
    blockers = _dedupe(
        [
            f"{endpoint}:{blocker}"
            for endpoint, quality in endpoint_quality.items()
            for blocker in quality.get("blockers", [])
        ]
        + [f"stock_day:{blocker}" for blocker in aggregate_quality.get("blockers", [])]
    )
    statuses = [quality.get("status") for quality in endpoint_quality.values()] + [aggregate_quality.get("status")]
    return {
        "status": "fail" if blockers else "pass" if all(status == "pass" for status in statuses) else "warn",
        "blockers": blockers,
        "endpoint_count": len(endpoint_quality),
        "pass_count": statuses.count("pass"),
        "warn_count": statuses.count("warn"),
        "fail_count": statuses.count("fail"),
        "pit_prescreen_allowed": not blockers,
        "portfolio_grid_allowed": False,
        "promotion_allowed": False,
    }


def _write_outputs(output_path: Path, report: dict[str, Any], top_list: pd.DataFrame, top_inst: pd.DataFrame, stock_day: pd.DataFrame) -> None:
    (output_path / "dragon_tiger_coverage_audit.json").write_text(
        json.dumps(_sanitize(report), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "dragon_tiger_coverage_audit.md").write_text(
        render_dragon_tiger_coverage_audit_markdown(report),
        encoding="utf-8",
    )
    pd.DataFrame(report.get("endpoint_quality", {})).T.to_csv(output_path / "dragon_tiger_endpoint_quality.csv")
    if not top_list.empty:
        top_list.to_csv(output_path / "dragon_tiger_top_list_sample.csv", index=False)
    if not top_inst.empty:
        top_inst.head(50000).to_csv(output_path / "dragon_tiger_top_inst_sample.csv", index=False)
    if not stock_day.empty:
        stock_day.to_csv(output_path / "dragon_tiger_stock_day_aggregate.csv", index=False)


def _write_processed_by_year(
    store: DatasetStore,
    dataset: str,
    frame: pd.DataFrame,
    market: str,
    dedupe_keys: list[str],
) -> None:
    if frame.empty:
        return
    dates = pd.to_datetime(frame["date"], errors="coerce")
    for year, group in frame.groupby(dates.dt.year):
        partitions = {"frequency": "1d", "market": market, "year": str(int(year))}
        merged = group
        if store.exists(f"processed/{dataset}", partitions):
            existing = store.read_frame(f"processed/{dataset}", partitions)
            merged = pd.concat([existing, group], ignore_index=True)
            merged = merged.drop_duplicates(dedupe_keys, keep="last")
        store.write_frame(merged, f"processed/{dataset}", partitions)


def _with_common_columns(
    frame: pd.DataFrame,
    columns: list[str],
    next_trade_date: dict[object, object],
    market: str,
    source_name: str,
) -> pd.DataFrame:
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce").dt.date
    output["available_date"] = output["date"].map(next_trade_date)
    output["market"] = market
    output["source"] = source_name
    output["ingested_at"] = pd.Timestamp.now(tz="UTC")
    output["asset_id"] = output["symbol"].map(_asset_id_from_tushare_symbol)
    for column in columns:
        if column not in output.columns:
            output[column] = pd.NA
    return output[columns].sort_values(["symbol", "date"]).reset_index(drop=True)


def _symbol(frame: pd.DataFrame) -> pd.Series:
    if "ts_code" in frame.columns:
        return frame["ts_code"].astype(str)
    if "symbol" in frame.columns:
        return frame["symbol"].astype(str)
    raise ValueError("Dragon-Tiger frame is missing ts_code/symbol")


def _date(frame: pd.DataFrame) -> pd.Series:
    for column in ["trade_date", "date"]:
        if column in frame.columns:
            return _parse_dates(frame[column])
    raise ValueError("Dragon-Tiger frame is missing trade_date/date")


def _parse_dates(values: pd.Series) -> pd.Series:
    text = values.astype(str)
    digit_mask = text.str.fullmatch(r"\d{8}")
    parsed = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")
    if digit_mask.any():
        parsed.loc[digit_mask] = pd.to_datetime(text.loc[digit_mask], format="%Y%m%d")
    if (~digit_mask).any():
        parsed.loc[~digit_mask] = pd.to_datetime(values.loc[~digit_mask], errors="coerce")
    return parsed.dt.date


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column in frame.columns:
        return pd.to_numeric(frame[column], errors="coerce")
    return pd.Series([pd.NA] * len(frame), index=frame.index)


def _text(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([""] * len(frame), index=frame.index)
    return frame[column].fillna("").astype(str)


def _missing_columns(frame: pd.DataFrame, required: list[str]) -> list[str]:
    if frame.empty:
        return []
    return [column for column in required if column not in frame.columns]


def _missing_by_column(frame: pd.DataFrame, columns: list[str]) -> dict[str, int]:
    return {
        column: int(frame[column].isna().sum())
        for column in columns
        if column in frame.columns and int(frame[column].isna().sum()) > 0
    }


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


def _endpoint_markdown_row(endpoint: str, quality: dict[str, Any]) -> str:
    return (
        f"| `{endpoint}` | {quality.get('status', '')} | {quality.get('request_count', 0)} | "
        f"{quality.get('non_empty_dates', 0)} | {quality.get('rows', 0)} | "
        f"{quality.get('empty_date_count', 0)} | {quality.get('request_error_count', 0)} | "
        f"{quality.get('lag_violation_count', 0)} | {quality.get('missing_available_date_count', 0)} | "
        f"{quality.get('duplicate_key_count', 0)} |"
    )


def _emit_progress(progress_callback: ProgressCallback | None, **event: object) -> None:
    if progress_callback is None:
        return
    progress_callback({"timestamp": pd.Timestamp.now(tz="UTC").isoformat(), **event})


def _date_to_tushare(value: pd.Timestamp) -> str:
    return pd.Timestamp(value).strftime("%Y%m%d")


def _iso_date(value: object) -> str:
    return pd.Timestamp(value).date().isoformat()


def _dedupe(values: list[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value in output:
            continue
        output.append(value)
    return output


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
