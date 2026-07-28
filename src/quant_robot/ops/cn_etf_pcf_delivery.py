from __future__ import annotations

import math
from typing import Any

import pandas as pd


STAGE = "cn_etf_pcf_delivery_contract_review"
READINESS_STAGE = "cn_etf_pcf_source_readiness"
CANONICAL_COLUMNS = (
    "trade_date",
    "available_date",
    "etf_code",
    "constituent_code",
    "constituent_name",
    "market_exchange",
    "constituent_exchange",
    "quantity",
    "substitution_flag",
    "subscription_rate_pct",
    "redemption_rate_pct",
    "cash_substitution_amount_cny",
    "subscription_cash_amount_cny",
    "redemption_cash_amount_cny",
    "availability_basis",
    "earliest_research_use_session_offset",
    "same_session_factor_use_allowed",
    "source_provider",
    "source_file",
)
KEY_COLUMNS = ("trade_date", "etf_code", "constituent_code")
TARGET_UNIVERSE_COLUMNS = (
    "etf_code",
    "market_exchange",
    "list_date",
    "delist_date",
)


def normalize_cn_etf_pcf_delivery(
    frame: pd.DataFrame,
    *,
    market_exchange: str,
    source_provider: str,
    source_file: str,
) -> pd.DataFrame:
    exchange = market_exchange.upper()
    if exchange not in {"SSE", "SZSE"}:
        raise ValueError("market_exchange must be SSE or SZSE")
    if frame.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)
    required = {
        "trade_date": _column(frame, "trade_date"),
        "etf_code": _column(frame, "etf_code", "ts_code"),
        "constituent_code": _column(frame, "constituent_code", "con_code"),
        "quantity": _column(frame, "quantity", "qty"),
        "substitution_flag": _column(frame, "substitution_flag", "sub_flag"),
    }
    missing = sorted(name for name, column in required.items() if column is None)
    if missing:
        raise ValueError(f"PCF delivery is missing required fields: {', '.join(missing)}")
    trade_date = pd.to_datetime(
        frame[required["trade_date"]],
        format="%Y%m%d",
        errors="coerce",
    )
    if trade_date.isna().any():
        fallback = pd.to_datetime(frame[required["trade_date"]], errors="coerce")
        trade_date = trade_date.fillna(fallback)
    if trade_date.isna().any():
        raise ValueError("PCF delivery contains invalid trade_date values")
    quantity = pd.to_numeric(frame[required["quantity"]], errors="coerce")
    if (
        quantity.isna().any()
        or (~quantity.map(math.isfinite)).any()
        or quantity.lt(0).any()
    ):
        raise ValueError("PCF delivery quantity must be finite and nonnegative")
    etf_code = frame[required["etf_code"]].astype("string").str.strip()
    suffix = ".SH" if exchange == "SSE" else ".SZ"
    if etf_code.isna().any() or (~etf_code.str.upper().str.endswith(suffix)).any():
        raise ValueError(f"PCF ETF codes do not match {exchange}")
    output = pd.DataFrame(
        {
            "trade_date": trade_date.dt.normalize(),
            "available_date": trade_date.dt.normalize(),
            "etf_code": etf_code.str.upper(),
            "constituent_code": frame[required["constituent_code"]]
            .astype("string")
            .str.strip()
            .str.upper(),
            "constituent_name": _text(frame, "constituent_name", "con_name"),
            "market_exchange": exchange,
            "constituent_exchange": _text(frame, "constituent_exchange", "exchange"),
            "quantity": quantity.astype(float),
            "substitution_flag": frame[required["substitution_flag"]]
            .astype("string")
            .str.strip(),
            "subscription_rate_pct": _numeric(frame, "subscription_rate_pct", "cpr"),
            "redemption_rate_pct": _numeric(frame, "redemption_rate_pct", "rdr"),
            "cash_substitution_amount_cny": _numeric(
                frame,
                "cash_substitution_amount_cny",
                "sca",
            ),
            "subscription_cash_amount_cny": _numeric(
                frame,
                "subscription_cash_amount_cny",
                "sub_cc",
            ),
            "redemption_cash_amount_cny": _numeric(
                frame,
                "redemption_cash_amount_cny",
                "red_cc",
            ),
            "availability_basis": "official_pre_open_daily_pcf",
            "earliest_research_use_session_offset": 1,
            "same_session_factor_use_allowed": False,
            "source_provider": str(source_provider),
            "source_file": str(source_file),
        }
    )
    if output["constituent_code"].isna().any() or output["constituent_code"].eq("").any():
        raise ValueError("PCF delivery contains missing constituent codes")
    duplicate = output.duplicated(list(KEY_COLUMNS), keep=False)
    if duplicate.any():
        raise ValueError(
            f"PCF delivery contains duplicate date/ETF/constituent keys: {int(duplicate.sum())}"
        )
    return (
        output.loc[:, CANONICAL_COLUMNS]
        .sort_values(list(KEY_COLUMNS), kind="stable")
        .reset_index(drop=True)
    )


