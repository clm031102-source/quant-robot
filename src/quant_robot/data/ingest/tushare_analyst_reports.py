from __future__ import annotations

from collections.abc import Callable
from datetime import date
import json
import re
from pathlib import Path
from time import sleep
from typing import Any, Protocol, Sequence

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore


SAFETY = "research-to-review only; no broker, account, order, or live-trading access"
ANALYST_REPORT_COLUMNS = [
    "report_date",
    "available_date",
    "asset_id",
    "symbol",
    "market",
    "source",
    "name",
    "org_name",
    "author_name",
    "report_title",
    "report_type",
    "rating",
    "quarter",
    "eps",
    "np",
    "roe",
    "tp",
    "min_price",
    "max_price",
    "pe",
    "op_rt",
    "op_pr",
    "ev_ebitda",
]


class TushareAnalystReportAdapter(Protocol):
    def fetch_report_rc(self, start_date: str = "", end_date: str = "", ts_code: str = "") -> pd.DataFrame:
        ...


ProgressCallback = Callable[[dict[str, object]], None]


def run_tushare_analyst_report_cache(
    adapter: TushareAnalystReportAdapter,
    start_date: str,
    end_date: str,
    output_dir: str | Path,
    *,
    processed_output_dir: str | Path | None = None,
    execute_write_processed: bool = True,
    resume: bool = True,
    window_frequency: str = "MS",
    request_sleep_seconds: float = 3660.0,
    max_rows_per_window: int = 5000,
    stop_on_rate_limit: bool = True,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, object]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    processed_path = Path(processed_output_dir) if processed_output_dir else output_path
    if execute_write_processed:
        processed_path.mkdir(parents=True, exist_ok=True)
    store = DatasetStore(processed_path)

    windows = _date_windows(start_date, end_date, frequency=window_frequency)
    rows_by_window: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    row_cap_warnings: list[dict[str, object]] = []
    normalized_frames: list[pd.DataFrame] = []
    fetched_count = 0
    stopped_on_rate_limit = False

    for index, (window_start, window_end) in enumerate(windows):
        start_label = _date_to_tushare(window_start)
        end_label = _date_to_tushare(window_end)
        partitions = {"window_start": start_label, "window_end": end_label}
        if resume and execute_write_processed and store.exists("processed/analyst_report_rc_window", partitions):
            cached = store.read_frame("processed/analyst_report_rc_window", partitions)
            rows_by_window.append(
                {
                    "window_start": start_label,
                    "window_end": end_label,
                    "rows": int(len(cached)),
                    "status": "cached",
                }
            )
            normalized_frames.append(_normalize_analyst_report_rc(cached))
            continue

        _emit(progress_callback, status="start", window_start=start_label, window_end=end_label)
        try:
            raw = adapter.fetch_report_rc(start_date=start_label, end_date=end_label)
        except Exception as exc:  # pragma: no cover - live provider behavior
            rate_limit = _provider_rate_limit(str(exc))
            failure = {
                "window_start": start_label,
                "window_end": end_label,
                "status": "failed",
                "error": type(exc).__name__,
                "message": str(exc),
            }
            if rate_limit:
                failure.update(rate_limit)
            failures.append(failure)
            rows_by_window.append(failure)
            _emit(progress_callback, **failure)
            if rate_limit and stop_on_rate_limit:
                stopped_on_rate_limit = True
                break
            if request_sleep_seconds > 0 and index < len(windows) - 1:
                sleep(float(request_sleep_seconds))
            continue

        normalized = _normalize_analyst_report_rc(raw)
        rows = int(len(normalized))
        fetched_count += 1
        status = "ok"
        if rows >= int(max_rows_per_window):
            warning = {
                "window_start": start_label,
                "window_end": end_label,
                "rows": rows,
                "warning": "row_count_at_or_above_window_cap_use_smaller_window",
            }
            row_cap_warnings.append(warning)
            status = "cap_warning"
        rows_by_window.append({"window_start": start_label, "window_end": end_label, "rows": rows, "status": status})
        if execute_write_processed:
            store.write_frame(normalized, "processed/analyst_report_rc_window", partitions)
        normalized_frames.append(normalized)
        _emit(progress_callback, status=status, rows=rows, window_start=start_label, window_end=end_label)
        if request_sleep_seconds > 0 and index < len(windows) - 1:
            sleep(float(request_sleep_seconds))

    combined = _concat(normalized_frames)
    if execute_write_processed and not combined.empty:
        for year, year_frame in combined.groupby(combined["report_date"].dt.year, sort=True):
            store.write_frame(year_frame.reset_index(drop=True), "processed/analyst_report_rc", {"year": str(int(year))})

    result: dict[str, object] = {
        "stage": "tushare_analyst_report_cache",
        "generated_at": date.today().isoformat(),
        "source": "tushare_report_rc",
        "start_date": _date_iso(start_date),
        "end_date": _date_iso(end_date),
        "window_frequency": window_frequency,
        "processed_output_dir": str(processed_path),
        "processed_writes_enabled": bool(execute_write_processed),
        "resume": bool(resume),
        "summary": {
            "windows": int(len(windows)),
            "fetched_windows": int(fetched_count),
            "failed_windows": int(len(failures)),
            "rate_limited_windows": int(sum(1 for failure in failures if "provider_rate_limit" in failure)),
            "next_retry_after_seconds": _next_retry_after_seconds(failures),
            "stopped_on_rate_limit": bool(stopped_on_rate_limit),
            "row_cap_warning_windows": int(len(row_cap_warnings)),
            "rows": int(len(combined)),
            "assets": int(combined["asset_id"].nunique()) if not combined.empty else 0,
            "min_report_date": _min_date(combined, "report_date"),
            "max_report_date": _max_date(combined, "report_date"),
        },
        "rows_by_window": rows_by_window,
        "row_cap_warnings": row_cap_warnings,
        "failures": failures,
        "columns": ANALYST_REPORT_COLUMNS,
        "safety": SAFETY,
        "live_boundary_allowed": False,
    }
    (output_path / "tushare_analyst_report_cache.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "tushare_analyst_report_cache.md").write_text(_markdown(result), encoding="utf-8")
    return result


def _normalize_analyst_report_rc(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=ANALYST_REPORT_COLUMNS)
    source = frame.copy()
    if "symbol" not in source and "ts_code" in source:
        source["symbol"] = source["ts_code"].astype(str)
    output = pd.DataFrame(
        {
            "report_date": _date_series(source, "report_date"),
            "available_date": _date_series(source, "report_date"),
            "asset_id": source["symbol"].map(_asset_id_from_symbol) if "symbol" in source else pd.NA,
            "symbol": source["symbol"].astype(str) if "symbol" in source else pd.NA,
            "market": "CN",
            "source": "tushare_report_rc",
            "name": _text_series(source, "name"),
            "org_name": _text_series(source, "org_name"),
            "author_name": _text_series(source, "author_name"),
            "report_title": _text_series(source, "report_title"),
            "report_type": _text_series(source, "report_type"),
            "rating": _text_series(source, "rating"),
            "quarter": _text_series(source, "quarter"),
            "eps": _num_series(source, "eps"),
            "np": _num_series(source, "np"),
            "roe": _num_series(source, "roe"),
            "tp": _num_series(source, "tp"),
            "min_price": _num_series(source, "min_price"),
            "max_price": _num_series(source, "max_price"),
            "pe": _num_series(source, "pe"),
            "op_rt": _num_series(source, "op_rt"),
            "op_pr": _num_series(source, "op_pr"),
            "ev_ebitda": _num_series(source, "ev_ebitda"),
        }
    )
    return (
        output.dropna(subset=["report_date", "asset_id", "symbol"])
        .drop_duplicates(["symbol", "report_date", "org_name", "author_name", "report_title"], keep="last")
        .sort_values(["symbol", "report_date", "org_name", "author_name"])
        .reset_index(drop=True)[ANALYST_REPORT_COLUMNS]
    )


def _date_windows(start_date: str, end_date: str, *, frequency: str) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    if start > end:
        raise ValueError("start_date must be <= end_date")
    if frequency.upper() in {"D", "1D"}:
        starts = pd.date_range(start, end, freq="D")
    else:
        starts = pd.date_range(start, end, freq=frequency)
        if len(starts) == 0 or starts[0] > start:
            starts = starts.insert(0, start)
    windows: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for index, window_start in enumerate(starts):
        next_start = starts[index + 1] if index + 1 < len(starts) else end + pd.Timedelta(days=1)
        window_end = min(next_start - pd.Timedelta(days=1), end)
        if window_start <= window_end:
            windows.append((pd.Timestamp(window_start), pd.Timestamp(window_end)))
    return windows


def _asset_id_from_symbol(symbol: Any) -> str | None:
    text = str(symbol).strip()
    if "." not in text:
        return None
    code, suffix = text.split(".", 1)
    exchange = {"SZ": "XSHE", "SH": "XSHG", "BJ": "XBEI"}.get(suffix.upper())
    if not exchange:
        return None
    return f"CN_{exchange}_{code}"


def _date_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(pd.NaT, index=frame.index, dtype="datetime64[ns]")
    return pd.to_datetime(frame[column], errors="coerce")


def _text_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series("", index=frame.index, dtype=str)
    return frame[column].fillna("").astype(str)


def _num_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _concat(frames: Sequence[pd.DataFrame]) -> pd.DataFrame:
    valid = [frame for frame in frames if isinstance(frame, pd.DataFrame) and not frame.empty]
    if not valid:
        return pd.DataFrame(columns=ANALYST_REPORT_COLUMNS)
    return pd.concat(valid, ignore_index=True).drop_duplicates().reset_index(drop=True)


def _date_to_tushare(value: str | pd.Timestamp) -> str:
    return pd.Timestamp(value).strftime("%Y%m%d")


def _date_iso(value: str | pd.Timestamp) -> str:
    return pd.Timestamp(value).date().isoformat()


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    values = pd.to_datetime(frame[column], errors="coerce").dropna()
    return pd.Timestamp(values.min()).date().isoformat() if not values.empty else None


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    values = pd.to_datetime(frame[column], errors="coerce").dropna()
    return pd.Timestamp(values.max()).date().isoformat() if not values.empty else None


def _emit(callback: ProgressCallback | None, **payload: object) -> None:
    if callback is not None:
        callback(payload)


def _provider_rate_limit(message: str) -> dict[str, object]:
    if "频率超限" not in message and "frequency" not in message.lower():
        return {}
    match = re.search(r"(\d+)\s*次\s*/\s*(分钟|小时|天|日)", message)
    if not match:
        return {"provider_rate_limit": "unknown", "retry_after_seconds": None}
    count = int(match.group(1))
    unit = match.group(2)
    seconds_by_unit = {"分钟": 60, "小时": 3600, "天": 86400, "日": 86400}
    retry_after = seconds_by_unit[unit]
    return {
        "provider_rate_limit": f"{count}_per_{'minute' if unit == '分钟' else 'hour' if unit == '小时' else 'day'}",
        "retry_after_seconds": retry_after,
    }


def _next_retry_after_seconds(failures: list[dict[str, object]]) -> int | None:
    retry_after_values = [
        int(failure["retry_after_seconds"])
        for failure in failures
        if failure.get("retry_after_seconds") is not None
    ]
    return max(retry_after_values) if retry_after_values else None


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, (pd.Timestamp, date)):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def _markdown(result: dict[str, object]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Tushare Analyst Report Cache",
        "",
        f"- Stage: {result.get('stage')}",
        f"- Source: {result.get('source')}",
        f"- Window: {result.get('start_date')}..{result.get('end_date')}",
        f"- Rows: {summary.get('rows', 0) if isinstance(summary, dict) else 0}",
        f"- Assets: {summary.get('assets', 0) if isinstance(summary, dict) else 0}",
        f"- Failed windows: {summary.get('failed_windows', 0) if isinstance(summary, dict) else 0}",
        f"- Cap-warning windows: {summary.get('row_cap_warning_windows', 0) if isinstance(summary, dict) else 0}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Interpretation",
        "",
        "- This cache is source proof and factor input only; it is not a trading signal.",
        "- Windows at or above the provider row cap must be rerun with a smaller window before full-sample claims.",
    ]
    return "\n".join(lines) + "\n"
