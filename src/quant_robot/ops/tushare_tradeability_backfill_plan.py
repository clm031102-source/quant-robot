from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Callable

import pandas as pd


STAGE = "tushare_tradeability_long_cycle_backfill_plan"
PER_TRADE_DATE_ENDPOINTS = 2
PER_SHARD_RANGE_ENDPOINTS = 1
STOCK_BASIC_STATUS_CALLS = 3
DEFAULT_MAX_BUSINESS_DAYS_PER_SHARD = 25
REQUIRED_COVERAGE_FEEDS = {
    "tradeability_stk_limit",
    "tradeability_suspension",
    "tradeability_namechange",
}

BackfillRunner = Callable[..., dict[str, Any]]


def build_tushare_tradeability_backfill_plan(
    *,
    start_date: str,
    end_date: str,
    processed_root: str | Path,
    report_root: str | Path | None = None,
    max_shards: int | None = None,
    max_estimated_business_days_per_shard: int = DEFAULT_MAX_BUSINESS_DAYS_PER_SHARD,
    execute: bool = False,
    execute_write_processed: bool = False,
    market: str = "CN",
    snapshot: str | None = None,
    skip_covered: bool = False,
) -> dict[str, Any]:
    market = market.upper()
    if market != "CN":
        raise ValueError(f"Unsupported Tushare tradeability backfill market: {market}")
    if max_shards is not None and max_shards <= 0:
        raise ValueError("max_shards must be positive when provided")

    start = pd.Timestamp(start_date).normalize()
    end = pd.Timestamp(end_date).normalize()
    if start > end:
        raise ValueError("start_date must be on or before end_date")

    processed_path = Path(processed_root)
    report_root_path = Path(report_root) if report_root else Path("data/reports") / f"{processed_path.name}_tradeability_shards"
    all_shards = _month_shards(start, end)
    coverage = _read_coverage_manifest(processed_path, market=market) if skip_covered else {}
    uncovered_shards = [
        shard
        for shard in all_shards
        if not _shard_is_covered(shard, coverage)
    ]
    selected_shards = uncovered_shards[:max_shards] if max_shards is not None else uncovered_shards
    shards = [
        _build_shard(
            shard=shard,
            processed_root=processed_path,
            report_root=report_root_path,
            execute_write_processed=execute_write_processed,
            market=market,
            snapshot=snapshot,
        )
        for shard in selected_shards
    ]
    over_budget = [
        shard["shard_id"]
        for shard in shards
        if int(shard["estimated_business_days"]) > max_estimated_business_days_per_shard
    ]
    blockers = ["shard_estimated_business_days_over_budget"] if over_budget else []
    return {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": "blocked" if blockers else "ready",
        "market": market,
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "processed_root": str(processed_path),
        "report_root": str(report_root_path),
        "execute": bool(execute),
        "processed_writes_enabled": bool(execute_write_processed),
        "skip_covered": bool(skip_covered),
        "snapshot": snapshot or "",
        "summary": {
            "planned_shards": len(all_shards),
            "covered_shards": len(all_shards) - len(uncovered_shards),
            "uncovered_shards": len(uncovered_shards),
            "selected_shards": len(shards),
            "total_estimated_business_days": sum(int(shard["estimated_business_days"]) for shard in shards),
            "per_trade_date_endpoints": PER_TRADE_DATE_ENDPOINTS,
            "per_shard_range_endpoints": PER_SHARD_RANGE_ENDPOINTS,
            "stock_basic_status_calls_per_shard": STOCK_BASIC_STATUS_CALLS,
            "total_estimated_endpoint_calls": sum(int(shard["estimated_endpoint_calls"]) for shard in shards),
            "max_estimated_business_days_per_shard": max_estimated_business_days_per_shard,
            "over_budget_shards": over_budget,
            "remaining_unselected_shards": max(len(uncovered_shards) - len(shards), 0),
        },
        "blockers": blockers,
        "blocked_uses": [
            "direct_cn_stock_factor_mining_before_tradeability_backfill",
            "short_window_profitability_claims_without_long_cycle_tradeability_masks",
            "portfolio_or_etf_signal_research_using_unmasked_cn_stock_universe",
        ],
        "required_after_each_shard": [
            "inspect_tradeability_feed_ingestion_report",
            "verify_zero_available_date_lag_violations",
            "rerun_cn_stock_tradeability_data_readiness_audit",
            "keep_processed_data_and_reports_out_of_git",
        ],
        "required_before_factor_mining": [
            "full_long_cycle_tradeability_feed_coverage_ready",
            "tradeability_mask_join_smoke_passed",
            "factor_mining_quality_gate_direct_factor_generation_allowed",
            "candidate_preregistration_rejects_short_sample_profit_claims",
        ],
        "known_limitations": [
            "stock_basic_status_snapshot_is_not_a_historical_point_in_time_membership_feed",
            "namechange_available_date_uses_next_trade_date_after_ann_date_or_start_date",
            "this_backfill_is_data_readiness_evidence_not_profitability_evidence",
        ],
        "shards": shards,
        "promotion_allowed": False,
        "promotion_blockers": [
            "backfill_plan_or_execution_is_not_alpha_evidence",
            "long_cycle_factor_walk_forward_not_run_yet",
            "statistical_reality_check_not_run_yet",
        ],
    }


