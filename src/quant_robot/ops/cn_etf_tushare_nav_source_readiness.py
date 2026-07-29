from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from quant_robot.storage.atomic import atomic_write, atomic_write_json, atomic_write_text


STAGE = "cn_etf_tushare_nav_source_readiness"
STATUS_READY = "ready_for_nav_premium_preregistration"
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
FORBIDDEN_COLUMN_TOKENS = ("return", "label", "signal", "score", "rank", "portfolio")


def build_cn_etf_tushare_nav_source_readiness(
    *,
    config: dict[str, Any],
    nav: pd.DataFrame,
    request_manifest: dict[str, Any],
    public_nav: pd.DataFrame,
    official_sessions: Sequence[pd.Timestamp],
    configuration_sha256: str,
) -> dict[str, Any]:
    analysis = dict(config["analysis"])
    thresholds = dict(config["thresholds"])
    boundaries = dict(config["boundaries"])
    start = pd.to_datetime(analysis["start_date"]).date()
    end = pd.to_datetime(analysis["end_date"]).date()
    holdout_start = pd.to_datetime(analysis["final_holdout_start"]).date()

    forbidden_columns = sorted(
        column
        for column in nav.columns
        if any(token in str(column).lower() for token in FORBIDDEN_COLUMN_TOKENS)
    )
    frame = _normalize_nav(nav)
    public = _normalize_public_nav(public_nav)
    official_index = pd.DatetimeIndex(
        pd.to_datetime(pd.Series(official_sessions), errors="raise")
    ).normalize().drop_duplicates().sort_values()
    sessions = sorted(
        {
            value.date()
            for value in official_index
            if start <= value.date() <= end
        }
    )
    request_rows, request_summary = _request_rows_and_summary(request_manifest)

    rows = int(len(frame))
    duplicate_rows = int(frame.duplicated(["asset_id", "nav_date"]).sum())
    outside_window_rows = int((~frame["nav_date"].between(start, end)).sum())
    holdout_rows = int((frame["nav_date"] >= holdout_start).sum())
    valid_announcement = frame["ann_date"].notna() & (frame["ann_date"] >= frame["nav_date"])
    valid_announcement_ratio = _ratio(int(valid_announcement.sum()), rows)
    known_from_valid = (
        frame["known_from"].notna()
        & (frame["known_from"] > frame["nav_date"])
        & (frame["known_from"] > frame["ann_date"])
    )
    known_from_violations = int((valid_announcement & ~known_from_valid).sum())
    availability_base = pd.concat(
        [
            pd.to_datetime(frame["nav_date"], errors="coerce"),
            pd.to_datetime(frame["ann_date"], errors="coerce"),
        ],
        axis=1,
    ).max(axis=1)
    expected_known_from = _first_official_session_strictly_after(
        availability_base,
        official_index,
    )
    exact_known_from = pd.to_datetime(
        frame["known_from"],
        errors="coerce",
    ).dt.normalize().eq(expected_known_from)
    exact_known_from_violations = int(
        (valid_announcement & known_from_valid & ~exact_known_from).sum()
    )
    unit_nav = pd.to_numeric(frame["unit_nav"], errors="coerce")
    positive_unit_nav = unit_nav.notna() & np.isfinite(unit_nav) & unit_nav.gt(0.0)
    positive_unit_nav_ratio = _ratio(int(positive_unit_nav.sum()), rows)
    source_identity_violations = int(frame["source"].ne("tushare_fund_nav").sum())

    eligible = frame.loc[
        frame["nav_date"].between(start, end)
        & valid_announcement
        & known_from_valid
        & positive_unit_nav,
        ["nav_date", "asset_id", "unit_nav", "is_pit_usable"],
    ].copy()
    eligible["is_pit_usable"] = eligible["is_pit_usable"].fillna(False).astype(bool)
    eligible = eligible.loc[eligible["is_pit_usable"]].copy()
    usable_counts = eligible.groupby("nav_date")["asset_id"].nunique()
    session_coverage_rows = pd.DataFrame({"date": sessions})
    session_coverage_rows["usable_assets"] = (
        session_coverage_rows["date"].map(usable_counts).fillna(0).astype(int)
    )
    session_coverage_rows["qualifies"] = session_coverage_rows["usable_assets"].ge(
        int(thresholds["minimum_usable_assets_per_session"])
    )
    qualifying_sessions = int(session_coverage_rows["qualifies"].sum())
    usable_session_coverage = _ratio(qualifying_sessions, len(sessions))

    public_inside = public.loc[public["date"].between(start, end)].copy()
    public_value = pd.to_numeric(public_inside["nav"], errors="coerce")
    public_inside = public_inside.loc[
        public_value.notna() & np.isfinite(public_value) & public_value.gt(0.0)
    ].copy()
    public_duplicate_rows = int(public_inside.duplicated(["asset_id", "date"]).sum())
    comparison = eligible.merge(
        public_inside,
        left_on=["asset_id", "nav_date"],
        right_on=["asset_id", "date"],
        how="inner",
        validate="one_to_one" if not public_duplicate_rows and not duplicate_rows else "many_to_many",
        suffixes=("_tushare", "_public"),
    )
    public_keys = int(len(public_inside.drop_duplicates(["asset_id", "date"])))
    public_assets = int(public_inside["asset_id"].nunique())
    matched_keys = int(len(comparison.drop_duplicates(["asset_id", "nav_date"])))
    matched_assets = int(comparison["asset_id"].nunique())
    public_key_intersection_ratio = _ratio(matched_keys, public_keys)
    public_asset_match_ratio = _ratio(matched_assets, public_assets)
    if comparison.empty:
        comparison["absolute_relative_difference"] = pd.Series(dtype=float)
    else:
        comparison["absolute_relative_difference"] = (
            pd.to_numeric(comparison["unit_nav"], errors="coerce")
            / pd.to_numeric(comparison["nav"], errors="coerce")
            - 1.0
        ).abs()
    difference = pd.to_numeric(comparison["absolute_relative_difference"], errors="coerce")
    agreement_rows = int(difference.notna().sum())
    within_10bp_rows = int(difference.le(0.001).sum())
    severe_disagreement_rows = int(
        difference.gt(float(thresholds["severe_disagreement_threshold"])).sum()
    )
    within_10bp_ratio = _ratio(within_10bp_rows, agreement_rows)
    severe_disagreement_ratio = _ratio(severe_disagreement_rows, agreement_rows)

    blockers: list[str] = []
    if request_summary["terminal_ratio"] < float(thresholds["minimum_terminal_request_ratio"]):
        blockers.append("fund_nav_terminal_request_ratio_below_minimum")
    if request_summary["failed"]:
        blockers.append("fund_nav_requests_failed")
    if request_summary["unresolved"]:
        blockers.append("fund_nav_requests_unresolved")
    if duplicate_rows:
        blockers.append("duplicate_nav_asset_date_rows")
    if public_duplicate_rows:
        blockers.append("duplicate_public_nav_asset_date_rows")
    if outside_window_rows:
        blockers.append("nav_rows_outside_frozen_analysis_window")
    if holdout_rows:
        blockers.append("final_holdout_rows_present")
    if valid_announcement_ratio < float(thresholds["minimum_valid_announcement_ratio"]):
        blockers.append("valid_announcement_ratio_below_minimum")
    if known_from_violations:
        blockers.append("known_from_not_strictly_after_nav_and_announcement")
    if exact_known_from_violations:
        blockers.append(
            "known_from_not_first_official_session_after_nav_and_announcement"
        )
    if positive_unit_nav_ratio < float(thresholds["minimum_positive_unit_nav_ratio"]):
        blockers.append("positive_unit_nav_ratio_below_minimum")
    if source_identity_violations:
        blockers.append("unapproved_nav_source_rows")
    if public_key_intersection_ratio < float(thresholds["minimum_public_key_intersection_ratio"]):
        blockers.append("public_nav_key_intersection_below_minimum")
    if public_asset_match_ratio < float(thresholds["minimum_public_asset_match_ratio"]):
        blockers.append("public_nav_asset_match_below_minimum")
    if within_10bp_ratio < float(thresholds["minimum_within_10bp_ratio"]):
        blockers.append("nav_agreement_within_10bp_below_minimum")
    if severe_disagreement_ratio > float(thresholds["maximum_severe_disagreement_ratio"]):
        blockers.append("severe_nav_disagreement_above_maximum")
    if usable_session_coverage < float(thresholds["minimum_usable_session_coverage"]):
        blockers.append("usable_session_coverage_below_minimum")
    if forbidden_columns:
        blockers.append("forbidden_analytical_columns_present")
    for key in BOUNDARY_KEYS:
        if boundaries.get(key) is not False:
            blockers.append(f"boundary_enabled:{key}")
    blockers = list(dict.fromkeys(blockers))
    status = "blocked" if blockers else STATUS_READY

    result = {
        "stage": STAGE,
        "review_date": config["review_date"],
        "status": status,
        "primary_market": config.get("primary_market", "CN_ETF"),
        "research_family": config.get(
            "research_family",
            "cn_etf_nav_premium_relative_value",
        ),
        "configuration": {"sha256": configuration_sha256},
        "analysis": analysis,
        "thresholds": thresholds,
        "gate": {"cleared": not blockers, "blockers": blockers},
        "summary": {
            "official_sessions": len(sessions),
            "nav_rows": rows,
            "nav_assets": int(frame["asset_id"].nunique()) if not frame.empty else 0,
            "duplicate_rows": duplicate_rows,
            "outside_window_rows": outside_window_rows,
            "holdout_rows": holdout_rows,
            "valid_announcement_rows": int(valid_announcement.sum()),
            "known_from_violations": known_from_violations,
            "exact_known_from_violations": exact_known_from_violations,
            "positive_unit_nav_rows": int(positive_unit_nav.sum()),
            "source_identity_violations": source_identity_violations,
            "forbidden_columns": forbidden_columns,
        },
        "quality": {
            "valid_announcement_ratio": valid_announcement_ratio,
            "positive_unit_nav_ratio": positive_unit_nav_ratio,
        },
        "coverage": {
            "qualifying_sessions": qualifying_sessions,
            "usable_session_coverage": usable_session_coverage,
            "minimum_usable_assets_per_session": int(
                thresholds["minimum_usable_assets_per_session"]
            ),
        },
        "agreement": {
            "public_keys": public_keys,
            "public_assets": public_assets,
            "matched_keys": matched_keys,
            "matched_assets": matched_assets,
            "public_key_intersection_ratio": public_key_intersection_ratio,
            "public_asset_match_ratio": public_asset_match_ratio,
            "agreement_rows": agreement_rows,
            "within_10bp_rows": within_10bp_rows,
            "within_10bp_ratio": within_10bp_ratio,
            "severe_disagreement_rows": severe_disagreement_rows,
            "severe_disagreement_ratio": severe_disagreement_ratio,
        },
        "request_summary": request_summary,
        "request_state_rows": request_rows,
        "session_coverage_rows": _records(session_coverage_rows),
        "nav_agreement_summary_rows": [
            {
                "public_keys": public_keys,
                "matched_keys": matched_keys,
                "public_key_intersection_ratio": public_key_intersection_ratio,
                "public_assets": public_assets,
                "matched_assets": matched_assets,
                "public_asset_match_ratio": public_asset_match_ratio,
                "agreement_rows": agreement_rows,
                "within_10bp_ratio": within_10bp_ratio,
                "severe_disagreement_ratio": severe_disagreement_ratio,
            }
        ],
        "source_lineage": {
            "primary": "tushare_fund_nav",
            "comparison": "eastmoney_fund_detail_history",
            "comparison_is_gate_only": True,
        },
        "boundaries": boundaries,
        "next_direction": (
            "write_separate_single_candidate_preregistration"
            if status == STATUS_READY
            else "close_cn_etf_nav_premium_relative_value_source_review"
        ),
    }
    result["markdown"] = render_cn_etf_tushare_nav_source_readiness(result)
    return result