def audit_cn_etf_pcf_delivery(
    frame: pd.DataFrame,
    *,
    analysis_start: str,
    analysis_end: str,
) -> dict[str, Any]:
    missing = sorted(set(CANONICAL_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"canonical PCF delivery is missing columns: {', '.join(missing)}")
    start = pd.Timestamp(analysis_start)
    end = pd.Timestamp(analysis_end)
    if start > end:
        raise ValueError("analysis_start must not exceed analysis_end")
    dates = pd.to_datetime(frame["trade_date"], errors="coerce")
    outside = dates.notna() & ~dates.between(start, end)
    blockers: list[str] = []
    if frame.empty:
        blockers.append("delivery_empty")
    if dates.isna().any():
        blockers.append("invalid_trade_dates")
    if outside.any():
        blockers.append("rows_outside_frozen_analysis_window")
    status = (
        "blocked_delivery_outside_frozen_window"
        if outside.any()
        else "blocked_empty_delivery"
        if frame.empty
        else "delivery_structurally_valid_source_readiness_required"
    )
    return {
        "stage": STAGE,
        "status": status,
        "analysis_start": start.date().isoformat(),
        "analysis_end": end.date().isoformat(),
        "rows": int(len(frame)),
        "dates": int(dates.nunique()),
        "etfs": int(frame["etf_code"].nunique()) if not frame.empty else 0,
        "constituents": int(frame["constituent_code"].nunique()) if not frame.empty else 0,
        "outside_window_rows": int(outside.sum()),
        "missing_subscription_rate_rows": int(frame["subscription_rate_pct"].isna().sum()),
        "missing_redemption_rate_rows": int(frame["redemption_rate_pct"].isna().sum()),
        "blockers": blockers,
        "decision": {
            "delivery_structurally_valid": not blockers,
            "source_ready": False,
            "full_history_coverage_audit_required": True,
            "calendar_alignment_audit_required": True,
            "source_fingerprint_required": True,
            "factor_generation_allowed": False,
            "forward_return_read_allowed": False,
            "portfolio_grid_allowed": False,
            "final_holdout_allowed": False,
            "paper_signal_allowed": False,
            "live_boundary_allowed": False,
        },
    }


def normalize_cn_etf_pcf_target_universe(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=TARGET_UNIVERSE_COLUMNS)
    source = frame.copy()
    if "is_etf" in source.columns:
        is_etf = (
            source["is_etf"]
            .astype("string")
            .str.strip()
            .str.lower()
            .isin({"1", "true", "yes", "y"})
        )
        source = source.loc[is_etf].copy()
    code_column = _column(source, "etf_code", "symbol", "ts_code")
    if code_column is None:
        raise ValueError("PCF target universe is missing etf_code/symbol/ts_code")
    if "list_date" not in source.columns:
        raise ValueError("PCF target universe is missing list_date")
    etf_code = source[code_column].astype("string").str.strip().str.upper()
    invalid_code = (
        etf_code.isna()
        | etf_code.eq("")
        | ~etf_code.str.endswith((".SH", ".SZ"), na=False)
    )
    if invalid_code.any():
        raise ValueError("PCF target universe contains invalid ETF codes")
    list_date = _dates(source["list_date"])
    if list_date.isna().any():
        raise ValueError("PCF target universe contains missing or invalid list_date values")
    if "delist_date" in source.columns:
        delist_date = _dates(source["delist_date"])
    else:
        delist_date = pd.Series(pd.NaT, index=source.index, dtype="datetime64[ns]")
    invalid_delist = delist_date.notna() & delist_date.lt(list_date)
    if invalid_delist.any():
        raise ValueError("PCF target universe delist_date precedes list_date")
    result = pd.DataFrame(
        {
            "etf_code": etf_code,
            "market_exchange": etf_code.map(
                lambda value: "SSE" if str(value).endswith(".SH") else "SZSE"
            ),
            "list_date": list_date.dt.normalize(),
            "delist_date": delist_date.dt.normalize(),
        }
    )
    if result["etf_code"].duplicated().any():
        raise ValueError("PCF target universe contains duplicate ETF codes")
    return (
        result.loc[:, TARGET_UNIVERSE_COLUMNS]
        .sort_values("etf_code", kind="stable")
        .reset_index(drop=True)
    )


def audit_cn_etf_pcf_history(
    frame: pd.DataFrame,
    *,
    target_universe: pd.DataFrame,
    trading_sessions: list[str] | tuple[str, ...],
    analysis_start: str,
    analysis_end: str,
    final_holdout_start: str,
    minimum_target_etfs: int,
    required_market_exchanges: tuple[str, ...] = ("SSE", "SZSE"),
) -> dict[str, Any]:
    missing_columns = sorted(set(CANONICAL_COLUMNS) - set(frame.columns))
    if missing_columns:
        raise ValueError(
            "canonical PCF history is missing columns: " + ", ".join(missing_columns)
        )
    if minimum_target_etfs < 1:
        raise ValueError("minimum_target_etfs must be positive")
    required_exchanges = tuple(str(value).upper() for value in required_market_exchanges)
    if not required_exchanges or not set(required_exchanges).issubset({"SSE", "SZSE"}):
        raise ValueError("required_market_exchanges must contain SSE and/or SZSE")

    start = pd.Timestamp(analysis_start).normalize()
    end = pd.Timestamp(analysis_end).normalize()
    holdout = pd.Timestamp(final_holdout_start).normalize()
    if not start <= end < holdout:
        raise ValueError("analysis and final-holdout dates are inconsistent")
    sessions = pd.DatetimeIndex(pd.to_datetime(list(trading_sessions))).normalize()
    if sessions.has_duplicates:
        raise ValueError("trading_sessions contains duplicate dates")
    sessions = sessions.sort_values()
    sessions = sessions[(sessions >= start) & (sessions <= end)]
    if sessions.empty:
        raise ValueError("trading_sessions does not cover the analysis window")

    targets = normalize_cn_etf_pcf_target_universe(target_universe)
    targets = targets[
        targets["list_date"].le(end)
        & (targets["delist_date"].isna() | targets["delist_date"].ge(start))
    ].reset_index(drop=True)
    expected_records: list[tuple[str, pd.Timestamp, str]] = []
    for row in targets.itertuples(index=False):
        active = sessions[
            (sessions >= row.list_date)
            & (pd.isna(row.delist_date) | (sessions <= row.delist_date))
        ]
        expected_records.extend(
            (row.etf_code, session, row.market_exchange) for session in active
        )
    expected = pd.DataFrame(
        expected_records,
        columns=["etf_code", "trade_date", "market_exchange"],
    )
    expected_pairs = pd.MultiIndex.from_frame(
        expected[["etf_code", "trade_date"]]
    )

    source = frame.copy()
    source["trade_date"] = pd.to_datetime(
        source["trade_date"],
        errors="coerce",
    ).dt.normalize()
    source["available_date"] = pd.to_datetime(
        source["available_date"],
        errors="coerce",
    ).dt.normalize()
    source["etf_code"] = source["etf_code"].astype("string").str.upper().str.strip()
    invalid_date_rows = int(
        (source["trade_date"].isna() | source["available_date"].isna()).sum()
    )
    duplicate_rows = int(source.duplicated(list(KEY_COLUMNS), keep=False).sum())
    point_in_time_ok = (
        source["available_date"].eq(source["trade_date"]).fillna(False)
        & source["availability_basis"].eq("official_pre_open_daily_pcf").fillna(False)
        & pd.to_numeric(
            source["earliest_research_use_session_offset"],
            errors="coerce",
        )
        .eq(1)
        .fillna(False)
        & source["same_session_factor_use_allowed"].eq(False).fillna(False)
    )
    point_in_time_mismatch_rows = int((~point_in_time_ok).sum())
    outside_window = ~source["trade_date"].between(start, end, inclusive="both")
    outside_window_rows = int(outside_window.fillna(True).sum())
    final_holdout_rows = int(
        (
            source["trade_date"].ge(holdout)
            | source["available_date"].ge(holdout)
        )
        .fillna(False)
        .sum()
    )
    official_session_rows = source["trade_date"].isin(sessions)
    non_session_rows = int((~official_session_rows).sum())
    target_codes = set(targets["etf_code"].astype(str))
    out_of_target_rows = int((~source["etf_code"].isin(target_codes)).sum())

    observed = (
        source.loc[
            source["trade_date"].between(start, end, inclusive="both")
            & source["trade_date"].isin(sessions)
            & source["etf_code"].isin(target_codes),
            ["etf_code", "trade_date"],
        ]
        .drop_duplicates()
        .sort_values(["etf_code", "trade_date"], kind="stable")
        .reset_index(drop=True)
    )
    observed_pairs = pd.MultiIndex.from_frame(observed)
    missing_pairs = expected_pairs.difference(observed_pairs)
    unexpected_pairs = observed_pairs.difference(expected_pairs)
    observed_expected_pairs = observed_pairs.intersection(expected_pairs)
    expected_count = int(len(expected_pairs))
    observed_count = int(len(observed_expected_pairs))
    coverage_ratio = float(observed_count / expected_count) if expected_count else 0.0

    etf_coverage = _coverage_rows(
        expected,
        observed,
        group_column="etf_code",
        all_values=targets["etf_code"].astype(str).tolist(),
    )
    date_coverage = _coverage_rows(
        expected.rename(columns={"trade_date": "date"}),
        observed.rename(columns={"trade_date": "date"}),
        group_column="date",
        all_values=[value.strftime("%Y-%m-%d") for value in sessions],
    )
    exchange_expected = expected[["etf_code", "trade_date", "market_exchange"]]
    exchange_observed = observed.merge(
        targets[["etf_code", "market_exchange"]],
        on="etf_code",
        how="left",
        validate="many_to_one",
    )
    exchange_coverage = _coverage_rows(
        exchange_expected,
        exchange_observed,
        group_column="market_exchange",
        all_values=list(required_exchanges),
    )

    blockers: list[str] = []
    target_exchange_set = set(targets["market_exchange"].astype(str))
    if len(targets) < minimum_target_etfs:
        blockers.append("target_etf_count_below_minimum")
    if not set(required_exchanges).issubset(target_exchange_set):
        blockers.append("required_market_exchange_missing_from_target_universe")
    if expected_count == 0:
        blockers.append("expected_target_history_empty")
    if frame.empty:
        blockers.append("pcf_history_empty")
    if invalid_date_rows:
        blockers.append("invalid_pcf_dates")
    if duplicate_rows:
        blockers.append("duplicate_pcf_keys")
    if point_in_time_mismatch_rows:
        blockers.append("point_in_time_contract_mismatch")
    if outside_window_rows:
        blockers.append("pcf_rows_outside_analysis_window")
    if final_holdout_rows:
        blockers.append("final_holdout_rows_present")
    if non_session_rows:
        blockers.append("pcf_rows_on_non_session_dates")
    if out_of_target_rows:
        blockers.append("pcf_rows_outside_target_universe")
    if len(unexpected_pairs):
        blockers.append("pcf_rows_outside_target_active_window")
    if len(missing_pairs):
        blockers.append("missing_target_etf_sessions")

    cleared = not blockers
    return {
        "stage": READINESS_STAGE,
        "status": "ready_for_pcf_source_preregistration" if cleared else "blocked",
        "primary_market": "CN_ETF",
        "analysis": {
            "start_date": start.date().isoformat(),
            "end_date": end.date().isoformat(),
            "final_holdout_start": holdout.date().isoformat(),
        },
        "thresholds": {
            "minimum_target_etfs": int(minimum_target_etfs),
            "required_market_exchanges": list(required_exchanges),
            "required_etf_session_coverage_ratio": 1.0,
        },
        "summary": {
            "pcf_rows": int(len(source)),
            "target_etfs": int(len(targets)),
            "analysis_sessions": int(len(sessions)),
            "expected_etf_sessions": expected_count,
            "observed_etf_sessions": observed_count,
            "missing_etf_sessions": int(len(missing_pairs)),
            "unexpected_etf_sessions": int(len(unexpected_pairs)),
            "coverage_ratio": coverage_ratio,
        },
        "integrity": {
            "invalid_date_rows": invalid_date_rows,
            "duplicate_key_rows": duplicate_rows,
            "point_in_time_mismatch_rows": point_in_time_mismatch_rows,
            "outside_window_rows": outside_window_rows,
            "final_holdout_rows": final_holdout_rows,
            "non_session_rows": non_session_rows,
            "out_of_target_rows": out_of_target_rows,
        },
        "missing_etf_session_sample": [
            {
                "etf_code": str(etf_code),
                "trade_date": pd.Timestamp(trade_date).date().isoformat(),
            }
            for etf_code, trade_date in list(missing_pairs)[:100]
        ],
        "etf_coverage": etf_coverage,
        "date_coverage": date_coverage,
        "exchange_coverage": exchange_coverage,
        "gate": {
            "cleared": cleared,
            "blockers": blockers,
        },
        "decision": {
            "delivery_structurally_valid": not any(
                blocker
                in {
                    "invalid_pcf_dates",
                    "duplicate_pcf_keys",
                    "point_in_time_contract_mismatch",
                    "pcf_rows_outside_analysis_window",
                    "final_holdout_rows_present",
                    "pcf_rows_on_non_session_dates",
                    "pcf_rows_outside_target_universe",
                    "pcf_rows_outside_target_active_window",
                }
                for blocker in blockers
            ),
            "source_ready": cleared,
            "full_history_coverage_audited": True,
            "calendar_alignment_audited": True,
            "factor_generation_allowed": False,
            "forward_return_read_allowed": False,
            "portfolio_grid_allowed": False,
            "final_holdout_allowed": False,
            "paper_signal_allowed": False,
            "live_boundary_allowed": False,
        },
        "next_direction": (
            "preregister_one_compact_pcf_factor_family"
            if cleared
            else "repair_pcf_delivery_or_target_universe"
        ),
    }


def _column(frame: pd.DataFrame, *names: str) -> str | None:
    return next((name for name in names if name in frame.columns), None)


def _text(frame: pd.DataFrame, *names: str) -> pd.Series:
    column = _column(frame, *names)
    if column is None:
        return pd.Series(pd.NA, index=frame.index, dtype="string")
    return frame[column].astype("string").str.strip()


def _numeric(frame: pd.DataFrame, *names: str) -> pd.Series:
    column = _column(frame, *names)
    if column is None:
        return pd.Series(float("nan"), index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _dates(values: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(values, format="%Y%m%d", errors="coerce")
    fallback = pd.to_datetime(values, errors="coerce")
    return parsed.fillna(fallback)


def _coverage_rows(
    expected: pd.DataFrame,
    observed: pd.DataFrame,
    *,
    group_column: str,
    all_values: list[Any],
) -> list[dict[str, Any]]:
    expected_counts = expected.groupby(group_column, sort=True).size()
    observed_counts = observed.groupby(group_column, sort=True).size()
    rows: list[dict[str, Any]] = []
    for raw_value in all_values:
        lookup = pd.Timestamp(raw_value) if group_column == "date" else raw_value
        expected_count = int(expected_counts.get(lookup, 0))
        observed_count = int(observed_counts.get(lookup, 0))
        value = (
            lookup.date().isoformat()
            if group_column == "date"
            else str(raw_value)
        )
        rows.append(
            {
                group_column: value,
                "expected_etf_sessions": expected_count,
                "observed_etf_sessions": observed_count,
                "missing_etf_sessions": max(expected_count - observed_count, 0),
                "coverage_ratio": (
                    float(observed_count / expected_count)
                    if expected_count
                    else 0.0
                ),
            }
        )
    return rows


__all__ = [
    "CANONICAL_COLUMNS",
    "KEY_COLUMNS",
    "READINESS_STAGE",
    "STAGE",
    "TARGET_UNIVERSE_COLUMNS",
    "audit_cn_etf_pcf_history",
    "audit_cn_etf_pcf_delivery",
    "normalize_cn_etf_pcf_delivery",
    "normalize_cn_etf_pcf_target_universe",
]
