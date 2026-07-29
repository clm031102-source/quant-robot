from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


CANONICAL_COLUMNS = [
    "nav_date",
    "ann_date",
    "known_from",
    "asset_id",
    "symbol",
    "exchange",
    "unit_nav",
    "accum_nav",
    "total_netasset",
    "update_flag",
    "is_pit_usable",
    "source",
]

_OPTIONAL_NUMERIC_COLUMNS = ["accum_nav", "total_netasset", "update_flag"]
_CONFLICT_VALUE_COLUMNS = ["unit_nav", "accum_nav", "total_netasset"]
_EXCHANGE_DETAILS = {
    "SSE": (".SH", "XSHG"),
    "SH": (".SH", "XSHG"),
    "XSHG": (".SH", "XSHG"),
    "SZSE": (".SZ", "XSHE"),
    "SZ": (".SZ", "XSHE"),
    "XSHE": (".SZ", "XSHE"),
}


def build_tushare_fund_nav_request_plan(
    target_universe: pd.DataFrame,
    *,
    start_date: str | pd.Timestamp,
    end_date: str | pd.Timestamp,
) -> pd.DataFrame:
    required = {"etf_code", "market_exchange", "list_date", "delist_date"}
    missing = sorted(required - set(target_universe.columns))
    if missing:
        raise ValueError(f"target universe is missing columns: {', '.join(missing)}")

    analysis_start = _as_date(start_date, "start_date")
    analysis_end = _as_date(end_date, "end_date")
    if analysis_start > analysis_end:
        raise ValueError("start_date must be on or before end_date")

    rows: list[dict[str, object]] = []
    for record in target_universe.to_dict(orient="records"):
        exchange_key = str(record["market_exchange"]).strip().upper()
        if exchange_key not in _EXCHANGE_DETAILS:
            raise ValueError(f"unsupported ETF exchange: {exchange_key}")
        expected_suffix, canonical_exchange = _EXCHANGE_DETAILS[exchange_key]
        raw_symbol = str(record["etf_code"]).strip().upper()
        symbol = raw_symbol if raw_symbol.endswith((".SH", ".SZ")) else raw_symbol + expected_suffix
        if not symbol.endswith(expected_suffix):
            raise ValueError(
                f"ETF symbol/exchange mismatch: {symbol} does not match {exchange_key}"
            )
        code = symbol.split(".", maxsplit=1)[0]
        if not code.isdigit() or len(code) != 6:
            raise ValueError(f"invalid ETF symbol: {symbol}")

        list_date = _as_optional_date(record["list_date"], f"{symbol} list_date")
        if list_date is None:
            raise ValueError(f"{symbol} list_date is required")
        delist_date = _as_optional_date(record["delist_date"], f"{symbol} delist_date")
        request_start = max(analysis_start, list_date)
        request_end = min(analysis_end, delist_date or analysis_end)
        if request_start > request_end:
            continue
        rows.append(
            {
                "asset_id": f"CN_ETF_{canonical_exchange}_{code}",
                "symbol": symbol,
                "exchange": canonical_exchange,
                "request_start": request_start,
                "request_end": request_end,
            }
        )

    result = pd.DataFrame(
        rows,
        columns=["asset_id", "symbol", "exchange", "request_start", "request_end"],
    )
    if result["symbol"].duplicated().any():
        duplicates = sorted(result.loc[result["symbol"].duplicated(keep=False), "symbol"].unique())
        raise ValueError(f"target universe contains duplicate ETF symbols: {', '.join(duplicates[:5])}")
    return result.sort_values("symbol").reset_index(drop=True)


