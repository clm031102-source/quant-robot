from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd


GAP_COLUMNS = [
    "asset_id",
    "symbol",
    "exchange",
    "missing_date",
    "classification",
    "list_date",
    "delist_date",
    "evidence_source",
    "suspend_date",
    "resume_date",
]

COVERAGE_COLUMNS = [
    "asset_id",
    "symbol",
    "exchange",
    "first_observed_date",
    "last_observed_date",
    "list_date",
    "delist_date",
    "observed_rows",
    "raw_expected_sessions",
    "raw_gap_rows",
    "listed_expected_sessions",
    "listed_observed_rows",
    "official_daily_suspension_rows",
    "official_legacy_suspension_rows",
    "unresolved_active_session_rows",
    "missing_lifecycle_metadata_rows",
    "observed_outside_lifecycle_rows",
]

OUTSIDE_COLUMNS = [
    "asset_id",
    "symbol",
    "exchange",
    "date",
    "reason",
    "list_date",
    "delist_date",
]


@dataclass(frozen=True)
class AssetSessionClassification:
    gaps: pd.DataFrame
    coverage_by_asset: pd.DataFrame
    observed_outside_lifecycle: pd.DataFrame
    summary: dict[str, Any]


@dataclass(frozen=True)
class _Lifecycle:
    list_date: date
    delist_date: date | None


@dataclass(frozen=True)
class _LegacyInterval:
    suspend_date: date
    resume_date: date | None
    source: str