def run_tushare_tradeability_backfill(
    *,
    start_date: str,
    end_date: str,
    processed_root: str | Path,
    output_dir: str | Path,
    report_root: str | Path | None = None,
    max_shards: int | None = None,
    max_estimated_business_days_per_shard: int = DEFAULT_MAX_BUSINESS_DAYS_PER_SHARD,
    execute: bool = False,
    execute_write_processed: bool = False,
    market: str = "CN",
    snapshot: str | None = None,
    skip_covered: bool = False,
    runner: BackfillRunner | None = None,
) -> dict[str, Any]:
    plan = build_tushare_tradeability_backfill_plan(
        start_date=start_date,
        end_date=end_date,
        processed_root=processed_root,
        report_root=report_root,
        max_shards=max_shards,
        max_estimated_business_days_per_shard=max_estimated_business_days_per_shard,
        execute=execute,
        execute_write_processed=execute_write_processed,
        market=market,
        snapshot=snapshot,
        skip_covered=skip_covered,
    )
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    execution_rows: list[dict[str, Any]] = []
    if execute:
        if plan["status"] != "ready":
            raise ValueError("Backfill plan is blocked; lower shard size or increase the shard business-day budget")
        if runner is None:
            raise ValueError("runner is required when execute=True")
        progress_path = output_path / "tradeability_backfill_progress.jsonl"
        with progress_path.open("w", encoding="utf-8") as handle:
            for shard in plan["shards"]:
                row = _execute_shard(
                    shard=shard,
                    runner=runner,
                    processed_root=processed_root,
                    execute_write_processed=execute_write_processed,
                    market=market,
                    snapshot=snapshot,
                )
                execution_rows.append(row)
                handle.write(json.dumps(row, sort_keys=True) + "\n")
    plan["execution_summary"] = _execution_summary(execution_rows)
    plan["executions"] = execution_rows
    write_tushare_tradeability_backfill_plan(plan, output_path)
    return plan


