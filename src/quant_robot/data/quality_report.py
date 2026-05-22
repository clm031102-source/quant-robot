from __future__ import annotations

from typing import Any

import pandas as pd


def build_quality_report(bars: pd.DataFrame) -> dict[str, Any]:
    required = ["asset_id", "market", "date", "volume"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Quality report bars are missing columns: {', '.join(missing)}")

    dates = pd.to_datetime(bars["date"]).dt.date
    frame = bars.copy()
    frame["date"] = dates
    duplicate_columns = [column for column in ["asset_id", "timestamp", "frequency", "source"] if column in frame.columns]
    if not duplicate_columns:
        duplicate_columns = ["asset_id", "date"]
    duplicate_bars = int(frame.duplicated(duplicate_columns).sum())
    zero_volume_rows = int((pd.to_numeric(frame["volume"], errors="coerce").fillna(0) == 0).sum())
    missing_date_rows = _missing_date_rows(frame)
    return {
        "rows": int(len(frame)),
        "assets": int(frame["asset_id"].nunique()),
        "markets": sorted(str(value) for value in frame["market"].dropna().unique()),
        "start_date": str(min(dates)) if len(dates) else None,
        "end_date": str(max(dates)) if len(dates) else None,
        "duplicate_bars": duplicate_bars,
        "zero_volume_rows": zero_volume_rows,
        "missing_date_rows": missing_date_rows,
        "coverage_by_asset": _coverage_by_asset(frame),
    }


def _missing_date_rows(frame: pd.DataFrame) -> int:
    missing = 0
    for _, group in frame.groupby("asset_id", sort=False):
        unique_dates = sorted(set(group["date"]))
        if len(unique_dates) < 2:
            continue
        expected = pd.date_range(unique_dates[0], unique_dates[-1], freq="D").date
        missing += len(set(expected) - set(unique_dates))
    return int(missing)


def _coverage_by_asset(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for asset_id, group in frame.groupby("asset_id", sort=True):
        rows.append(
            {
                "asset_id": str(asset_id),
                "rows": int(len(group)),
                "start_date": str(group["date"].min()),
                "end_date": str(group["date"].max()),
            }
        )
    return rows
