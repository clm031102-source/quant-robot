from __future__ import annotations

import math
from typing import Any

import pandas as pd


STAGE = "cn_etf_pcf_delivery_contract_review"
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


__all__ = [
    "CANONICAL_COLUMNS",
    "KEY_COLUMNS",
    "STAGE",
    "audit_cn_etf_pcf_delivery",
    "normalize_cn_etf_pcf_delivery",
]