def write_tushare_tradeability_backfill_plan(plan: dict[str, Any], output_dir: str | Path) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean_plan = _sanitize(plan)
    (output_path / "tushare_tradeability_long_cycle_backfill_plan.json").write_text(
        json.dumps(clean_plan, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "tushare_tradeability_long_cycle_backfill_plan.md").write_text(
        render_tushare_tradeability_backfill_plan_markdown(clean_plan),
        encoding="utf-8",
    )


def render_tushare_tradeability_backfill_plan_markdown(plan: dict[str, Any]) -> str:
    summary = _dict(plan.get("summary"))
    execution_summary = _dict(plan.get("execution_summary"))
    lines = [
        "# Tushare Tradeability Long-Cycle Backfill Plan",
        "",
        f"- Stage: {plan.get('stage', STAGE)}",
        f"- Status: {plan.get('status', '')}",
        f"- Market: {plan.get('market', '')}",
        f"- Window: {plan.get('start_date', '')} to {plan.get('end_date', '')}",
        f"- Processed root: {plan.get('processed_root', '')}",
        f"- Report root: {plan.get('report_root', '')}",
        f"- Execute: {plan.get('execute', False)}",
        f"- Processed writes enabled: {plan.get('processed_writes_enabled', False)}",
        f"- Planned shards: {summary.get('planned_shards', 0)}",
        f"- Selected shards: {summary.get('selected_shards', 0)}",
        f"- Estimated endpoint calls: {summary.get('total_estimated_endpoint_calls', 0)}",
        f"- Executed shards: {execution_summary.get('executed_shards', 0)}",
        f"- Failed shards: {execution_summary.get('failed_shards', 0)}",
        f"- Promotion allowed: {plan.get('promotion_allowed', False)}",
        "",
        "## Blockers",
        "",
    ]
    blockers = _list(plan.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(
        [
            "",
            "## Shards",
            "",
            "| Shard | Start | End | Est. business days | Est. calls | Command |",
            "|---|---|---|---:|---:|---|",
        ]
    )
    for shard in _list_of_dicts(plan.get("shards")):
        lines.append(
            "| {shard_id} | {start} | {end} | {days} | {calls} | `{command}` |".format(
                shard_id=shard.get("shard_id", ""),
                start=shard.get("start_date", ""),
                end=shard.get("end_date", ""),
                days=shard.get("estimated_business_days", 0),
                calls=shard.get("estimated_endpoint_calls", 0),
                command=shard.get("command", ""),
            )
        )
    lines.extend(["", "## Required Before Factor Mining", ""])
    lines.extend(f"- {item}" for item in _list(plan.get("required_before_factor_mining")))
    lines.extend(["", "## Known Limitations", ""])
    lines.extend(f"- {item}" for item in _list(plan.get("known_limitations")))
    lines.append("")
    return "\n".join(lines)


def _month_shards(start: pd.Timestamp, end: pd.Timestamp) -> list[dict[str, Any]]:
    shards: list[dict[str, Any]] = []
    current_month = start.replace(day=1)
    while current_month <= end:
        month_end = current_month + pd.offsets.MonthEnd(0)
        shard_start = max(start, current_month)
        shard_end = min(end, month_end)
        if shard_start <= shard_end:
            shards.append(
                {
                    "shard_id": f"{current_month:%Y%m}",
                    "start": shard_start,
                    "end": shard_end,
                }
            )
        current_month = current_month + pd.DateOffset(months=1)
    return shards


def _read_coverage_manifest(processed_root: Path, *, market: str) -> dict[str, list[tuple[pd.Timestamp, pd.Timestamp]]]:
    coverage_root = processed_root / "metadata" / "tushare_tradeability_feed_coverage"
    if not coverage_root.exists():
        return {}
    intervals: dict[str, list[tuple[pd.Timestamp, pd.Timestamp]]] = {}
    for path in sorted(coverage_root.rglob("*.parquet")):
        frame = pd.read_parquet(path)
        required_columns = {"feed", "start_date", "end_date"}
        if not required_columns.issubset(frame.columns):
            continue
        if "market" in frame.columns:
            frame = frame[frame["market"].astype(str).str.upper() == market]
        for _, row in frame.iterrows():
            feed = str(row["feed"])
            if feed not in REQUIRED_COVERAGE_FEEDS:
                continue
            start = pd.Timestamp(row["start_date"]).normalize()
            end = pd.Timestamp(row["end_date"]).normalize()
            intervals.setdefault(feed, []).append((start, end))
    return {feed: _merge_intervals(feed_intervals) for feed, feed_intervals in intervals.items()}


def _merge_intervals(intervals: list[tuple[pd.Timestamp, pd.Timestamp]]) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    merged: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for start, end in sorted(intervals, key=lambda item: item[0]):
        if not merged or start > merged[-1][1] + pd.Timedelta(days=1):
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def _shard_is_covered(shard: dict[str, Any], coverage: dict[str, list[tuple[pd.Timestamp, pd.Timestamp]]]) -> bool:
    shard_start = pd.Timestamp(shard["start"]).normalize()
    shard_end = pd.Timestamp(shard["end"]).normalize()
    return all(_intervals_cover(feed_intervals, shard_start, shard_end) for feed_intervals in coverage.values()) and REQUIRED_COVERAGE_FEEDS.issubset(coverage)


def _intervals_cover(intervals: list[tuple[pd.Timestamp, pd.Timestamp]], start: pd.Timestamp, end: pd.Timestamp) -> bool:
    return any(interval_start <= start and interval_end >= end for interval_start, interval_end in intervals)


def _build_shard(
    *,
    shard: dict[str, Any],
    processed_root: Path,
    report_root: Path,
    execute_write_processed: bool,
    market: str,
    snapshot: str | None,
) -> dict[str, Any]:
    start = pd.Timestamp(shard["start"])
    end = pd.Timestamp(shard["end"])
    business_days = int(len(pd.bdate_range(start, end)))
    report_dir = report_root / f"shard_{shard['shard_id']}"
    endpoint_calls = business_days * PER_TRADE_DATE_ENDPOINTS + PER_SHARD_RANGE_ENDPOINTS + STOCK_BASIC_STATUS_CALLS
    command_parts = [
        "python scripts\\run_tushare_tradeability_feed_ingest.py",
        f"--start-date {start.date().isoformat()}",
        f"--end-date {end.date().isoformat()}",
        f"--output-dir {report_dir}",
        f"--market {market}",
    ]
    if snapshot:
        command_parts.append(f"--snapshot {snapshot}")
    if execute_write_processed:
        command_parts.append("--execute-write-processed")
    return {
        "shard_id": str(shard["shard_id"]),
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "estimated_business_days": business_days,
        "estimated_endpoint_calls": endpoint_calls,
        "processed_root": str(processed_root),
        "report_dir": str(report_dir),
        "command": " ".join(command_parts),
    }


def _execute_shard(
    *,
    shard: dict[str, Any],
    runner: BackfillRunner,
    processed_root: str | Path,
    execute_write_processed: bool,
    market: str,
    snapshot: str | None,
) -> dict[str, Any]:
    result = runner(
        start_date=shard["start_date"],
        end_date=shard["end_date"],
        output_dir=Path(shard["report_dir"]),
        processed_root=Path(processed_root),
        execute_write_processed=execute_write_processed,
        market=market,
        snapshot=snapshot,
    )
    summary = _dict(result.get("summary"))
    status = str(summary.get("status") or ("fail" if int(summary.get("fail_count", 0) or 0) else "pass"))
    return {
        "shard_id": shard["shard_id"],
        "start_date": shard["start_date"],
        "end_date": shard["end_date"],
        "status": status,
        "warn_count": int(summary.get("warn_count", 0) or 0),
        "fail_count": int(summary.get("fail_count", 0) or 0),
        "processed_writes_enabled": bool(result.get("processed_writes_enabled", execute_write_processed)),
        "report_dir": shard["report_dir"],
    }


def _execution_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "executed_shards": len(rows),
        "passed_shards": sum(1 for row in rows if row.get("status") == "pass"),
        "warned_shards": sum(1 for row in rows if row.get("status") == "warn"),
        "failed_shards": sum(1 for row in rows if row.get("status") == "fail" or int(row.get("fail_count", 0) or 0) > 0),
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in _list(value) if isinstance(item, dict)]


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item"):
        return value.item()
    return value
