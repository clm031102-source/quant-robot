from __future__ import annotations

from typing import Any

import pandas as pd


def build_quality_report(
    bars: pd.DataFrame,
    expected_dates: list[object] | None = None,
    *,
    extreme_return_threshold: float = 0.50,
    stale_price_days: int = 3,
    adj_close_jump_threshold: float = 0.50,
) -> dict[str, Any]:
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
    expected = [value.date() if hasattr(value, "date") else value for value in expected_dates] if expected_dates else None
    expected = list(pd.to_datetime(expected).date) if expected is not None else None
    missing_date_rows = _missing_date_rows(frame, expected)
    price_column = _price_column(frame)
    return {
        "rows": int(len(frame)),
        "assets": int(frame["asset_id"].nunique()),
        "markets": sorted(str(value) for value in frame["market"].dropna().unique()),
        "start_date": str(min(dates)) if len(dates) else None,
        "end_date": str(max(dates)) if len(dates) else None,
        "duplicate_bars": duplicate_bars,
        "zero_volume_rows": zero_volume_rows,
        "missing_date_rows": missing_date_rows,
        "extreme_return_rows": _extreme_return_rows(frame, price_column, extreme_return_threshold),
        "stale_price_rows": _stale_price_rows(frame, price_column, stale_price_days),
        "adj_close_jump_rows": _adj_close_jump_rows(frame, adj_close_jump_threshold),
        "coverage_by_asset": _coverage_by_asset(frame, expected),
    }


def _missing_date_rows(frame: pd.DataFrame, expected_dates: list[object] | None) -> int:
    missing = 0
    for _, group in frame.groupby("asset_id", sort=False):
        unique_dates = sorted(set(group["date"]))
        if len(unique_dates) < 2:
            continue
        if expected_dates is None:
            expected = pd.date_range(unique_dates[0], unique_dates[-1], freq="D").date
        else:
            expected = [date for date in expected_dates if unique_dates[0] <= date <= unique_dates[-1]]
        missing += len(set(expected) - set(unique_dates))
    return int(missing)


def _coverage_by_asset(frame: pd.DataFrame, expected_dates: list[object] | None = None) -> list[dict[str, Any]]:
    rows = []
    for asset_id, group in frame.groupby("asset_id", sort=True):
        unique_dates = sorted(set(group["date"]))
        rows.append(
            {
                "asset_id": str(asset_id),
                "rows": int(len(group)),
                "start_date": str(group["date"].min()),
                "end_date": str(group["date"].max()),
                "missing_trade_dates": _missing_trade_dates(unique_dates, expected_dates),
            }
        )
    return rows


def _missing_trade_dates(unique_dates: list[object], expected_dates: list[object] | None) -> list[str]:
    if len(unique_dates) < 2:
        return []
    if expected_dates is None:
        expected = pd.date_range(unique_dates[0], unique_dates[-1], freq="D").date
    else:
        expected = [date for date in expected_dates if unique_dates[0] <= date <= unique_dates[-1]]
    missing = sorted(set(expected) - set(unique_dates))
    return [str(value) for value in missing]


def _price_column(frame: pd.DataFrame) -> str | None:
    if "adj_close" in frame.columns:
        return "adj_close"
    if "close" in frame.columns:
        return "close"
    return None


def _extreme_return_rows(frame: pd.DataFrame, price_column: str | None, threshold: float) -> int:
    if price_column is None:
        return 0
    rows = 0
    for _, group in frame.sort_values(["asset_id", "date"]).groupby("asset_id", sort=False):
        prices = pd.to_numeric(group[price_column], errors="coerce")
        rows += int((prices.pct_change().abs() > abs(threshold)).sum())
    return rows


def _stale_price_rows(frame: pd.DataFrame, price_column: str | None, stale_price_days: int) -> int:
    if price_column is None or stale_price_days <= 1:
        return 0
    rows = 0
    for _, group in frame.sort_values(["asset_id", "date"]).groupby("asset_id", sort=False):
        prices = pd.to_numeric(group[price_column], errors="coerce")
        run_ids = prices.ne(prices.shift()).cumsum()
        for _, run in prices.groupby(run_ids):
            clean = run.dropna()
            if len(clean) >= stale_price_days:
                rows += len(clean)
    return int(rows)


def _adj_close_jump_rows(frame: pd.DataFrame, threshold: float) -> int:
    if "adj_close" not in frame.columns or "close" not in frame.columns:
        return 0
    rows = 0
    for _, group in frame.sort_values(["asset_id", "date"]).groupby("asset_id", sort=False):
        close = pd.to_numeric(group["close"], errors="coerce").replace(0.0, pd.NA)
        adj_close = pd.to_numeric(group["adj_close"], errors="coerce")
        ratio = (adj_close / close).dropna()
        rows += int((ratio.pct_change().abs() > abs(threshold)).sum())
    return rows