def classify_asset_sessions(
    *,
    bars: pd.DataFrame,
    expected_sessions: pd.DataFrame,
    stock_basic: pd.DataFrame,
    daily_suspension: pd.DataFrame | None = None,
    legacy_suspension: pd.DataFrame | None = None,
) -> AssetSessionClassification:
    clean_bars = _prepare_bars(bars)
    calendar = _prepare_sessions(expected_sessions)
    lifecycles = _prepare_lifecycles(stock_basic)
    daily = _prepare_daily_suspension(daily_suspension)
    legacy = _prepare_legacy_suspension(legacy_suspension)

    gap_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    outside_rows: list[dict[str, Any]] = []
    classification_counts: Counter[str] = Counter()
    raw_gap_assets: set[str] = set()
    unresolved_assets: set[str] = set()
    missing_metadata_assets: set[str] = set()
    outside_assets: set[str] = set()

    for asset_id, group in clean_bars.groupby("asset_id", sort=True):
        asset = str(asset_id)
        observed = set(group["date"])
        first_observed = min(observed)
        last_observed = max(observed)
        symbol = _first_text(group, "symbol")
        exchange = _first_text(group, "exchange") or _exchange_from_asset_id(asset)
        lifecycle = lifecycles.get(asset)
        if lifecycle is None:
            missing_metadata_assets.add(asset)

        raw_sessions = calendar[
            bisect_left(calendar, first_observed) : bisect_right(calendar, last_observed)
        ]
        asset_counts: Counter[str] = Counter()
        asset_gap_count = 0

        for observed_date in sorted(observed):
            reason = _outside_lifecycle_reason(observed_date, lifecycle, exchange)
            if reason is None:
                continue
            outside_assets.add(asset)
            outside_rows.append(
                {
                    "asset_id": asset,
                    "symbol": symbol,
                    "exchange": exchange,
                    "date": observed_date.isoformat(),
                    "reason": reason,
                    "list_date": _date_text(lifecycle.list_date if lifecycle else None),
                    "delist_date": _date_text(lifecycle.delist_date if lifecycle else None),
                }
            )

        for missing_date in raw_sessions:
            if missing_date in observed:
                continue
            raw_gap_assets.add(asset)
            asset_gap_count += 1
            classification, evidence_source, interval = _classify_gap(
                asset,
                missing_date,
                lifecycle,
                daily,
                legacy,
            )
            classification_counts[classification] += 1
            asset_counts[classification] += 1
            if classification == "unresolved_active_session":
                unresolved_assets.add(asset)
            gap_rows.append(
                {
                    "asset_id": asset,
                    "symbol": symbol,
                    "exchange": exchange,
                    "missing_date": missing_date.isoformat(),
                    "classification": classification,
                    "list_date": _date_text(lifecycle.list_date if lifecycle else None),
                    "delist_date": _date_text(lifecycle.delist_date if lifecycle else None),
                    "evidence_source": evidence_source,
                    "suspend_date": _date_text(interval.suspend_date if interval else None),
                    "resume_date": _date_text(interval.resume_date if interval else None),
                }
            )

        listed_sessions = _listed_sessions(calendar, first_observed, last_observed, lifecycle)
        listed_observed_rows = sum(
            1 for observed_date in observed if _inside_lifecycle(observed_date, lifecycle)
        )
        outside_count = sum(
            1 for observed_date in observed if _outside_lifecycle_reason(observed_date, lifecycle, exchange)
        )
        coverage_rows.append(
            {
                "asset_id": asset,
                "symbol": symbol,
                "exchange": exchange,
                "first_observed_date": first_observed.isoformat(),
                "last_observed_date": last_observed.isoformat(),
                "list_date": _date_text(lifecycle.list_date if lifecycle else None),
                "delist_date": _date_text(lifecycle.delist_date if lifecycle else None),
                "observed_rows": int(len(group)),
                "raw_expected_sessions": int(len(raw_sessions)),
                "raw_gap_rows": int(asset_gap_count),
                "listed_expected_sessions": int(len(listed_sessions)),
                "listed_observed_rows": int(listed_observed_rows),
                "official_daily_suspension_rows": int(asset_counts["official_daily_suspension"]),
                "official_legacy_suspension_rows": int(asset_counts["official_legacy_suspension"]),
                "unresolved_active_session_rows": int(asset_counts["unresolved_active_session"]),
                "missing_lifecycle_metadata_rows": int(asset_counts["missing_lifecycle_metadata"]),
                "observed_outside_lifecycle_rows": int(outside_count),
            }
        )

    gaps = pd.DataFrame(gap_rows, columns=GAP_COLUMNS)
    coverage = pd.DataFrame(coverage_rows, columns=COVERAGE_COLUMNS)
    outside = pd.DataFrame(outside_rows, columns=OUTSIDE_COLUMNS)
    summary = {
        "bar_rows": int(len(clean_bars)),
        "assets": int(clean_bars["asset_id"].nunique()),
        "expected_market_sessions": int(len(calendar)),
        "raw_gap_rows": int(len(gaps)),
        "raw_gap_assets": int(len(raw_gap_assets)),
        "before_official_list_date_rows": int(classification_counts["before_official_list_date"]),
        "after_official_delist_date_rows": int(classification_counts["after_official_delist_date"]),
        "official_daily_suspension_rows": int(classification_counts["official_daily_suspension"]),
        "official_legacy_suspension_rows": int(classification_counts["official_legacy_suspension"]),
        "missing_lifecycle_metadata_rows": int(classification_counts["missing_lifecycle_metadata"]),
        "missing_lifecycle_metadata_assets": int(len(missing_metadata_assets)),
        "unresolved_active_session_rows": int(classification_counts["unresolved_active_session"]),
        "unresolved_active_session_assets": int(len(unresolved_assets)),
        "observed_outside_lifecycle_rows": int(len(outside)),
        "observed_outside_lifecycle_assets": int(len(outside_assets)),
        "classification_rows": int(sum(classification_counts.values())),
    }
    return AssetSessionClassification(
        gaps=gaps,
        coverage_by_asset=coverage,
        observed_outside_lifecycle=outside,
        summary=summary,
    )


def _prepare_bars(frame: pd.DataFrame) -> pd.DataFrame:
    _require_columns(frame, ["asset_id", "date"], "bars")
    bars = frame.copy()
    bars["asset_id"] = bars["asset_id"].astype(str)
    bars["date"] = _date_series(bars["date"], "bars.date")
    if bars.duplicated(["asset_id", "date"]).any():
        raise ValueError("bars contain duplicate asset-session rows")
    return bars.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _prepare_sessions(frame: pd.DataFrame) -> list[date]:
    _require_columns(frame, ["date"], "expected sessions")
    dates = _date_series(frame["date"], "expected_sessions.date")
    if dates.duplicated().any():
        raise ValueError("expected sessions contain duplicate dates")
    return sorted(dates.tolist())


