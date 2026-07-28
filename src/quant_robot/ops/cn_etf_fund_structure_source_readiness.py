from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from quant_robot.storage.atomic import atomic_write, atomic_write_json, atomic_write_text


STAGE = "cn_etf_fund_structure_source_readiness"
STATUS_READY = "ready_for_fund_structure_preregistration"

BOUNDARY_KEYS = (
    "factor_generation_allowed",
    "forward_return_read",
    "portfolio_grid_allowed",
    "walk_forward_allowed",
    "final_holdout_allowed",
    "promotion_allowed",
    "paper_signal_allowed",
    "broker_connection_allowed",
    "account_read_allowed",
    "order_placement_allowed",
    "live_boundary_allowed",
)


def build_cn_etf_fund_structure_source_readiness(
    *,
    config: dict[str, Any],
    processed: pd.DataFrame,
    bars: pd.DataFrame,
    request_manifest: dict[str, Any],
    configuration_sha256: str,
) -> dict[str, Any]:
    analysis = dict(config["analysis"])
    thresholds = dict(config["thresholds"])
    boundaries = dict(config["boundaries"])
    start = pd.to_datetime(analysis["start_date"]).date()
    end = pd.to_datetime(analysis["end_date"]).date()
    holdout_start = pd.to_datetime(analysis["final_holdout_start"]).date()

    bar_frame = _normalize_bars(bars, start=start, end=end)
    source_frame = _normalize_processed(processed)
    date_rows, exchange_metrics = _coverage_rows(
        processed=source_frame,
        bars=bar_frame,
        thresholds=thresholds,
    )
    analysis_sessions = sorted(bar_frame["date"].unique())
    combined_qualifying_dates = int(date_rows["combined_qualifies"].sum()) if not date_rows.empty else 0
    combined_coverage = _ratio(combined_qualifying_dates, len(analysis_sessions))
    qualifying_fractions = date_rows.loc[
        date_rows["combined_qualifies"], "share_asset_coverage"
    ]
    median_share_coverage = (
        float(qualifying_fractions.median()) if not qualifying_fractions.empty else 0.0
    )

    rows = len(source_frame)
    positive_share_rows = int(
        (pd.to_numeric(source_frame.get("total_share"), errors="coerce") > 0.0).sum()
    )
    nav_values = pd.to_numeric(source_frame.get("nav"), errors="coerce")
    retained_nav_rows = int(nav_values.notna().sum())
    positive_nav_rows = int((nav_values > 0.0).sum())
    positive_share_ratio = _ratio(positive_share_rows, rows)
    positive_nav_ratio = _ratio(positive_nav_rows, retained_nav_rows)
    nav_intersection_coverage = _ratio(positive_nav_rows, rows)

    processed_dates = pd.to_datetime(source_frame.get("date"), errors="coerce").dt.date
    known_from = pd.to_datetime(source_frame.get("known_from"), errors="coerce").dt.date
    duplicate_rows = (
        int(source_frame.duplicated(["asset_id", "date"]).sum())
        if {"asset_id", "date"}.issubset(source_frame.columns)
        else rows
    )
    outside_window_rows = int((~processed_dates.between(start, end)).sum())
    holdout_rows = int((processed_dates >= holdout_start).sum())
    pit_violations = int(
        (
            processed_dates.isna()
            | known_from.isna()
            | (pd.to_datetime(known_from) <= pd.to_datetime(processed_dates))
        ).sum()
    )
    official_share_failures = _official_share_failures(request_manifest)
    unapproved_close_source_rows = int(
        source_frame["close_source"].ne("tushare_fund_daily").sum()
    )
    unapproved_share_source_rows = int(
        (
            ~source_frame["share_source"].isin(
                {"sse_official_etf_scale", "szse_official_fund_scale"}
            )
        ).sum()
    )
    unapproved_nav_source_rows = int(
        (
            nav_values.notna()
            & source_frame["nav_source"].ne("eastmoney_fund_detail_history")
        ).sum()
    )
    numeric_share = pd.to_numeric(source_frame["total_share"], errors="coerce")
    numeric_close = pd.to_numeric(source_frame["close"], errors="coerce")
    numeric_size = pd.to_numeric(source_frame["total_size"], errors="coerce")
    numeric_premium = pd.to_numeric(source_frame["nav_premium_discount"], errors="coerce")
    derived_eligible = (
        numeric_share.gt(0.0)
        & nav_values.gt(0.0)
        & numeric_close.gt(0.0)
    )
    expected_size = numeric_share * nav_values
    expected_premium = numeric_close / nav_values - 1.0
    size_matches = np.isclose(
        numeric_size.to_numpy(dtype=float, na_value=np.nan),
        expected_size.to_numpy(dtype=float, na_value=np.nan),
        rtol=1e-10,
        atol=1e-12,
        equal_nan=False,
    )
    premium_matches = np.isclose(
        numeric_premium.to_numpy(dtype=float, na_value=np.nan),
        expected_premium.to_numpy(dtype=float, na_value=np.nan),
        rtol=1e-10,
        atol=1e-12,
        equal_nan=False,
    )
    derived_total_size_mismatch_rows = int(
        (derived_eligible & ~pd.Series(size_matches, index=source_frame.index)).sum()
    )
    derived_premium_mismatch_rows = int(
        (derived_eligible & ~pd.Series(premium_matches, index=source_frame.index)).sum()
    )

    blockers: list[str] = []
    if duplicate_rows:
        blockers.append("duplicate_processed_asset_date_rows")
    if outside_window_rows:
        blockers.append("processed_rows_outside_frozen_analysis_window")
    if holdout_rows:
        blockers.append("final_holdout_rows_present")
    if pit_violations:
        blockers.append("known_from_not_after_observation_date")
    if official_share_failures:
        blockers.append("official_share_requests_incomplete")
    if unapproved_close_source_rows:
        blockers.append("unapproved_close_source_rows")
    if unapproved_share_source_rows:
        blockers.append("unapproved_share_source_rows")
    if unapproved_nav_source_rows:
        blockers.append("unapproved_nav_source_rows")
    if derived_total_size_mismatch_rows:
        blockers.append("derived_total_size_mismatch_rows")
    if derived_premium_mismatch_rows:
        blockers.append("derived_premium_discount_mismatch_rows")
    if combined_coverage < float(thresholds["minimum_combined_date_coverage"]):
        blockers.append("combined_share_date_coverage_below_minimum")
    for exchange, prefix in (("SSE", "sse"), ("SZSE", "szse")):
        if exchange_metrics[exchange]["date_coverage"] < float(
            thresholds["minimum_exchange_date_coverage"]
        ):
            blockers.append(f"{prefix}_share_date_coverage_below_minimum")
    if median_share_coverage < float(thresholds["minimum_median_share_asset_coverage"]):
        blockers.append("median_share_asset_coverage_below_minimum")
    if nav_intersection_coverage < float(thresholds["minimum_nav_intersection_coverage"]):
        blockers.append("nav_intersection_coverage_below_minimum")
    if positive_share_ratio < float(thresholds["minimum_positive_share_ratio"]):
        blockers.append("positive_share_ratio_below_minimum")
    if positive_nav_ratio < float(thresholds["minimum_positive_nav_ratio"]):
        blockers.append("positive_nav_ratio_below_minimum")
    for key in BOUNDARY_KEYS:
        if boundaries.get(key) is not False:
            blockers.append(f"boundary_enabled:{key}")
    blockers = list(dict.fromkeys(blockers))

    status = "blocked" if blockers else STATUS_READY
    result = {
        "stage": STAGE,
        "review_date": config["review_date"],
        "status": status,
        "primary_market": "CN_ETF",
        "research_family": "cn_etf_fund_structure",
        "configuration": {"sha256": configuration_sha256},
        "analysis": analysis,
        "thresholds": thresholds,
        "gate": {
            "cleared": not blockers,
            "blockers": blockers,
        },
        "summary": {
            "analysis_sessions": len(analysis_sessions),
            "bar_assets": int(bar_frame["asset_id"].nunique()) if not bar_frame.empty else 0,
            "bar_rows": int(len(bar_frame)),
            "share_assets": int(source_frame["asset_id"].nunique()) if not source_frame.empty else 0,
            "share_rows": rows,
            "nav_rows": retained_nav_rows,
            "positive_nav_rows": positive_nav_rows,
            "duplicate_rows": duplicate_rows,
            "outside_window_rows": outside_window_rows,
            "holdout_rows": holdout_rows,
            "pit_violations": pit_violations,
            "official_share_request_failures": official_share_failures,
            "unapproved_close_source_rows": unapproved_close_source_rows,
            "unapproved_share_source_rows": unapproved_share_source_rows,
            "unapproved_nav_source_rows": unapproved_nav_source_rows,
            "derived_total_size_mismatch_rows": derived_total_size_mismatch_rows,
            "derived_premium_discount_mismatch_rows": derived_premium_mismatch_rows,
        },
        "coverage": {
            "combined_qualifying_dates": combined_qualifying_dates,
            "combined_qualifying_date_coverage": combined_coverage,
            "median_share_asset_coverage": median_share_coverage,
            "nav_intersection_coverage": nav_intersection_coverage,
            "positive_share_ratio": positive_share_ratio,
            "positive_nav_ratio": positive_nav_ratio,
            "exchange": exchange_metrics,
        },
        "date_coverage_rows": _records(date_rows),
        "request_summary": _request_summary(request_manifest),
        "source_authority": {
            "shares": ["sse_official_etf_scale", "szse_official_fund_scale"],
            "nav": "eastmoney_fund_detail_history",
            "close": "tushare_fund_daily",
            "nav_is_secondary_source": True,
        },
        "factor_generation_allowed": False,
        "forward_return_read": False,
        "portfolio_grid_allowed": False,
        "walk_forward_allowed": False,
        "final_holdout_allowed": False,
        "promotion_allowed": False,
        "paper_signal_allowed": False,
        "broker_connection_allowed": False,
        "account_read_allowed": False,
        "order_placement_allowed": False,
        "live_boundary_allowed": False,
        "next_direction": (
            "preregister_one_compact_cn_etf_fund_structure_prescreen"
            if status == STATUS_READY
            else "rotate_to_next_orthogonal_cn_etf_source_readiness_review"
        ),
    }
    result["markdown"] = render_cn_etf_fund_structure_source_readiness(result)
    return result


