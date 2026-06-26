from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Sequence

import pandas as pd


STAGE = "cn_stock_tradeability_data_readiness_audit"
TRADEABILITY_CONTROLS = [
    "limit_up_down_filter",
    "suspension_filter",
    "st_flag_filter",
    "new_listing_age_filter",
    "delisting_risk_filter",
    "board_permission_filter",
]
READY_STATUSES = {"ready"}

LIMIT_FIELDS = {"up_limit", "down_limit", "limit_up", "limit_down", "limit_status", "limit"}
SUSPENSION_FIELDS = {"is_suspended", "suspend_type", "suspend_reason", "suspend_date", "suspend_timing"}
ST_FIELDS = {"is_st", "st_flag", "special_treatment_flag", "st_status"}
DELIST_FIELDS = {"is_delisted", "delist_status"}
LIMIT_FEED_FIELDS = {"up_limit", "down_limit"}
SUSPENSION_FEED_FIELDS = {"suspend_timing", "suspend_type", "suspend_reason", "reason_type", "resume_date"}
NAMECHANGE_FEED_FIELDS = {"name", "is_st_name", "start_date", "ann_date"}
TRADEABILITY_COVERAGE_FEEDS = {
    "tradeability_stk_limit",
    "tradeability_suspension",
    "tradeability_namechange",
}


def build_cn_stock_tradeability_data_readiness_audit(
    *,
    data_roots: Sequence[str | Path],
    expected_start: str | None = None,
    expected_end: str | None = None,
) -> dict[str, Any]:
    roots = [Path(path) for path in data_roots]
    bars_profile = _profile_bars(_find_parquet_files(roots, "processed/bars"))
    coverage_profile = _profile_tradeability_coverage_manifest(
        _find_parquet_files(roots, "metadata/tushare_tradeability_feed_coverage"),
        expected_start=expected_start,
        expected_end=expected_end,
    )
    limit_feed_profile = _profile_tradeability_feed(
        _find_parquet_files(roots, "processed/tradeability_stk_limit"),
        required_fields=LIMIT_FEED_FIELDS,
    )
    limit_feed_profile = _attach_expected_feed_coverage(
        limit_feed_profile,
        feed="tradeability_stk_limit",
        coverage_profile=coverage_profile,
        expected_start=expected_start,
        expected_end=expected_end,
        allow_date_range_without_manifest=True,
    )
    suspension_feed_profile = _profile_tradeability_feed(
        _find_parquet_files(roots, "processed/tradeability_suspension"),
        required_fields=SUSPENSION_FEED_FIELDS,
    )
    suspension_feed_profile = _attach_expected_feed_coverage(
        suspension_feed_profile,
        feed="tradeability_suspension",
        coverage_profile=coverage_profile,
        expected_start=expected_start,
        expected_end=expected_end,
        allow_date_range_without_manifest=False,
    )
    namechange_feed_profile = _profile_tradeability_feed(
        _find_parquet_files(roots, "processed/tradeability_namechange"),
        required_fields=NAMECHANGE_FEED_FIELDS,
        st_name_feed=True,
    )
    namechange_feed_profile = _attach_expected_feed_coverage(
        namechange_feed_profile,
        feed="tradeability_namechange",
        coverage_profile=coverage_profile,
        expected_start=expected_start,
        expected_end=expected_end,
        allow_date_range_without_manifest=False,
    )
    stock_basic_profile = _profile_stock_basic(_find_parquet_files(roots, "tushare_stock_basic"))
    control_rows = _control_rows(
        bars_profile=bars_profile,
        limit_feed_profile=limit_feed_profile,
        suspension_feed_profile=suspension_feed_profile,
        namechange_feed_profile=namechange_feed_profile,
        stock_basic_profile=stock_basic_profile,
    )
    blockers = [
        f"tradeability_data_not_ready:{row['control_id']}:{row['status']}"
        for row in control_rows
        if not row["usable_for_direct_mining"]
    ]
    missing_feeds = _missing_data_feeds(control_rows)
    direct_allowed = not blockers
    status = "tradeability_data_ready" if direct_allowed else "direct_mining_blocked"
    return {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "summary": {
            "data_roots": [str(path) for path in roots],
            "bars_files": bars_profile["file_count"],
            "bars_rows": bars_profile["row_count"],
            "bars_assets": bars_profile["asset_count"],
            "bars_start_date": bars_profile["start_date"],
            "bars_end_date": bars_profile["end_date"],
            "limit_feed_files": limit_feed_profile["file_count"],
            "limit_feed_rows": limit_feed_profile["row_count"],
            "limit_feed_expected_window_coverage": limit_feed_profile["expected_window_coverage"],
            "suspension_feed_files": suspension_feed_profile["file_count"],
            "suspension_feed_rows": suspension_feed_profile["row_count"],
            "suspension_feed_expected_window_coverage": suspension_feed_profile["expected_window_coverage"],
            "namechange_feed_files": namechange_feed_profile["file_count"],
            "namechange_feed_rows": namechange_feed_profile["row_count"],
            "namechange_feed_expected_window_coverage": namechange_feed_profile["expected_window_coverage"],
            "stock_basic_files": stock_basic_profile["file_count"],
            "stock_basic_rows": stock_basic_profile["row_count"],
            "stock_basic_assets": stock_basic_profile["asset_count"],
            "stock_basic_snapshot_statuses": stock_basic_profile["list_status_values"],
            "expected_start": expected_start or "",
            "expected_end": expected_end or "",
            "expected_window_coverage": _coverage_status(
                bars_profile["start_date"],
                bars_profile["end_date"],
                expected_start=expected_start,
                expected_end=expected_end,
            ),
            "ready_controls": sum(1 for row in control_rows if row["status"] == "ready"),
            "blocking_controls": len(blockers),
        },
        "datasets": {
            "bars": bars_profile,
            "tradeability_stk_limit": limit_feed_profile,
            "tradeability_suspension": suspension_feed_profile,
            "tradeability_namechange": namechange_feed_profile,
            "stock_basic": stock_basic_profile,
            "tradeability_feed_coverage": coverage_profile,
        },
        "control_rows": control_rows,
        "missing_data_feeds": missing_feeds,
        "decision": {
            "direct_factor_generation_allowed": direct_allowed,
            "next_round_direction": (
                "round198_tradeability_controls_ready_for_quality_gate_closeout_after_manifest_coverage"
                if direct_allowed
                else "round198_continue_long_cycle_tradeability_backfill_until_manifest_coverage_then_mask_integration"
            ),
            "allowed_next_work_modes": (
                ["quality_gate_closeout", "direct_factor_generation_with_candidate_plan_gate"]
                if direct_allowed
                else [
                    "official_tradeability_feed_backfill",
                    "tradeability_mask_implementation",
                    "candidate_preregistration_without_profit_claims",
                ]
            ),
            "blockers": blockers,
        },
    }