def _prepare_lifecycles(frame: pd.DataFrame) -> dict[str, _Lifecycle]:
    _require_columns(frame, ["asset_id", "list_date"], "stock_basic")
    metadata = frame.copy()
    metadata["asset_id"] = metadata["asset_id"].astype(str)
    if metadata.duplicated("asset_id").any():
        raise ValueError("stock_basic contains duplicate asset_id rows")
    metadata["list_date"] = _optional_date_series(metadata["list_date"])
    if "delist_date" not in metadata:
        metadata["delist_date"] = pd.NaT
    metadata["delist_date"] = _optional_date_series(metadata["delist_date"])
    rows: dict[str, _Lifecycle] = {}
    for row in metadata.itertuples(index=False):
        if pd.isna(row.list_date):
            continue
        delist_date = None if pd.isna(row.delist_date) else row.delist_date
        if delist_date is not None and delist_date < row.list_date:
            raise ValueError(f"stock_basic delist_date precedes list_date: {row.asset_id}")
        rows[str(row.asset_id)] = _Lifecycle(row.list_date, delist_date)
    return rows


def _prepare_daily_suspension(frame: pd.DataFrame | None) -> dict[tuple[str, date], str]:
    if frame is None or frame.empty:
        return {}
    _require_columns(frame, ["asset_id", "date"], "daily suspension")
    daily = frame.copy()
    daily["asset_id"] = daily["asset_id"].astype(str)
    daily["date"] = _date_series(daily["date"], "daily_suspension.date")
    if daily.duplicated(["asset_id", "date"]).any():
        raise ValueError("daily suspension contains duplicate asset-session rows")
    if "source" not in daily:
        daily["source"] = "tushare_suspend_d"
    return {
        (str(row.asset_id), row.date): str(row.source or "tushare_suspend_d")
        for row in daily.itertuples(index=False)
    }


def _prepare_legacy_suspension(
    frame: pd.DataFrame | None,
) -> dict[str, list[_LegacyInterval]]:
    if frame is None or frame.empty:
        return {}
    _require_columns(frame, ["asset_id", "suspend_date"], "legacy suspension")
    legacy = frame.copy()
    legacy["asset_id"] = legacy["asset_id"].astype(str)
    legacy["suspend_date"] = _date_series(legacy["suspend_date"], "legacy_suspension.suspend_date")
    if "resume_date" not in legacy:
        legacy["resume_date"] = pd.NaT
    legacy["resume_date"] = _optional_date_series(legacy["resume_date"], open_ended_1900=True)
    if "source" not in legacy:
        legacy["source"] = "tushare_suspend"
    duplicate_columns = ["asset_id", "suspend_date", "resume_date"]
    if legacy.duplicated(duplicate_columns).any():
        raise ValueError("legacy suspension contains duplicate intervals")
    output: dict[str, list[_LegacyInterval]] = {}
    for row in legacy.itertuples(index=False):
        resume_date = None if pd.isna(row.resume_date) else row.resume_date
        if resume_date is not None and resume_date <= row.suspend_date:
            raise ValueError(f"legacy suspension resume_date is not after suspend_date: {row.asset_id}")
        output.setdefault(str(row.asset_id), []).append(
            _LegacyInterval(
                suspend_date=row.suspend_date,
                resume_date=resume_date,
                source=str(row.source or "tushare_suspend"),
            )
        )
    for intervals in output.values():
        intervals.sort(key=lambda item: item.suspend_date)
    return output


