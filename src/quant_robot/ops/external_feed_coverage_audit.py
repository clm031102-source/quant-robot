from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore


STAGE = "external_feed_coverage_audit"
DEFAULT_HK_HOLD_MIN_OBSERVATION_DATES = 25
DEFAULT_HK_HOLD_MAX_MEDIAN_GAP_DAYS = 10
DEFAULT_MACRO_MIN_OBSERVATION_DATES = 60
DEFAULT_LPR_MIN_NON_NULL_RATIO = 0.8


def run_external_feed_coverage_audit(
    *,
    processed_root: str | Path,
    output_dir: str | Path,
    market: str = "CN",
    min_hk_hold_observation_dates: int = DEFAULT_HK_HOLD_MIN_OBSERVATION_DATES,
    max_hk_hold_median_gap_days: int = DEFAULT_HK_HOLD_MAX_MEDIAN_GAP_DAYS,
    min_macro_observation_dates: int = DEFAULT_MACRO_MIN_OBSERVATION_DATES,
    min_lpr_non_null_ratio: float = DEFAULT_LPR_MIN_NON_NULL_RATIO,
) -> dict[str, Any]:
    processed_path = Path(processed_root)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    hk_hold = _read_processed_dataset(processed_path, "external_hk_hold", market)
    macro_rates = _read_processed_dataset(processed_path, "external_macro_rates", market)

    feed_coverage = {
        "external_hk_hold": _audit_hk_hold(
            hk_hold,
            min_observation_dates=min_hk_hold_observation_dates,
            max_median_gap_days=max_hk_hold_median_gap_days,
        ),
        "external_macro_rates": _audit_macro_rates(
            macro_rates,
            min_observation_dates=min_macro_observation_dates,
            min_lpr_non_null_ratio=min_lpr_non_null_ratio,
        ),
    }
    summary = _summary(feed_coverage)
    report = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "processed_root": str(processed_path),
        "market": market.upper(),
        "thresholds": {
            "min_hk_hold_observation_dates": int(min_hk_hold_observation_dates),
            "max_hk_hold_median_gap_days": int(max_hk_hold_median_gap_days),
            "min_macro_observation_dates": int(min_macro_observation_dates),
            "min_lpr_non_null_ratio": float(min_lpr_non_null_ratio),
        },
        "summary": summary,
        "feed_coverage": feed_coverage,
        "promotion_allowed": False,
        "promotion_blockers": [
            "coverage_audit_is_not_ic_or_profitability_evidence",
            "external_feed_candidates_still_require_ic_quantile_turnover_cost_capacity_walk_forward",
        ],
    }
    (output_path / "external_feed_coverage_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "external_feed_coverage_audit.md").write_text(
        render_external_feed_coverage_audit_markdown(report),
        encoding="utf-8",
    )
    return report