def write_cn_etf_fund_structure_source_readiness(
    output_dir: str | Path,
    result: dict[str, Any],
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    clean = {key: value for key, value in result.items() if key != "markdown"}
    json_path = output / f"{STAGE}.json"
    markdown_path = output / f"{STAGE}.md"
    coverage_path = output / "date_coverage.csv"
    atomic_write_json(json_path, _sanitize(clean))
    atomic_write_text(markdown_path, render_cn_etf_fund_structure_source_readiness(result))
    coverage = pd.DataFrame(result.get("date_coverage_rows", []))
    atomic_write(coverage_path, lambda temporary: coverage.to_csv(temporary, index=False))
    return {
        "json": json_path,
        "markdown": markdown_path,
        "date_coverage_csv": coverage_path,
    }


def render_cn_etf_fund_structure_source_readiness(result: dict[str, Any]) -> str:
    summary = result["summary"]
    coverage = result["coverage"]
    blockers = result["gate"]["blockers"]
    lines = [
        "# CN ETF Fund-Structure Source Readiness",
        "",
        f"- Review date: {result['review_date']}",
        f"- Status: `{result['status']}`",
        f"- Analysis window: {result['analysis']['start_date']} to {result['analysis']['end_date']}",
        f"- Analysis sessions: {summary['analysis_sessions']}",
        f"- Share rows / assets: {summary['share_rows']} / {summary['share_assets']}",
        f"- Positive NAV rows: {summary['positive_nav_rows']}",
        f"- Combined qualifying-date coverage: {coverage['combined_qualifying_date_coverage']:.2%}",
        f"- Median share asset coverage: {coverage['median_share_asset_coverage']:.2%}",
        f"- NAV intersection coverage: {coverage['nav_intersection_coverage']:.2%}",
        f"- SSE date coverage: {coverage['exchange']['SSE']['date_coverage']:.2%}",
        f"- SZSE date coverage: {coverage['exchange']['SZSE']['date_coverage']:.2%}",
        "",
        "## Decision",
        "",
        (
            "The public fund-structure source passed the frozen readiness gates. "
            "Only a later preregistration task is authorized."
            if result["gate"]["cleared"]
            else "The public fund-structure source remains blocked. No factor generation is authorized."
        ),
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{blocker}`" for blocker in blockers] or ["- None"])
    lines.extend(
        [
            "",
            "## Safety Boundary",
            "",
            "Research-to-paper only. No forward-return read, factor generation, portfolio grid, "
            "walk-forward run, final-holdout access, broker connection, account read, order placement, "
            "or live trading is authorized.",
            "",
        ]
    )
    return "\n".join(lines)


def _normalize_bars(bars: pd.DataFrame, *, start: Any, end: Any) -> pd.DataFrame:
    required = {"date", "asset_id", "symbol", "close", "source"}
    missing = sorted(required - set(bars.columns))
    if missing:
        raise ValueError(f"bar authority is missing columns: {', '.join(missing)}")
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
    frame = frame.loc[frame["date"].between(start, end)].copy()
    if frame.duplicated(["asset_id", "date"]).any():
        raise ValueError("bar authority contains duplicate asset-date rows")
    frame["exchange"] = frame["symbol"].astype(str).map(
        lambda value: "SSE" if value.upper().endswith(".SH") else "SZSE"
    )
    return frame


def _normalize_processed(processed: pd.DataFrame) -> pd.DataFrame:
    required = {
        "date",
        "known_from",
        "asset_id",
        "symbol",
        "exchange",
        "total_share",
        "nav",
        "close",
        "total_size",
        "nav_premium_discount",
        "share_source",
        "nav_source",
        "close_source",
    }
    missing = sorted(required - set(processed.columns))
    if missing:
        raise ValueError(f"processed fund-structure inputs are missing columns: {', '.join(missing)}")
    frame = processed.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
    frame["known_from"] = pd.to_datetime(frame["known_from"], errors="coerce").dt.date
    return frame


def _coverage_rows(
    *,
    processed: pd.DataFrame,
    bars: pd.DataFrame,
    thresholds: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    bar_counts = (
        bars.groupby("date", as_index=False)["asset_id"]
        .nunique()
        .rename(columns={"asset_id": "bar_assets"})
    )
    share_counts = (
        processed.groupby("date", as_index=False)["asset_id"]
        .nunique()
        .rename(columns={"asset_id": "share_assets"})
    )
    rows = bar_counts.merge(share_counts, on="date", how="left")
    rows["share_assets"] = rows["share_assets"].fillna(0).astype(int)
    rows["share_asset_coverage"] = rows["share_assets"] / rows["bar_assets"].replace(0, np.nan)
    rows["combined_qualifies"] = (
        rows["share_assets"] >= int(thresholds["minimum_combined_assets_per_date"])
    )

    exchange_metrics: dict[str, Any] = {}
    for exchange in ("SSE", "SZSE"):
        exchange_bars = bars[bars["exchange"] == exchange]
        exchange_shares = processed[processed["exchange"] == exchange]
        eligible = (
            exchange_bars.groupby("date")["asset_id"].nunique()
            >= int(thresholds["minimum_exchange_assets_per_date"])
        )
        eligible_dates = set(eligible[eligible].index)
        share_counts_by_date = exchange_shares.groupby("date")["asset_id"].nunique()
        qualifying_dates = {
            date
            for date in eligible_dates
            if int(share_counts_by_date.get(date, 0))
            >= int(thresholds["minimum_exchange_assets_per_date"])
        }
        exchange_metrics[exchange] = {
            "eligible_dates": len(eligible_dates),
            "qualifying_dates": len(qualifying_dates),
            "date_coverage": _ratio(len(qualifying_dates), len(eligible_dates)),
            "share_assets": int(exchange_shares["asset_id"].nunique())
            if not exchange_shares.empty
            else 0,
        }
        rows[f"{exchange.lower()}_bar_assets"] = rows["date"].map(
            exchange_bars.groupby("date")["asset_id"].nunique()
        ).fillna(0).astype(int)
        rows[f"{exchange.lower()}_share_assets"] = rows["date"].map(
            share_counts_by_date
        ).fillna(0).astype(int)
    return rows.sort_values("date").reset_index(drop=True), exchange_metrics


def _official_share_failures(manifest: dict[str, Any]) -> int:
    requests = manifest.get("requests", {})
    if not isinstance(requests, dict):
        return 1
    return sum(
        1
        for row in requests.values()
        if isinstance(row, dict)
        and row.get("kind") in {"sse_share", "szse_share"}
        and row.get("status") != "completed"
    )


def _request_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    requests = manifest.get("requests", {})
    if not isinstance(requests, dict):
        return {"total": 0, "completed": 0, "failed": 0, "by_kind": {}}
    by_kind: dict[str, dict[str, int]] = {}
    completed = 0
    failed = 0
    for row in requests.values():
        if not isinstance(row, dict):
            continue
        kind = str(row.get("kind", "unknown"))
        status = str(row.get("status", "unknown"))
        group = by_kind.setdefault(kind, {"total": 0, "completed": 0, "failed": 0})
        group["total"] += 1
        if status == "completed":
            completed += 1
            group["completed"] += 1
        else:
            failed += 1
            group["failed"] += 1
    return {
        "total": len(requests),
        "completed": completed,
        "failed": failed,
        "by_kind": by_kind,
    }


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    clean = frame.copy()
    if "date" in clean.columns:
        clean["date"] = pd.to_datetime(clean["date"]).dt.strftime("%Y-%m-%d")
    return json.loads(clean.to_json(orient="records"))


def _ratio(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value