def write_cn_etf_tushare_nav_source_readiness(
    output_dir: str | Path,
    result: Mapping[str, Any],
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "source_readiness.json"
    markdown_path = output / "source_readiness.md"
    request_path = output / "request_states.csv"
    agreement_path = output / "nav_agreement_summary.csv"
    coverage_path = output / "session_coverage.csv"
    clean = {key: value for key, value in result.items() if key != "markdown"}
    atomic_write_json(json_path, _sanitize(clean))
    atomic_write_text(markdown_path, render_cn_etf_tushare_nav_source_readiness(result))
    _write_csv(request_path, pd.DataFrame(result.get("request_state_rows", [])))
    _write_csv(
        agreement_path,
        pd.DataFrame(result.get("nav_agreement_summary_rows", [])),
    )
    _write_csv(coverage_path, pd.DataFrame(result.get("session_coverage_rows", [])))
    return {
        "json": json_path,
        "markdown": markdown_path,
        "request_states_csv": request_path,
        "nav_agreement_summary_csv": agreement_path,
        "session_coverage_csv": coverage_path,
    }


def render_cn_etf_tushare_nav_source_readiness(result: Mapping[str, Any]) -> str:
    summary = result["summary"]
    coverage = result["coverage"]
    agreement = result["agreement"]
    blockers = result["gate"]["blockers"]
    lines = [
        "# CN ETF Tushare NAV Source Readiness",
        "",
        f"- Review date: {result['review_date']}",
        f"- Status: `{result['status']}`",
        f"- Analysis window: {result['analysis']['start_date']} to {result['analysis']['end_date']}",
        f"- NAV rows / assets: {summary['nav_rows']} / {summary['nav_assets']}",
        f"- Usable-session coverage: {coverage['usable_session_coverage']:.2%}",
        f"- Public NAV key intersection: {agreement['public_key_intersection_ratio']:.2%}",
        f"- Public NAV asset match: {agreement['public_asset_match_ratio']:.2%}",
        f"- Agreement within 10 bp: {agreement['within_10bp_ratio']:.2%}",
        f"- Severe disagreement: {agreement['severe_disagreement_ratio']:.4%}",
        "",
        "## Decision",
        "",
        (
            "The source passed the frozen gates. Only a separate one-candidate "
            "preregistration is authorized."
            if result["gate"]["cleared"]
            else "The source is blocked. No NAV-premium factor generation is authorized."
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
            "No return, factor, portfolio, paper signal, broker connection, account read, "
            "order placement, or live-trading action is authorized by this audit.",
            "",
        ]
    )
    return "\n".join(lines)


def _first_official_session_strictly_after(
    availability_base: pd.Series,
    official_sessions: pd.DatetimeIndex,
) -> pd.Series:
    base = pd.to_datetime(availability_base, errors="coerce").dt.normalize()
    expected = pd.Series(pd.NaT, index=base.index, dtype="datetime64[ns]")
    valid = base.notna()
    if not valid.any() or official_sessions.empty:
        return expected
    positions = official_sessions.searchsorted(base.loc[valid], side="right")
    within_calendar = positions < len(official_sessions)
    target_index = base.loc[valid].index[within_calendar]
    expected.loc[target_index] = official_sessions.take(positions[within_calendar])
    return expected


def _normalize_nav(nav: pd.DataFrame) -> pd.DataFrame:
    required = {
        "nav_date",
        "ann_date",
        "known_from",
        "asset_id",
        "symbol",
        "unit_nav",
        "is_pit_usable",
        "source",
    }
    missing = sorted(required - set(nav.columns))
    if missing:
        raise ValueError(f"Tushare NAV source is missing columns: {', '.join(missing)}")
    frame = nav.copy()
    for column in ("nav_date", "ann_date", "known_from"):
        frame[column] = pd.to_datetime(frame[column], errors="coerce").dt.date
    return frame


def _normalize_public_nav(public_nav: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "asset_id", "nav"}
    missing = sorted(required - set(public_nav.columns))
    if missing:
        raise ValueError(f"public NAV comparison is missing columns: {', '.join(missing)}")
    frame = public_nav[["date", "asset_id", "nav"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
    frame["nav"] = pd.to_numeric(frame["nav"], errors="coerce")
    return frame


def _request_rows_and_summary(
    manifest: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    requests = manifest.get("requests", {})
    if not isinstance(requests, dict):
        requests = {}
    scope = manifest.get("scope", {})
    expected = scope.get("symbols", []) if isinstance(scope, dict) else []
    expected_symbols = sorted(str(value) for value in expected)
    if not expected_symbols:
        expected_symbols = sorted(str(value) for value in requests)
    rows = []
    completed = empty = failed = unresolved = 0
    for symbol in expected_symbols:
        request = requests.get(symbol)
        if not isinstance(request, dict):
            status = "unresolved"
        else:
            status = str(request.get("status", "unresolved"))
        if status == "completed":
            completed += 1
        elif status == "empty":
            empty += 1
        elif status == "failed":
            failed += 1
        else:
            unresolved += 1
        rows.append(
            {
                "symbol": symbol,
                "status": status,
                "rows": int(request.get("rows", 0)) if isinstance(request, dict) else 0,
                "request_sha256": (
                    str(request.get("request_sha256", "")) if isinstance(request, dict) else ""
                ),
                "response_sha256": (
                    str(request.get("response_sha256", "")) if isinstance(request, dict) else ""
                ),
            }
        )
    total = len(expected_symbols)
    terminal = completed + empty + failed
    return rows, {
        "total": total,
        "completed": completed,
        "empty": empty,
        "failed": failed,
        "unresolved": unresolved,
        "terminal": terminal,
        "terminal_ratio": _ratio(terminal, total),
    }


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    atomic_write(path, lambda temporary: frame.to_csv(temporary, index=False))


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