def _classify_gap(
    asset_id: str,
    missing_date: date,
    lifecycle: _Lifecycle | None,
    daily: dict[tuple[str, date], str],
    legacy: dict[str, list[_LegacyInterval]],
) -> tuple[str, str, _LegacyInterval | None]:
    if lifecycle is not None and missing_date < lifecycle.list_date:
        return "before_official_list_date", "tushare_stock_basic", None
    if lifecycle is not None and lifecycle.delist_date is not None and missing_date > lifecycle.delist_date:
        return "after_official_delist_date", "tushare_stock_basic", None
    daily_source = daily.get((asset_id, missing_date))
    if daily_source is not None:
        return "official_daily_suspension", daily_source, None
    for interval in legacy.get(asset_id, []):
        if missing_date >= interval.suspend_date and (
            interval.resume_date is None or missing_date < interval.resume_date
        ):
            return "official_legacy_suspension", interval.source, interval
    if lifecycle is None:
        return "missing_lifecycle_metadata", "", None
    return "unresolved_active_session", "", None


def _listed_sessions(
    calendar: list[date],
    first_observed: date,
    last_observed: date,
    lifecycle: _Lifecycle | None,
) -> list[date]:
    if lifecycle is None:
        return []
    start = max(first_observed, lifecycle.list_date)
    end = min(last_observed, lifecycle.delist_date) if lifecycle.delist_date else last_observed
    if end < start:
        return []
    return calendar[bisect_left(calendar, start) : bisect_right(calendar, end)]


def _inside_lifecycle(value: date, lifecycle: _Lifecycle | None) -> bool:
    if lifecycle is None or value < lifecycle.list_date:
        return False
    return lifecycle.delist_date is None or value <= lifecycle.delist_date


def _outside_lifecycle_reason(
    value: date,
    lifecycle: _Lifecycle | None,
    exchange: str,
) -> str | None:
    if lifecycle is None:
        return None
    if value < lifecycle.list_date:
        return "exchange_transition_prelisting" if exchange.upper() == "XBEI" else "before_official_list_date"
    if lifecycle.delist_date is not None and value > lifecycle.delist_date:
        return "after_official_delist_date"
    return None


def _require_columns(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} missing columns: {', '.join(missing)}")


def _date_series(values: pd.Series, label: str) -> pd.Series:
    parsed = _parse_dates(values)
    if parsed.isna().any():
        raise ValueError(f"{label} contains invalid dates")
    return parsed


def _optional_date_series(values: pd.Series, *, open_ended_1900: bool = False) -> pd.Series:
    text = _clean_text(values)
    parsed = _parse_dates(values, errors="coerce")
    if open_ended_1900:
        open_mask = text.isin({"19000101", "1900-01-01"})
        parsed.loc[open_mask] = pd.NaT
    return parsed


def _parse_dates(values: pd.Series, *, errors: str = "raise") -> pd.Series:
    non_null = values.dropna()
    if pd.api.types.is_datetime64_any_dtype(values) or (
        not non_null.empty and isinstance(non_null.iloc[0], date)
    ):
        return pd.to_datetime(values, errors=errors).dt.date
    text = _clean_text(values)
    digit_mask = text.str.fullmatch(r"\d{8}", na=False).fillna(False).astype(bool)
    parsed = pd.Series(pd.NaT, index=values.index, dtype="object")
    if digit_mask.any():
        numeric = pd.to_datetime(text.loc[digit_mask], format="%Y%m%d", errors=errors)
        parsed.loc[digit_mask] = numeric.dt.date
    other_mask = ~digit_mask & (text != "") & (text.str.lower() != "nat")
    if other_mask.any():
        other = pd.to_datetime(values.loc[other_mask], errors=errors)
        parsed.loc[other_mask] = other.dt.date
    return parsed


def _clean_text(values: pd.Series) -> pd.Series:
    return values.map(lambda value: "" if pd.isna(value) else str(value).strip())


def _first_text(frame: pd.DataFrame, column: str) -> str:
    if column not in frame:
        return ""
    values = frame[column].dropna().astype(str)
    return values.iloc[0] if not values.empty else ""


def _exchange_from_asset_id(asset_id: str) -> str:
    parts = asset_id.split("_")
    return parts[1] if len(parts) >= 3 else ""


def _date_text(value: date | None) -> str:
    return value.isoformat() if value is not None else ""