def render_external_feed_coverage_audit_markdown(report: dict[str, Any]) -> str:
    summary = _dict(report.get("summary"))
    hk_hold = _dict(_dict(report.get("feed_coverage")).get("external_hk_hold"))
    macro = _dict(_dict(report.get("feed_coverage")).get("external_macro_rates"))
    lines = [
        "# External Feed Coverage Audit",
        "",
        f"- Stage: {report.get('stage', STAGE)}",
        f"- Market: {report.get('market', '')}",
        f"- Processed root: {report.get('processed_root', '')}",
        f"- Blocked feeds: {summary.get('blocked_count', 0)}",
        f"- Pass feeds: {summary.get('pass_count', 0)}",
        f"- Promotion allowed: {report.get('promotion_allowed', False)}",
        "",
        "## HK Hold",
        "",
        f"- Status: {hk_hold.get('status', '')}",
        f"- Rows: {hk_hold.get('rows', 0)}",
        f"- Observation dates: {hk_hold.get('unique_observation_dates', 0)}",
        f"- First/last date: {hk_hold.get('first_date')} to {hk_hold.get('last_date')}",
        f"- Unique symbols: {hk_hold.get('unique_symbols')}",
        f"- Median gap days: {hk_hold.get('median_gap_days')}",
        f"- Detected frequency: {hk_hold.get('detected_frequency')}",
        f"- Blockers: {', '.join(_list(hk_hold.get('blockers'))) or 'none'}",
        f"- Allowed use: {hk_hold.get('allowed_use')}",
        "",
        "## Macro Rates",
        "",
        f"- Status: {macro.get('status', '')}",
        f"- Rows: {macro.get('rows', 0)}",
        f"- Observation dates: {macro.get('unique_observation_dates', 0)}",
        f"- First/last date: {macro.get('first_date')} to {macro.get('last_date')}",
        f"- SHIBOR complete rows: {macro.get('shibor_complete_rows', 0)}",
        f"- LPR 1Y non-null rows: {macro.get('lpr_1y_non_null_rows', 0)}",
        f"- LPR 5Y non-null rows: {macro.get('lpr_5y_non_null_rows', 0)}",
        f"- LPR non-null ratio: {macro.get('lpr_non_null_ratio', 0.0):.2%}",
        f"- Blockers: {', '.join(_list(macro.get('blockers'))) or 'none'}",
        f"- Allowed use: {macro.get('allowed_use')}",
        "",
        "## Blocked Uses",
        "",
    ]
    blocked_uses = _unique_preserving_order(
        _list(hk_hold.get("blocked_uses")) + _list(macro.get("blocked_uses"))
    )
    lines.extend(f"- {item}" for item in blocked_uses) if blocked_uses else lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def _audit_hk_hold(
    frame: pd.DataFrame,
    *,
    min_observation_dates: int,
    max_median_gap_days: int,
) -> dict[str, Any]:
    columns = ["hold_ratio", "hold_vol"]
    if frame.empty:
        return _blocked_feed(
            "external_hk_hold",
            blockers=["hk_hold_processed_feed_missing_or_empty"],
            blocked_uses=_hk_hold_blocked_uses(),
            required_columns=["date", "available_date", "symbol", *columns],
        )
    missing_columns = [column for column in ["date", "available_date", "symbol", *columns] if column not in frame.columns]
    if missing_columns:
        return _blocked_feed(
            "external_hk_hold",
            blockers=["hk_hold_required_columns_missing"],
            blocked_uses=_hk_hold_blocked_uses(),
            missing_columns=missing_columns,
            rows=len(frame),
        )
    normalized = frame.copy()
    dates = pd.to_datetime(normalized["date"]).dropna().sort_values()
    unique_dates = dates.drop_duplicates()
    date_counts = dates.dt.date.value_counts().sort_index()
    gaps = unique_dates.diff().dt.days.dropna()
    median_gap = float(gaps.median()) if not gaps.empty else None
    max_gap = int(gaps.max()) if not gaps.empty else None
    blockers: list[str] = []
    if int(unique_dates.nunique()) < min_observation_dates:
        blockers.append("hk_hold_observation_dates_below_minimum")
    if median_gap is None or median_gap > max_median_gap_days:
        blockers.append("hk_hold_frequency_not_daily_enough_for_daily_rank")

    status = "blocked" if blockers else "pass"
    return {
        "feed": "external_hk_hold",
        "status": status,
        "rows": int(len(frame)),
        "unique_observation_dates": int(unique_dates.nunique()),
        "first_date": unique_dates.min().date().isoformat() if not unique_dates.empty else None,
        "last_date": unique_dates.max().date().isoformat() if not unique_dates.empty else None,
        "unique_symbols": int(normalized["symbol"].nunique()),
        "date_row_count_min": int(date_counts.min()) if not date_counts.empty else 0,
        "date_row_count_median": float(date_counts.median()) if not date_counts.empty else 0.0,
        "date_row_count_max": int(date_counts.max()) if not date_counts.empty else 0,
        "median_gap_days": median_gap,
        "max_gap_days": max_gap,
        "detected_frequency": _detected_frequency(median_gap),
        "missing_by_column": _missing_by_column(normalized, columns),
        "blockers": blockers,
        "blocked_uses": _hk_hold_blocked_uses() if blockers else [],
        "allowed_use": (
            "low_frequency_state_or_interaction_after_redesign"
            if "hk_hold_frequency_not_daily_enough_for_daily_rank" in blockers
            else "daily_cross_sectional_rank_after_full_validation"
        ),
    }