def canonicalize_tushare_fund_nav(
    raw: pd.DataFrame,
    trading_sessions: Sequence[pd.Timestamp],
    *,
    start_date: str | pd.Timestamp | None = None,
    end_date: str | pd.Timestamp | None = None,
    source: str = "tushare_fund_nav",
) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)
    required = {"symbol", "nav_date", "ann_date", "unit_nav"}
    missing = sorted(required - set(raw.columns))
    if missing:
        raise ValueError(f"Tushare fund NAV input is missing columns: {', '.join(missing)}")

    sessions = pd.DatetimeIndex(pd.to_datetime(pd.Series(trading_sessions), errors="raise")).normalize()
    if sessions.empty:
        raise ValueError("trading_sessions must not be empty")
    if sessions.duplicated().any():
        raise ValueError("trading_sessions contains duplicate dates")
    if not sessions.is_monotonic_increasing:
        sessions = sessions.sort_values()

    frame = raw.copy()
    frame["symbol"] = frame["symbol"].astype(str).str.strip().str.upper()
    invalid_symbols = ~frame["symbol"].str.fullmatch(r"\d{6}\.(SH|SZ)")
    if invalid_symbols.any():
        raise ValueError(f"invalid ETF symbol: {frame.loc[invalid_symbols, 'symbol'].iloc[0]}")
    frame["nav_date"] = pd.to_datetime(frame["nav_date"], errors="coerce").dt.normalize()
    if frame["nav_date"].isna().any():
        raise ValueError("Tushare fund NAV input contains invalid nav_date")
    frame["ann_date"] = pd.to_datetime(frame["ann_date"], errors="coerce").dt.normalize()
    frame["unit_nav"] = pd.to_numeric(frame["unit_nav"], errors="coerce")
    for column in _OPTIONAL_NUMERIC_COLUMNS:
        if column not in frame.columns:
            frame[column] = np.nan
        else:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    if start_date is not None:
        start = pd.Timestamp(start_date).normalize()
        frame = frame.loc[frame["nav_date"] >= start].copy()
    if end_date is not None:
        end = pd.Timestamp(end_date).normalize()
        frame = frame.loc[frame["nav_date"] <= end].copy()
    if frame.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    selected_rows = []
    for _, group in frame.groupby(["symbol", "nav_date"], sort=True, dropna=False):
        selected_rows.append(_select_revision(group).iloc[0].to_dict())
    selected = pd.DataFrame(selected_rows)
    selected["exchange"] = selected["symbol"].map(
        lambda value: "XSHG" if value.endswith(".SH") else "XSHE"
    )
    selected["asset_id"] = selected.apply(
        lambda row: f"CN_ETF_{row['exchange']}_{row['symbol'].split('.')[0]}",
        axis=1,
    )

    known_from: list[pd.Timestamp | pd.NaT] = []
    pit_usable: list[bool] = []
    for row in selected.itertuples(index=False):
        valid_lag = pd.notna(row.ann_date) and row.ann_date >= row.nav_date
        next_session: pd.Timestamp | pd.NaT = pd.NaT
        if valid_lag:
            cutoff = max(row.nav_date, row.ann_date)
            position = sessions.searchsorted(cutoff, side="right")
            if position < len(sessions):
                next_session = sessions[position]
        positive_nav = bool(np.isfinite(row.unit_nav) and row.unit_nav > 0.0)
        known_from.append(next_session)
        pit_usable.append(bool(valid_lag and pd.notna(next_session) and positive_nav))
    selected["known_from"] = known_from
    selected["is_pit_usable"] = pit_usable
    selected["source"] = source

    for column in ["nav_date", "ann_date", "known_from"]:
        selected[column] = pd.to_datetime(selected[column], errors="coerce").dt.date
    result = selected[CANONICAL_COLUMNS].sort_values(["asset_id", "nav_date"]).reset_index(drop=True)
    if result.duplicated(["asset_id", "nav_date"]).any():
        raise ValueError("canonical Tushare fund NAV contains duplicate asset-date rows")
    return result


def _select_revision(group: pd.DataFrame) -> pd.DataFrame:
    working = group.copy()
    announcement_rank = working["ann_date"].fillna(pd.Timestamp.min)
    latest_announcement = announcement_rank.max()
    candidates = working.loc[announcement_rank == latest_announcement].copy()
    update_rank = candidates["update_flag"].fillna(float("-inf"))
    highest_update = update_rank.max()
    candidates = candidates.loc[update_rank == highest_update].copy()
    if len(candidates) > 1:
        comparison = candidates[_CONFLICT_VALUE_COLUMNS].copy()
        first = comparison.iloc[0]
        same = comparison.apply(lambda row: _values_equal(row, first), axis=1)
        if not bool(same.all()):
            symbol = str(candidates["symbol"].iloc[0])
            nav_date = pd.Timestamp(candidates["nav_date"].iloc[0]).date().isoformat()
            raise ValueError(f"conflicting NAV revisions for {symbol} on {nav_date}")
    return candidates.iloc[[0]]


def _values_equal(left: pd.Series, right: pd.Series) -> bool:
    for column in _CONFLICT_VALUE_COLUMNS:
        left_value = left[column]
        right_value = right[column]
        if pd.isna(left_value) and pd.isna(right_value):
            continue
        if left_value != right_value:
            return False
    return True


def _as_date(value: object, label: str):
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"{label} is not a valid date")
    return parsed.date()


def _as_optional_date(value: object, label: str):
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    return _as_date(value, label)