def write_cn_stock_tradeability_data_readiness_audit(output_dir: str | Path, packet: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean_packet = _sanitize(packet)
    (output_path / "cn_stock_tradeability_data_readiness_audit.json").write_text(
        json.dumps(clean_packet, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "cn_stock_tradeability_data_readiness_audit.md").write_text(
        render_markdown(clean_packet),
        encoding="utf-8",
    )


def render_markdown(packet: dict[str, Any]) -> str:
    summary = _dict(packet.get("summary"))
    decision = _dict(packet.get("decision"))
    lines = [
        "# CN Stock Tradeability Data Readiness Audit",
        "",
        f"- Stage: {packet.get('stage', STAGE)}",
        f"- Status: {packet.get('status', '')}",
        f"- Bars files: {summary.get('bars_files', 0)}",
        f"- Bars rows: {summary.get('bars_rows', 0)}",
        f"- Bars assets: {summary.get('bars_assets', 0)}",
        f"- Bars date range: {summary.get('bars_start_date', '')} to {summary.get('bars_end_date', '')}",
        f"- Stock basic files: {summary.get('stock_basic_files', 0)}",
        f"- Stock basic assets: {summary.get('stock_basic_assets', 0)}",
        f"- Expected window coverage: {summary.get('expected_window_coverage', '')}",
        f"- Ready controls: {summary.get('ready_controls', 0)}",
        f"- Blocking controls: {summary.get('blocking_controls', 0)}",
        f"- Direct factor generation allowed: {decision.get('direct_factor_generation_allowed', False)}",
        f"- Next round direction: {decision.get('next_round_direction', '')}",
        "",
        "## Control Rows",
        "",
        "| Control | Status | Usable for direct mining | Evidence | Next action |",
        "|---|---|---:|---|---|",
    ]
    for row in _list_of_dicts(packet.get("control_rows")):
        lines.append(
            "| {control} | {status} | {usable} | {evidence} | {next_action} |".format(
                control=row.get("control_id", ""),
                status=row.get("status", ""),
                usable=row.get("usable_for_direct_mining", False),
                evidence=row.get("evidence", ""),
                next_action=row.get("next_action", ""),
            )
        )
    lines.extend(["", "## Missing Data Feeds", ""])
    missing_feeds = _list(packet.get("missing_data_feeds"))
    lines.extend(f"- {feed}" for feed in missing_feeds) if missing_feeds else lines.append("- none")
    lines.extend(["", "## Blockers", ""])
    blockers = _list(decision.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    return "\n".join(lines) + "\n"


def _find_parquet_files(roots: Sequence[Path], marker: str) -> list[Path]:
    files: list[Path] = []
    marker_parts = tuple(part.lower() for part in Path(marker).parts)
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.parquet"):
            parts = tuple(part.lower() for part in path.parts)
            if _contains_parts(parts, marker_parts):
                files.append(path)
    return sorted(files)


def _contains_parts(parts: tuple[str, ...], marker_parts: tuple[str, ...]) -> bool:
    if not marker_parts:
        return False
    width = len(marker_parts)
    return any(parts[index : index + width] == marker_parts for index in range(len(parts) - width + 1))


def _profile_bars(paths: list[Path]) -> dict[str, Any]:
    frames = []
    columns: set[str] = set()
    for path in paths:
        frame = pd.read_parquet(path)
        columns.update(str(column) for column in frame.columns)
        required_columns = [column for column in ("date", "asset_id") if column in frame.columns]
        if required_columns:
            frames.append(frame[required_columns])
    if frames:
        combined = pd.concat(frames, ignore_index=True)
        dates = pd.to_datetime(combined["date"], errors="coerce") if "date" in combined.columns else pd.Series(dtype="datetime64[ns]")
        assets = combined["asset_id"].dropna() if "asset_id" in combined.columns else pd.Series(dtype="object")
        start_date = dates.min().date().isoformat() if not dates.dropna().empty else ""
        end_date = dates.max().date().isoformat() if not dates.dropna().empty else ""
        row_count = int(len(combined))
        asset_count = int(assets.nunique())
    else:
        start_date = ""
        end_date = ""
        row_count = 0
        asset_count = 0
    return {
        "file_count": len(paths),
        "row_count": row_count,
        "asset_count": asset_count,
        "start_date": start_date,
        "end_date": end_date,
        "columns": sorted(columns),
        "has_ohlcv": {"open", "high", "low", "close", "volume", "amount"}.issubset(columns),
        "has_limit_fields": bool(columns & LIMIT_FIELDS),
        "limit_fields": sorted(columns & LIMIT_FIELDS),
        "has_suspension_fields": bool(columns & SUSPENSION_FIELDS),
        "suspension_fields": sorted(columns & SUSPENSION_FIELDS),
        "has_st_fields": bool(columns & ST_FIELDS),
        "st_fields": sorted(columns & ST_FIELDS),
        "has_delist_fields": bool(columns & DELIST_FIELDS),
        "delist_fields": sorted(columns & DELIST_FIELDS),
    }


def _profile_tradeability_feed(
    paths: list[Path],
    *,
    required_fields: set[str],
    st_name_feed: bool = False,
) -> dict[str, Any]:
    frames = []
    columns: set[str] = set()
    for path in paths:
        frame = pd.read_parquet(path)
        columns.update(str(column) for column in frame.columns)
        required_columns = [column for column in ("date", "asset_id", "symbol") if column in frame.columns]
        value_columns = [column for column in required_fields if column in frame.columns]
        selected_columns = sorted(set(required_columns + value_columns))
        if selected_columns:
            frames.append(frame[selected_columns])
    if frames:
        combined = pd.concat(frames, ignore_index=True)
        dates = pd.to_datetime(combined["date"], errors="coerce") if "date" in combined.columns else pd.Series(dtype="datetime64[ns]")
        assets = combined["asset_id"].dropna() if "asset_id" in combined.columns else pd.Series(dtype="object")
        start_date = dates.min().date().isoformat() if not dates.dropna().empty else ""
        end_date = dates.max().date().isoformat() if not dates.dropna().empty else ""
        row_count = int(len(combined))
        asset_count = int(assets.nunique())
        has_st_rows = _has_st_name_rows(combined) if st_name_feed else False
    else:
        start_date = ""
        end_date = ""
        row_count = 0
        asset_count = 0
        has_st_rows = False
    present_required_fields = sorted(columns & required_fields)
    return {
        "file_count": len(paths),
        "row_count": row_count,
        "asset_count": asset_count,
        "start_date": start_date,
        "end_date": end_date,
        "columns": sorted(columns),
        "required_fields": sorted(required_fields),
        "present_required_fields": present_required_fields,
        "has_required_fields": bool(columns & required_fields),
        "has_st_name_rows": has_st_rows,
    }


def _profile_tradeability_coverage_manifest(
    paths: list[Path],
    *,
    expected_start: str | None,
    expected_end: str | None,
) -> dict[str, Any]:
    frames = []
    columns: set[str] = set()
    for path in paths:
        frame = pd.read_parquet(path)
        columns.update(str(column) for column in frame.columns)
        selected = [column for column in ("feed", "start_date", "end_date", "market", "shard_id") if column in frame.columns]
        if {"feed", "start_date", "end_date"}.issubset(selected):
            frames.append(frame[selected])
    feeds: dict[str, Any] = {}
    if frames:
        combined = pd.concat(frames, ignore_index=True)
        for feed in sorted(str(value) for value in combined["feed"].dropna().unique()):
            feed_frame = combined[combined["feed"].astype(str) == feed]
            intervals = [
                (pd.Timestamp(row["start_date"]).normalize(), pd.Timestamp(row["end_date"]).normalize())
                for _, row in feed_frame.iterrows()
                if pd.notna(row["start_date"]) and pd.notna(row["end_date"])
            ]
            feeds[feed] = _coverage_from_intervals(
                intervals,
                expected_start=expected_start,
                expected_end=expected_end,
            )
            feeds[feed]["manifest_rows"] = int(len(feed_frame))
    return {
        "file_count": len(paths),
        "columns": sorted(columns),
        "expected_start": expected_start or "",
        "expected_end": expected_end or "",
        "feeds": feeds,
    }


def _attach_expected_feed_coverage(
    profile: dict[str, Any],
    *,
    feed: str,
    coverage_profile: dict[str, Any],
    expected_start: str | None,
    expected_end: str | None,
    allow_date_range_without_manifest: bool,
) -> dict[str, Any]:
    output = dict(profile)
    if not expected_start and not expected_end:
        output["expected_window_coverage"] = "not_requested"
        output["expected_window_coverage_source"] = "not_requested"
        return output
    feed_coverage = _dict(_dict(coverage_profile.get("feeds")).get(feed))
    if feed_coverage:
        output["expected_window_coverage"] = feed_coverage.get("status", "missing")
        output["expected_window_coverage_source"] = "manifest"
        output["coverage_manifest"] = feed_coverage
        return output
    if allow_date_range_without_manifest and output.get("row_count"):
        output["expected_window_coverage"] = _coverage_status(
            str(output.get("start_date", "")),
            str(output.get("end_date", "")),
            expected_start=expected_start,
            expected_end=expected_end,
        )
        output["expected_window_coverage_source"] = "date_range"
        return output
    output["expected_window_coverage"] = "missing_manifest" if output.get("row_count") else "missing"
    output["expected_window_coverage_source"] = "manifest_required"
    return output


def _coverage_from_intervals(
    intervals: list[tuple[pd.Timestamp, pd.Timestamp]],
    *,
    expected_start: str | None,
    expected_end: str | None,
) -> dict[str, Any]:
    if not expected_start and not expected_end:
        return {"status": "not_requested", "start_date": "", "end_date": "", "gaps": []}
    if not intervals:
        return {"status": "missing", "start_date": "", "end_date": "", "gaps": []}
    sorted_intervals = sorted(intervals, key=lambda item: item[0])
    merged: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for start, end in sorted_intervals:
        if not merged or start > merged[-1][1] + pd.Timedelta(days=1):
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    gaps = []
    for index in range(1, len(merged)):
        gap_start = merged[index - 1][1] + pd.Timedelta(days=1)
        gap_end = merged[index][0] - pd.Timedelta(days=1)
        gaps.append({"start_date": gap_start.date().isoformat(), "end_date": gap_end.date().isoformat()})
    expected_start_ts = pd.Timestamp(expected_start).normalize() if expected_start else merged[0][0]
    expected_end_ts = pd.Timestamp(expected_end).normalize() if expected_end else merged[-1][1]
    covered_start = merged[0][0] <= expected_start_ts
    covered_end = merged[-1][1] >= expected_end_ts
    in_window_gaps = [
        gap
        for gap in gaps
        if pd.Timestamp(gap["start_date"]) <= expected_end_ts and pd.Timestamp(gap["end_date"]) >= expected_start_ts
    ]
    status = "covered" if covered_start and covered_end and not in_window_gaps else "incomplete"
    return {
        "status": status,
        "start_date": merged[0][0].date().isoformat(),
        "end_date": merged[-1][1].date().isoformat(),
        "interval_count": len(sorted_intervals),
        "merged_interval_count": len(merged),
        "gaps": in_window_gaps,
    }


def _profile_stock_basic(paths: list[Path]) -> dict[str, Any]:
    frames = []
    columns: set[str] = set()
    for path in paths:
        frame = pd.read_parquet(path)
        columns.update(str(column) for column in frame.columns)
        frames.append(frame)
    if frames:
        combined = pd.concat(frames, ignore_index=True)
        list_status_values = sorted(str(value) for value in combined.get("list_status", pd.Series(dtype="object")).dropna().unique())
        has_active_only_snapshot = bool(list_status_values) and set(list_status_values) <= {"L"}
        return {
            "file_count": len(paths),
            "row_count": int(len(combined)),
            "asset_count": int(combined["asset_id"].nunique()) if "asset_id" in combined.columns else 0,
            "columns": sorted(columns),
            "list_status_values": list_status_values,
            "has_current_active_only_snapshot": has_active_only_snapshot or ("list_status" not in combined.columns),
            "has_list_date": _has_non_null(combined, "list_date"),
            "has_delist_date": _has_non_null(combined, "delist_date"),
            "has_board_fields": bool({"exchange", "stock_market"} & columns),
            "has_st_name_proxy": "name" in columns,
            "has_historical_status": bool(list_status_values) and not set(list_status_values) <= {"L"},
        }
    return {
        "file_count": 0,
        "row_count": 0,
        "asset_count": 0,
        "columns": [],
        "list_status_values": [],
        "has_current_active_only_snapshot": False,
        "has_list_date": False,
        "has_delist_date": False,
        "has_board_fields": False,
        "has_st_name_proxy": False,
        "has_historical_status": False,
    }


def _control_rows(
    *,
    bars_profile: dict[str, Any],
    limit_feed_profile: dict[str, Any],
    suspension_feed_profile: dict[str, Any],
    namechange_feed_profile: dict[str, Any],
    stock_basic_profile: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = [
        _limit_row(bars_profile, limit_feed_profile),
        _suspension_row(bars_profile, suspension_feed_profile),
        _st_row(bars_profile, namechange_feed_profile, stock_basic_profile),
        _new_listing_row(stock_basic_profile),
        _delisting_row(bars_profile, stock_basic_profile),
        _board_row(stock_basic_profile),
    ]
    return rows


def _limit_row(bars_profile: dict[str, Any], limit_feed_profile: dict[str, Any]) -> dict[str, Any]:
    if _official_feed_present(limit_feed_profile):
        if not _official_feed_coverage_ready(limit_feed_profile):
            return _row(
                "limit_up_down_filter",
                "partial_coverage",
                "Official stk_limit fields exist, but expected-window coverage is "
                + _official_feed_coverage_text(limit_feed_profile)
                + ".",
                "Complete long-cycle Tushare stk_limit backfill coverage before direct mining.",
            )
        return _row(
            "limit_up_down_filter",
            "ready",
            "Official stk_limit dataset is present with fields: "
            + ", ".join(_list(limit_feed_profile.get("present_required_fields")))
            + ".",
            "",
        )
    if bars_profile.get("has_limit_fields"):
        return _row("limit_up_down_filter", "ready", f"Official limit fields present: {', '.join(_list(bars_profile.get('limit_fields')))}.", "")
    if bars_profile.get("has_ohlcv"):
        return _row(
            "limit_up_down_filter",
            "proxy_only",
            "OHLCV can infer limit-like price behavior, but no official up/down limit field is present.",
            "Backfill Tushare stk_limit or limit_list_d and store point-in-time up_limit/down_limit fields.",
        )
    return _row(
        "limit_up_down_filter",
        "missing",
        "No OHLCV or official limit fields found.",
        "Backfill bars plus Tushare stk_limit or limit_list_d before direct mining.",
    )


def _suspension_row(bars_profile: dict[str, Any], suspension_feed_profile: dict[str, Any]) -> dict[str, Any]:
    if _official_feed_present(suspension_feed_profile):
        if not _official_feed_coverage_ready(suspension_feed_profile):
            return _row(
                "suspension_filter",
                "partial_coverage",
                "Official suspend_d fields exist, but expected-window coverage is "
                + _official_feed_coverage_text(suspension_feed_profile)
                + ".",
                "Complete long-cycle Tushare suspend_d backfill coverage before direct mining.",
            )
        return _row(
            "suspension_filter",
            "ready",
            "Official suspend_d dataset is present with fields: "
            + ", ".join(_list(suspension_feed_profile.get("present_required_fields")))
            + ".",
            "",
        )
    if bars_profile.get("has_suspension_fields"):
        return _row("suspension_filter", "ready", f"Official suspension fields present: {', '.join(_list(bars_profile.get('suspension_fields')))}.", "")
    if bars_profile.get("file_count") and bars_profile.get("asset_count"):
        return _row(
            "suspension_filter",
            "proxy_only",
            "Missing asset/date rows can proxy non-trading days, but cannot separate suspension from universe gaps.",
            "Backfill an official suspend_d style feed or store is_suspended by asset/date.",
        )
    return _row("suspension_filter", "missing", "No asset/date bars available.", "Backfill bars and official suspension status.")


def _st_row(
    bars_profile: dict[str, Any],
    namechange_feed_profile: dict[str, Any],
    stock_basic_profile: dict[str, Any],
) -> dict[str, Any]:
    if _official_feed_present(namechange_feed_profile) and namechange_feed_profile.get("has_st_name_rows"):
        if not _official_feed_coverage_ready(namechange_feed_profile):
            return _row(
                "st_flag_filter",
                "partial_coverage",
                "Official namechange ST evidence exists, but expected-window coverage is "
                + _official_feed_coverage_text(namechange_feed_profile)
                + ".",
                "Complete long-cycle Tushare namechange coverage before direct mining.",
            )
        return _row(
            "st_flag_filter",
            "ready",
            "Official namechange dataset is present and contains ST-name effective-date evidence.",
            "",
        )
    if bars_profile.get("has_st_fields"):
        return _row("st_flag_filter", "ready", f"Official ST fields present: {', '.join(_list(bars_profile.get('st_fields')))}.", "")
    if stock_basic_profile.get("has_st_name_proxy"):
        return _row(
            "st_flag_filter",
            "blocked_missing_official_history",
            "Current stock_basic name can only identify a snapshot ST proxy, not historical ST timing.",
            "Backfill Tushare namechange or another historical ST status feed and store effective-date ranges.",
        )
    return _row("st_flag_filter", "missing", "No ST field or name proxy found.", "Backfill historical ST status.")


def _new_listing_row(stock_basic_profile: dict[str, Any]) -> dict[str, Any]:
    if stock_basic_profile.get("has_list_date"):
        return _row("new_listing_age_filter", "ready", "Stock basic list_date is present for listing-age filters.", "")
    return _row("new_listing_age_filter", "missing", "No list_date field found.", "Backfill stock_basic list_date.")


def _delisting_row(bars_profile: dict[str, Any], stock_basic_profile: dict[str, Any]) -> dict[str, Any]:
    if bars_profile.get("has_delist_fields") or stock_basic_profile.get("has_historical_status"):
        evidence = []
        if bars_profile.get("has_delist_fields"):
            evidence.append(f"bars delist fields: {', '.join(_list(bars_profile.get('delist_fields')))}")
        if stock_basic_profile.get("has_historical_status"):
            evidence.append(f"stock_basic list_status values: {', '.join(_list(stock_basic_profile.get('list_status_values')))}")
        return _row("delisting_risk_filter", "ready", "; ".join(evidence), "")
    if stock_basic_profile.get("has_current_active_only_snapshot"):
        suffix = " Non-null delist_date in an active-only snapshot is not enough without historical list_status coverage."
        return _row(
            "delisting_risk_filter",
            "blocked_missing_official_history",
            "Only a current/active stock_basic snapshot is available; delisted and paused histories are not represented." + suffix,
            "Backfill stock_basic for L/P/D statuses or another PIT delisting-risk feed.",
        )
    return _row("delisting_risk_filter", "missing", "No delisting status evidence found.", "Backfill delisting status history.")


def _board_row(stock_basic_profile: dict[str, Any]) -> dict[str, Any]:
    if stock_basic_profile.get("has_board_fields"):
        return _row("board_permission_filter", "ready", "Exchange or stock_market fields are present for board permission filters.", "")
    return _row("board_permission_filter", "missing", "No exchange or board field found.", "Backfill exchange/stock_market metadata.")


def _row(control_id: str, status: str, evidence: str, next_action: str) -> dict[str, Any]:
    return {
        "control_id": control_id,
        "status": status,
        "usable_for_direct_mining": status in READY_STATUSES,
        "evidence": evidence,
        "next_action": next_action,
    }


def _missing_data_feeds(control_rows: list[dict[str, Any]]) -> list[str]:
    missing = []
    status_by_control = {row["control_id"]: row["status"] for row in control_rows}
    if status_by_control.get("limit_up_down_filter") != "ready":
        missing.append("tushare_stk_limit_or_limit_list")
    if status_by_control.get("suspension_filter") != "ready":
        missing.append("tushare_suspend_d")
    if status_by_control.get("st_flag_filter") != "ready":
        missing.append("tushare_namechange_or_historical_st_flag")
    if status_by_control.get("delisting_risk_filter") != "ready":
        missing.append("tushare_stock_basic_all_status_or_delist_feed")
    if status_by_control.get("new_listing_age_filter") != "ready":
        missing.append("tushare_stock_basic_list_date")
    if status_by_control.get("board_permission_filter") != "ready":
        missing.append("tushare_stock_basic_exchange_or_board")
    return missing


def _coverage_status(start_date: str, end_date: str, *, expected_start: str | None, expected_end: str | None) -> str:
    if not expected_start and not expected_end:
        return "not_requested"
    if not start_date or not end_date:
        return "missing_bars"
    start_ok = not expected_start or _date_within_start_tolerance(start_date, expected_start)
    end_ok = not expected_end or end_date >= expected_end
    if start_ok and end_ok:
        return "covered"
    return "incomplete"


def _date_within_start_tolerance(start_date: str, expected_start: str) -> bool:
    actual = pd.to_datetime(start_date)
    expected = pd.to_datetime(expected_start)
    return actual <= expected or (actual - expected).days <= 7


def _official_feed_present(profile: dict[str, Any]) -> bool:
    return bool(profile.get("row_count")) and bool(profile.get("has_required_fields"))


def _official_feed_ready(profile: dict[str, Any]) -> bool:
    return _official_feed_present(profile) and _official_feed_coverage_ready(profile)


def _official_feed_coverage_ready(profile: dict[str, Any]) -> bool:
    return str(profile.get("expected_window_coverage", "not_requested")) in {"covered", "not_requested"}


def _official_feed_coverage_text(profile: dict[str, Any]) -> str:
    status = str(profile.get("expected_window_coverage", "missing"))
    source = str(profile.get("expected_window_coverage_source", "unknown"))
    manifest = _dict(profile.get("coverage_manifest"))
    start = manifest.get("start_date") or profile.get("start_date", "")
    end = manifest.get("end_date") or profile.get("end_date", "")
    if start or end:
        return f"{status} via {source} ({start} to {end})"
    return f"{status} via {source}"


def _has_st_name_rows(frame: pd.DataFrame) -> bool:
    if "is_st_name" in frame.columns and frame["is_st_name"].fillna(False).astype(bool).any():
        return True
    if "name" not in frame.columns:
        return False
    return frame["name"].fillna("").astype(str).str.upper().str.contains("ST", regex=False).any()


def _has_non_null(frame: pd.DataFrame, column: str) -> bool:
    return column in frame.columns and not frame[column].dropna().empty


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