def _audit_macro_rates(
    frame: pd.DataFrame,
    *,
    min_observation_dates: int,
    min_lpr_non_null_ratio: float,
) -> dict[str, Any]:
    shibor_columns = ["shibor_1m", "shibor_3m", "shibor_1y"]
    lpr_columns = ["lpr_1y", "lpr_5y"]
    required_columns = ["date", "available_date", *shibor_columns, *lpr_columns]
    if frame.empty:
        return _blocked_feed(
            "external_macro_rates",
            blockers=["macro_rates_processed_feed_missing_or_empty"],
            blocked_uses=_macro_blocked_uses(),
            required_columns=required_columns,
        )
    missing_columns = [column for column in required_columns if column not in frame.columns]
    if missing_columns:
        return _blocked_feed(
            "external_macro_rates",
            blockers=["macro_rates_required_columns_missing"],
            blocked_uses=_macro_blocked_uses(),
            missing_columns=missing_columns,
            rows=len(frame),
        )
    normalized = frame.copy()
    dates = pd.to_datetime(normalized["date"]).dropna().sort_values()
    unique_dates = dates.drop_duplicates()
    shibor_complete = normalized[shibor_columns].notna().all(axis=1)
    lpr_complete = normalized[lpr_columns].notna().all(axis=1)
    lpr_ratio = float(lpr_complete.mean()) if len(normalized) else 0.0
    blockers: list[str] = []
    if int(unique_dates.nunique()) < min_observation_dates:
        blockers.append("macro_observation_dates_below_minimum")
    if lpr_ratio < min_lpr_non_null_ratio:
        blockers.append("lpr_non_missing_coverage_below_threshold")
    status = "blocked" if blockers else "pass"
    return {
        "feed": "external_macro_rates",
        "status": status,
        "rows": int(len(frame)),
        "unique_observation_dates": int(unique_dates.nunique()),
        "first_date": unique_dates.min().date().isoformat() if not unique_dates.empty else None,
        "last_date": unique_dates.max().date().isoformat() if not unique_dates.empty else None,
        "shibor_complete_rows": int(shibor_complete.sum()),
        "shibor_complete_ratio": float(shibor_complete.mean()) if len(normalized) else 0.0,
        "lpr_1y_non_null_rows": int(normalized["lpr_1y"].notna().sum()),
        "lpr_5y_non_null_rows": int(normalized["lpr_5y"].notna().sum()),
        "lpr_complete_rows": int(lpr_complete.sum()),
        "lpr_non_null_ratio": lpr_ratio,
        "missing_by_column": _missing_by_column(normalized, shibor_columns + lpr_columns),
        "blockers": blockers,
        "blocked_uses": _macro_blocked_uses() if blockers else [],
        "allowed_use": (
            "shibor_only_regime_control_after_long_cycle_validation"
            if blockers == ["lpr_non_missing_coverage_below_threshold"]
            else "macro_regime_control_after_full_validation"
        ),
    }


def _read_processed_dataset(root: Path, dataset: str, market: str) -> pd.DataFrame:
    store_root = _normalize_processed_root(root, dataset)
    store = DatasetStore(store_root)
    base = store_root / "processed" / dataset / "frequency=1d" / f"market={market.upper()}"
    frames = []
    for year_path in sorted(base.glob("year=*")):
        year = year_path.name.split("=", 1)[1]
        frames.append(store.read_frame(f"processed/{dataset}", {"frequency": "1d", "market": market.upper(), "year": year}))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _normalize_processed_root(root: Path, dataset: str) -> Path:
    if (root / dataset).exists() and not (root / "processed" / dataset).exists():
        return root.parent
    return root


def _blocked_feed(
    feed: str,
    *,
    blockers: list[str],
    blocked_uses: list[str],
    required_columns: list[str] | None = None,
    missing_columns: list[str] | None = None,
    rows: int = 0,
) -> dict[str, Any]:
    return {
        "feed": feed,
        "status": "blocked",
        "rows": int(rows),
        "unique_observation_dates": 0,
        "first_date": None,
        "last_date": None,
        "required_columns": required_columns or [],
        "missing_columns": missing_columns or [],
        "blockers": blockers,
        "blocked_uses": blocked_uses,
        "allowed_use": "none_until_coverage_repaired",
    }


def _summary(feed_coverage: dict[str, dict[str, Any]]) -> dict[str, Any]:
    statuses = [str(feed.get("status")) for feed in feed_coverage.values()]
    blocked_uses = _unique_preserving_order(
        [item for feed in feed_coverage.values() for item in _list(feed.get("blocked_uses"))]
    )
    blockers = _unique_preserving_order(
        [item for feed in feed_coverage.values() for item in _list(feed.get("blockers"))]
    )
    return {
        "audited_feed_count": len(feed_coverage),
        "pass_count": statuses.count("pass"),
        "blocked_count": statuses.count("blocked"),
        "warn_count": statuses.count("warn"),
        "blockers": blockers,
        "blocked_factor_uses": blocked_uses,
        "external_feed_ic_or_portfolio_allowed": not blockers,
    }


def _detected_frequency(median_gap: float | None) -> str:
    if median_gap is None:
        return "single_observation"
    if median_gap <= 3:
        return "daily_or_near_daily"
    if median_gap <= 10:
        return "weekly_or_irregular"
    if median_gap <= 45:
        return "monthly_or_sparse"
    return "quarterly_or_sparse"


def _missing_by_column(frame: pd.DataFrame, columns: list[str]) -> dict[str, int]:
    return {column: int(frame[column].isna().sum()) for column in columns if column in frame.columns}


def _hk_hold_blocked_uses() -> list[str]:
    return [
        "external_feed_hk_hold_daily_rank_factor_before_frequency_repair",
        "northbound_hold_ratio_accumulation_before_hk_hold_coverage_repair",
        "northbound_hold_accumulation_flow_regime_before_hk_hold_coverage_repair",
    ]


def _macro_blocked_uses() -> list[str]:
    return [
        "external_feed_lpr_factor_before_non_missing_lpr_coverage",
        "policy_liquidity_lpr_regime_before_lpr_coverage_repair",
    ]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _unique_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique
