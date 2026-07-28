from __future__ import annotations

from typing import Any

import pandas as pd

from quant_robot.ops.cn_etf_pcf_delivery import (
    TARGET_UNIVERSE_COLUMNS,
    normalize_cn_etf_pcf_target_universe,
)


STAGE = "cn_etf_pcf_target_universe"


def build_cn_etf_pcf_target_universe(
    *,
    fund_basic: pd.DataFrame,
    bars: pd.DataFrame,
    analysis_start: str,
    analysis_end: str,
    minimum_target_etfs: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    required_fund = {"symbol", "is_etf", "status", "list_date", "delist_date"}
    missing_fund = sorted(required_fund - set(fund_basic.columns))
    if missing_fund:
        raise ValueError(
            "fund_basic is missing columns: " + ", ".join(missing_fund)
        )
    required_bars = {"symbol", "date"}
    missing_bars = sorted(required_bars - set(bars.columns))
    if missing_bars:
        raise ValueError("bars are missing columns: " + ", ".join(missing_bars))
    if minimum_target_etfs < 1:
        raise ValueError("minimum_target_etfs must be positive")
    start = pd.Timestamp(analysis_start).normalize()
    end = pd.Timestamp(analysis_end).normalize()
    if start > end:
        raise ValueError("analysis_start must not exceed analysis_end")

    fund = fund_basic.copy()
    fund["symbol"] = fund["symbol"].astype("string").str.strip().str.upper()
    if fund["symbol"].duplicated().any():
        raise ValueError("fund_basic contains duplicate symbols")
    is_etf = (
        fund["is_etf"]
        .astype("string")
        .str.strip()
        .str.lower()
        .isin({"1", "true", "yes", "y"})
    )
    fund = fund.loc[is_etf].copy()
    fund["list_date"] = pd.to_datetime(
        fund["list_date"],
        errors="coerce",
    ).dt.normalize()
    fund["delist_date"] = pd.to_datetime(
        fund["delist_date"],
        errors="coerce",
    ).dt.normalize()
    fund["status"] = fund["status"].astype("string").str.strip().str.upper()

    bar_frame = bars[["symbol", "date"]].copy()
    bar_frame["symbol"] = (
        bar_frame["symbol"].astype("string").str.strip().str.upper()
    )
    bar_frame["date"] = pd.to_datetime(
        bar_frame["date"],
        errors="coerce",
    ).dt.normalize()
    if bar_frame["date"].isna().any():
        raise ValueError("bars contains invalid dates")
    bar_frame = bar_frame[bar_frame["date"].between(start, end, inclusive="both")]
    bar_symbols = set(bar_frame["symbol"].dropna().astype(str))

    missing_list = fund["list_date"].isna()
    missing_list_symbols = set(fund.loc[missing_list, "symbol"].astype(str))
    missing_with_bars = sorted(missing_list_symbols & bar_symbols)
    missing_without_bars = sorted(missing_list_symbols - bar_symbols)
    invalid_delist = (
        fund["delist_date"].notna()
        & fund["list_date"].notna()
        & fund["delist_date"].lt(fund["list_date"])
    )

    eligible = fund[
        fund["list_date"].notna()
        & fund["list_date"].le(end)
        & (fund["delist_date"].isna() | fund["delist_date"].ge(start))
    ].copy()
    target = normalize_cn_etf_pcf_target_universe(
        eligible[["symbol", "list_date", "delist_date"]]
    )

    statuses = set(fund["status"].dropna().astype(str))
    blockers: list[str] = []
    if not (statuses - {"", "L"}):
        blockers.append("current_active_only_fund_snapshot")
    if invalid_delist.any():
        blockers.append("fund_snapshot_delist_date_precedes_list_date")
    if missing_with_bars:
        blockers.append("missing_list_date_for_bar_observed_etf")
    if len(target) < minimum_target_etfs:
        blockers.append("target_etf_count_below_minimum")
    if not {"SSE", "SZSE"}.issubset(set(target["market_exchange"].astype(str))):
        blockers.append("target_universe_missing_exchange")

    cleared = not blockers
    result = {
        "stage": STAGE,
        "status": "ready" if cleared else "blocked",
        "primary_market": "CN_ETF",
        "analysis": {
            "start_date": start.date().isoformat(),
            "end_date": end.date().isoformat(),
        },
        "thresholds": {
            "minimum_target_etfs": int(minimum_target_etfs),
            "required_market_exchanges": ["SSE", "SZSE"],
            "requires_non_active_status_evidence": True,
        },
        "summary": {
            "fund_rows": int(len(fund_basic)),
            "classified_etf_rows": int(len(fund)),
            "target_etfs": int(len(target)),
            "sse_target_etfs": int(target["market_exchange"].eq("SSE").sum()),
            "szse_target_etfs": int(target["market_exchange"].eq("SZSE").sum()),
            "delisted_target_etfs": int(target["delist_date"].notna().sum()),
            "analysis_bar_symbols": int(len(bar_symbols)),
        },
        "integrity": {
            "fund_statuses": sorted(statuses),
            "invalid_delist_rows": int(invalid_delist.sum()),
            "missing_list_date_rows": int(missing_list.sum()),
            "missing_list_date_with_bar_rows": int(len(missing_with_bars)),
            "missing_list_date_without_bar_rows": int(len(missing_without_bars)),
            "missing_list_date_with_bar_symbols": missing_with_bars[:100],
        },
        "canonical_columns": list(TARGET_UNIVERSE_COLUMNS),
        "gate": {
            "cleared": cleared,
            "blockers": blockers,
        },
        "decision": {
            "target_universe_ready": cleared,
            "survivorship_review_passed": (
                "current_active_only_fund_snapshot" not in blockers
            ),
            "factor_generation_allowed": False,
            "forward_return_read_allowed": False,
            "portfolio_grid_allowed": False,
            "final_holdout_allowed": False,
            "paper_signal_allowed": False,
            "live_boundary_allowed": False,
        },
        "next_direction": (
            "use_frozen_target_for_pcf_delivery_coverage_audit"
            if cleared
            else "repair_historical_etf_target_universe"
        ),
    }
    return target, result


__all__ = [
    "STAGE",
    "build_cn_etf_pcf_target_universe",
]
