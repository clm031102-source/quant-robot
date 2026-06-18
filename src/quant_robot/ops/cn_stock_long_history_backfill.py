from __future__ import annotations

import json
from calendar import monthrange
from datetime import date
from pathlib import Path
from typing import Any, Callable

import pandas as pd


STAGE = "cn_stock_long_history_backfill"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."

SOURCE_MAP = {
    "daily": "tushare",
    "daily_basic": "tushare-factor",
    "moneyflow": "tushare-moneyflow",
}


def build_monthly_windows(start_date: str, end_date: str) -> list[dict[str, str]]:
    start = pd.to_datetime(start_date).date()
    end = pd.to_datetime(end_date).date()
    if start > end:
        raise ValueError("start_date must be on or before end_date")
    windows = []
    cursor = start
    while cursor <= end:
        month_end = date(cursor.year, cursor.month, monthrange(cursor.year, cursor.month)[1])
        window_end = min(month_end, end)
        windows.append({"start_date": cursor.isoformat(), "end_date": window_end.isoformat()})
        cursor = window_end + pd.Timedelta(days=1)
    return windows


def run_cn_stock_long_history_backfill(
    *,
    start_date: str,
    end_date: str,
    output_dir: str | Path,
    execute: bool = False,
    interfaces: tuple[str, ...] = ("daily", "daily_basic", "moneyflow"),
    market: str = "CN",
    daily_adjustment_retries: int = 2,
    empty_raw_retries: int = 2,
    ingest_runner: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    windows = build_monthly_windows(start_date, end_date)
    pack = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "mode": "execute" if execute else "dry_run",
        "market": market,
        "start_date": start_date,
        "end_date": end_date,
        "output_dir": str(output_path),
        "interfaces": list(interfaces),
        "windows": [],
        "summary": {"windows": len(windows), "interfaces": 0, "blockers": 0},
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    if not execute:
        pack["windows"] = [{**window, "interfaces": list(interfaces)} for window in windows]
        _write_summary(output_path, pack)
        return pack

    runner = ingest_runner or _default_ingest_runner
    for window in windows:
        window_pack = {**window, "interfaces": []}
        for interface in interfaces:
            result = _run_interface(
                runner,
                interface=interface,
                market=market,
                output_dir=output_path,
                start_date=window["start_date"],
                end_date=window["end_date"],
                daily_adjustment_retries=daily_adjustment_retries,
                empty_raw_retries=empty_raw_retries,
            )
            window_pack["interfaces"].append(result)
            pack["summary"]["interfaces"] += 1
            pack["summary"]["blockers"] += len(result.get("blockers", []))
        pack["windows"].append(window_pack)

    _write_summary(output_path, pack)
    return pack


def _run_interface(
    runner: Callable[..., dict[str, Any]],
    *,
    interface: str,
    market: str,
    output_dir: Path,
    start_date: str,
    end_date: str,
    daily_adjustment_retries: int,
    empty_raw_retries: int,
) -> dict[str, Any]:
    source = _source_for_interface(interface)
    max_attempts = daily_adjustment_retries if interface == "daily" else 1
    max_attempts = max(max_attempts, empty_raw_retries)
    max_attempts = max(1, max_attempts)
    attempts: list[dict[str, Any]] = []
    for attempt_number in range(max_attempts):
        try:
            result = runner(
                source=source,
                market=market,
                output_dir=output_dir,
                start_date=start_date,
                end_date=end_date,
            )
        except RuntimeError as exc:
            if not _is_empty_raw_response_error(exc):
                raise
            attempts.append(_compact_error_attempt(exc))
            if attempt_number + 1 >= max_attempts:
                break
            continue

        compact = _compact_attempt(result)
        if interface != "daily" and _looks_like_empty_trade_calendar_response(compact, start_date, end_date):
            compact = _with_empty_trade_calendar_error(compact, start_date, end_date)
            attempts.append(compact)
            if attempt_number + 1 >= max_attempts:
                break
            continue
        attempts.append(compact)
        if interface == "daily" and not _daily_adjustment_complete(result):
            continue
        break

    latest = attempts[-1]
    blockers = []
    if latest.get("error_kind") == "empty_raw_response":
        blockers.append("empty_raw_response")
    if latest.get("error_kind") == "empty_trade_calendar_response":
        blockers.append("empty_trade_calendar_response")
    if interface == "daily" and "error" not in latest and not _daily_adjustment_complete_from_attempt(latest):
        blockers.append("daily_adjustment_incomplete")
    return {
        "interface": interface,
        "source": source,
        "start_date": start_date,
        "end_date": end_date,
        "attempts": len(attempts),
        "latest": latest,
        "blockers": blockers,
    }


def _source_for_interface(interface: str) -> str:
    try:
        return SOURCE_MAP[interface]
    except KeyError as exc:
        raise ValueError(f"Unsupported CN stock backfill interface: {interface}") from exc


def _daily_adjustment_complete(result: dict[str, Any]) -> bool:
    report = _dict(result.get("adjustment_report"))
    return bool(result.get("adjusted") is True and float(report.get("coverage", 0.0) or 0.0) >= 1.0)


def _daily_adjustment_complete_from_attempt(attempt: dict[str, Any]) -> bool:
    report = _dict(attempt.get("adjustment_report"))
    return bool(attempt.get("adjusted") is True and float(report.get("coverage", 0.0) or 0.0) >= 1.0)


def _compact_attempt(result: dict[str, Any]) -> dict[str, Any]:
    report = _dict(result.get("quality_report"))
    compact = {
        "processed_rows": _int(result.get("processed_rows", report.get("rows", 0))),
        "downloaded_trade_dates": list(result.get("downloaded_trade_dates", [])),
        "skipped_trade_dates": list(result.get("skipped_trade_dates", [])),
    }
    if "adjusted" in result:
        compact["adjusted"] = bool(result.get("adjusted"))
    if "adjustment_report" in result:
        compact["adjustment_report"] = _dict(result.get("adjustment_report"))
    if report:
        compact["quality_report"] = {
            "rows": _int(report.get("rows", result.get("processed_rows", 0))),
            "assets": _int(report.get("assets", 0)),
            "start_date": report.get("start_date"),
            "end_date": report.get("end_date"),
            "missing_numeric_rows": _int(report.get("missing_numeric_rows", 0)),
            "extreme_return_rows": _int(report.get("extreme_return_rows", 0)),
            "zero_volume_rows": _int(report.get("zero_volume_rows", 0)),
        }
    return compact


def _compact_error_attempt(exc: RuntimeError) -> dict[str, Any]:
    return {
        "processed_rows": 0,
        "downloaded_trade_dates": [],
        "skipped_trade_dates": [],
        "error_kind": "empty_raw_response",
        "error": str(exc),
    }


def _is_empty_raw_response_error(exc: RuntimeError) -> bool:
    return "empty raw response" in str(exc).lower()


def _looks_like_empty_trade_calendar_response(attempt: dict[str, Any], start_date: str, end_date: str) -> bool:
    days = (pd.to_datetime(end_date).date() - pd.to_datetime(start_date).date()).days + 1
    return bool(
        days >= 7
        and _int(attempt.get("processed_rows")) == 0
        and not attempt.get("downloaded_trade_dates")
        and not attempt.get("skipped_trade_dates")
    )


def _with_empty_trade_calendar_error(attempt: dict[str, Any], start_date: str, end_date: str) -> dict[str, Any]:
    enriched = dict(attempt)
    enriched["error_kind"] = "empty_trade_calendar_response"
    enriched["error"] = f"empty trade calendar response for monthly window {start_date} to {end_date}"
    return enriched


def _write_summary(output_path: Path, pack: dict[str, Any]) -> None:
    (output_path / "cn_stock_long_history_backfill_summary.json").write_text(
        json.dumps(_sanitize(pack), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _default_ingest_runner(**kwargs: Any) -> dict[str, Any]:
    from scripts.ingest_data import run_ingest

    return run_ingest(**kwargs)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
