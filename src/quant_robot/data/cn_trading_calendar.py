from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from quant_robot.storage.atomic import atomic_write, atomic_write_json
from quant_robot.storage.fingerprints import sha256_file, sha256_text_parts


CALENDAR_SCHEMA_VERSION = 1
REQUIRED_EXCHANGES = ("SSE", "SZSE")
CALENDAR_FILENAME = "cn_trading_calendar.csv"
MANIFEST_FILENAME = "cn_trading_calendar_manifest.json"
SAFETY_TEXT = "Research data only. No broker connection, no account reads, no order placement, no live trading."


def build_cn_trading_calendar(
    exchange_frames: Mapping[str, pd.DataFrame],
    *,
    start_date: str,
    end_date: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    requested_start = _iso_date(start_date)
    requested_end = _iso_date(end_date)
    if requested_start > requested_end:
        raise ValueError("calendar start_date must not be after end_date")

    dates_by_exchange: dict[str, list[str]] = {}
    for exchange in REQUIRED_EXCHANGES:
        frame = exchange_frames.get(exchange)
        if frame is None or frame.empty:
            raise ValueError(f"{exchange} calendar is empty")
        dates_by_exchange[exchange] = _exchange_dates(frame, exchange, requested_start, requested_end)
        if not dates_by_exchange[exchange]:
            raise ValueError(f"{exchange} calendar is empty")

    reference = set(dates_by_exchange[REQUIRED_EXCHANGES[0]])
    for exchange in REQUIRED_EXCHANGES[1:]:
        current = set(dates_by_exchange[exchange])
        if current != reference:
            left_only = sorted(reference - current)[:5]
            right_only = sorted(current - reference)[:5]
            raise ValueError(
                "Tushare exchange calendars diverge: "
                f"{REQUIRED_EXCHANGES[0]}_only={left_only}, {exchange}_only={right_only}"
            )

    dates = sorted(reference)
    calendar = pd.DataFrame(
        {
            "market": ["CN"] * len(dates),
            "date": dates,
            "is_open": [1] * len(dates),
            "source": ["tushare"] * len(dates),
        }
    )
    manifest = {
        "calendar_schema_version": CALENDAR_SCHEMA_VERSION,
        "stage": "cn_trading_calendar",
        "status": "cleared",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": "tushare",
        "endpoint": "trade_cal",
        "market": "CN",
        "required_exchanges": list(REQUIRED_EXCHANGES),
        "requested_range": {"start": requested_start, "end": requested_end},
        "effective_range": {"start": dates[0], "end": dates[-1]},
        "summary": {
            "session_rows": len(dates),
            "exchange_session_rows": {
                exchange: len(dates_by_exchange[exchange]) for exchange in REQUIRED_EXCHANGES
            },
            "exchange_date_sha256": {
                exchange: _date_fingerprint(dates_by_exchange[exchange]) for exchange in REQUIRED_EXCHANGES
            },
            "session_date_sha256": _date_fingerprint(dates),
        },
        "decision": {"calendar_cleared": True, "blockers": []},
        "live_boundary_allowed": False,
        "safety": SAFETY_TEXT,
    }
    return calendar, manifest


def write_cn_trading_calendar(
    output_dir: str | Path,
    calendar: pd.DataFrame,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    output_path = Path(output_dir)
    calendar_path = output_path / CALENDAR_FILENAME
    manifest_path = output_path / MANIFEST_FILENAME
    atomic_write(calendar_path, lambda temporary: calendar.to_csv(temporary, index=False))
    final_manifest = dict(manifest)
    final_manifest["artifact"] = {
        "path": str(calendar_path),
        "sha256": sha256_file(calendar_path),
        "size_bytes": int(calendar_path.stat().st_size),
    }
    atomic_write_json(manifest_path, final_manifest)
    return {
        "calendar_path": str(calendar_path),
        "manifest_path": str(manifest_path),
        "manifest": final_manifest,
    }


def validate_cn_trading_calendar_artifact(
    calendar_path: str | Path,
    manifest_path: str | Path,
    *,
    expected_start_date: str | None = None,
    expected_end_date: str | None = None,
) -> dict[str, Any]:
    calendar_file = Path(calendar_path)
    manifest_file = Path(manifest_path)
    if not calendar_file.is_file():
        raise ValueError(f"CN trading calendar artifact does not exist: {calendar_file}")
    if not manifest_file.is_file():
        raise ValueError(f"CN trading calendar manifest does not exist: {manifest_file}")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8-sig"))
    if int(manifest.get("calendar_schema_version") or 0) != CALENDAR_SCHEMA_VERSION:
        raise ValueError(f"CN trading calendar schema mismatch: {manifest_file}")
    if manifest.get("status") != "cleared" or manifest.get("decision", {}).get("calendar_cleared") is not True:
        raise ValueError(f"CN trading calendar is not cleared: {manifest_file}")
    if manifest.get("provider") != "tushare" or manifest.get("endpoint") != "trade_cal":
        raise ValueError(f"CN trading calendar provider contract mismatch: {manifest_file}")
    if manifest.get("required_exchanges") != list(REQUIRED_EXCHANGES):
        raise ValueError(f"CN trading calendar required exchanges mismatch: {manifest_file}")
    if manifest.get("live_boundary_allowed") is not False:
        raise ValueError(f"CN trading calendar violates live boundary: {manifest_file}")
    artifact = manifest.get("artifact", {}) if isinstance(manifest.get("artifact"), dict) else {}
    if artifact.get("sha256") != sha256_file(calendar_file):
        raise ValueError(f"CN trading calendar artifact fingerprint mismatch: {calendar_file}")

    calendar = pd.read_csv(calendar_file)
    required_columns = ["market", "date", "is_open", "source"]
    if list(calendar.columns) != required_columns:
        raise ValueError(f"CN trading calendar columns mismatch: {calendar_file}")
    if calendar.empty:
        raise ValueError(f"CN trading calendar is empty: {calendar_file}")
    dates = pd.to_datetime(calendar["date"], errors="raise").dt.strftime("%Y-%m-%d")
    if dates.duplicated().any():
        raise ValueError(f"CN trading calendar contains duplicate dates: {calendar_file}")
    if not calendar["market"].astype(str).eq("CN").all():
        raise ValueError(f"CN trading calendar contains another market: {calendar_file}")
    if not calendar["source"].astype(str).eq("tushare").all():
        raise ValueError(f"CN trading calendar source mismatch: {calendar_file}")
    if not pd.to_numeric(calendar["is_open"], errors="coerce").eq(1).all():
        raise ValueError(f"CN trading calendar contains closed or invalid rows: {calendar_file}")
    requested = manifest.get("requested_range", {}) if isinstance(manifest.get("requested_range"), dict) else {}
    if expected_start_date is not None and requested.get("start") != _iso_date(expected_start_date):
        raise ValueError(f"CN trading calendar requested start mismatch: {manifest_file}")
    if expected_end_date is not None and requested.get("end") != _iso_date(expected_end_date):
        raise ValueError(f"CN trading calendar requested end mismatch: {manifest_file}")
    summary = manifest.get("summary", {}) if isinstance(manifest.get("summary"), dict) else {}
    normalized_dates = dates.tolist()
    if int(summary.get("session_rows") or 0) != len(normalized_dates):
        raise ValueError(f"CN trading calendar row count mismatch: {manifest_file}")
    if summary.get("session_date_sha256") != _date_fingerprint(normalized_dates):
        raise ValueError(f"CN trading calendar session fingerprint mismatch: {manifest_file}")
    effective = manifest.get("effective_range", {}) if isinstance(manifest.get("effective_range"), dict) else {}
    if effective != {"start": normalized_dates[0], "end": normalized_dates[-1]}:
        raise ValueError(f"CN trading calendar effective range mismatch: {manifest_file}")
    return manifest


def _exchange_dates(frame: pd.DataFrame, exchange: str, start_date: str, end_date: str) -> list[str]:
    missing = [column for column in ("date", "is_open") if column not in frame.columns]
    if missing:
        raise ValueError(f"{exchange} calendar is missing columns: {', '.join(missing)}")
    source = frame.copy()
    if "exchange" in source.columns:
        exchanges = {str(value).upper() for value in source["exchange"].dropna().unique()}
        if exchanges and exchanges != {exchange}:
            raise ValueError(f"{exchange} calendar contains mismatched exchanges: {sorted(exchanges)}")
    source = source[pd.to_numeric(source["is_open"], errors="coerce").eq(1)]
    dates = pd.to_datetime(source["date"], errors="raise").dt.strftime("%Y-%m-%d")
    if dates.duplicated().any():
        raise ValueError(f"{exchange} calendar contains duplicate dates")
    if ((dates < start_date) | (dates > end_date)).any():
        raise ValueError(f"{exchange} calendar contains dates outside the requested range")
    return sorted(dates.tolist())


def _date_fingerprint(dates: list[str]) -> str:
    return sha256_text_parts(sorted(str(value) for value in dates))


def _iso_date(value: str) -> str:
    return pd.Timestamp(value).date().isoformat()
