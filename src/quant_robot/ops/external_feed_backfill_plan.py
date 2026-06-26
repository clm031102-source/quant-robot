from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "external_feed_long_cycle_backfill_plan"
DEFAULT_PER_TRADE_DATE_ENDPOINTS = 4
DEFAULT_PER_SHARD_RANGE_ENDPOINTS = 2


def build_external_feed_backfill_plan(
    *,
    start_date: str,
    end_date: str,
    output_root: str | Path,
    report_root: str | Path | None = None,
    shard_months: int = 1,
    max_estimated_business_days_per_shard: int = 25,
    market: str = "CN",
) -> dict[str, Any]:
    if shard_months <= 0:
        raise ValueError("shard_months must be positive")
    start = pd.Timestamp(start_date).normalize()
    end = pd.Timestamp(end_date).normalize()
    if start > end:
        raise ValueError("start_date must be on or before end_date")
    processed_output_dir = Path(output_root)
    report_root_path = Path(report_root) if report_root else Path("data/reports") / f"{processed_output_dir.name}_shard_reports"

    shards = []
    current = start
    while current <= end:
        shard_end = min(current + pd.DateOffset(months=shard_months) - pd.Timedelta(days=1), end)
        business_days = int(len(pd.bdate_range(current, shard_end)))
        shard_id = f"{current:%Y%m}" if shard_months == 1 else f"{current:%Y%m}_{shard_end:%Y%m}"
        shard_report_dir = report_root_path / f"shard_{shard_id}"
        per_shard_calls = business_days * DEFAULT_PER_TRADE_DATE_ENDPOINTS + DEFAULT_PER_SHARD_RANGE_ENDPOINTS
        shards.append(
            {
                "shard_id": shard_id,
                "start_date": current.date().isoformat(),
                "end_date": shard_end.date().isoformat(),
                "estimated_business_days": business_days,
                "estimated_endpoint_calls": per_shard_calls,
                "output_dir": str(processed_output_dir),
                "processed_output_dir": str(processed_output_dir),
                "report_copy_dir": str(shard_report_dir),
                "command": (
                    "python scripts\\run_tushare_external_feed_ingest.py "
                    f"--start-date {current.date().isoformat()} "
                    f"--end-date {shard_end.date().isoformat()} "
                    f"--output-dir {processed_output_dir} "
                    f"--report-copy-dir {shard_report_dir} "
                    "--execute-write-processed"
                ),
            }
        )
        current = shard_end + pd.Timedelta(days=1)

    over_budget = [
        shard["shard_id"]
        for shard in shards
        if int(shard["estimated_business_days"]) > max_estimated_business_days_per_shard
    ]
    blockers = ["shard_estimated_business_days_over_budget"] if over_budget else []
    total_business_days = sum(int(shard["estimated_business_days"]) for shard in shards)
    total_calls = sum(int(shard["estimated_endpoint_calls"]) for shard in shards) + 1
    return {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": "blocked" if blockers else "ready",
        "market": market.upper(),
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "output_root": str(processed_output_dir),
        "processed_output_dir": str(processed_output_dir),
        "report_root": str(report_root_path),
        "shard_months": shard_months,
        "summary": {
            "shard_count": len(shards),
            "total_estimated_business_days": total_business_days,
            "per_trade_date_endpoints": DEFAULT_PER_TRADE_DATE_ENDPOINTS,
            "per_shard_range_endpoints": DEFAULT_PER_SHARD_RANGE_ENDPOINTS,
            "lpr_cache_calls": 1,
            "total_estimated_endpoint_calls": total_calls,
            "max_estimated_business_days_per_shard": max_estimated_business_days_per_shard,
            "over_budget_shards": over_budget,
        },
        "blockers": blockers,
        "blocked_uses": [
            "external_feed_portfolio_grid_before_long_cycle_backfill_coverage",
            "external_feed_short_join_smoke_as_profitability_evidence",
            "lpr_factor_before_lpr_coverage_is_non_missing",
        ],
        "required_after_each_shard": [
            "inspect_external_feed_ingestion_report",
            "rerun_external_feed_factor_matrix_join_smoke",
            "verify_zero_available_date_violations",
            "verify_zero_raw_same_day_or_future_date_violations",
            "keep_data_raw_processed_reports_out_of_git",
        ],
        "shards": shards,
        "promotion_allowed": False,
        "promotion_blockers": [
            "backfill_plan_is_not_ic_evidence",
            "no_long_cycle_join_smoke_report_yet",
            "no_cost_capacity_walk_forward",
        ],
    }


def write_external_feed_backfill_plan(plan: dict[str, Any], output_dir: str | Path) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "external_feed_long_cycle_backfill_plan.json").write_text(
        json.dumps(plan, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "external_feed_long_cycle_backfill_plan.md").write_text(
        render_external_feed_backfill_plan_markdown(plan),
        encoding="utf-8",
    )


def render_external_feed_backfill_plan_markdown(plan: dict[str, Any]) -> str:
    summary = plan.get("summary", {})
    lines = [
        "# External Feed Long-Cycle Backfill Plan",
        "",
        f"- Stage: {plan.get('stage', STAGE)}",
        f"- Status: {plan.get('status', '')}",
        f"- Market: {plan.get('market', '')}",
        f"- Window: {plan.get('start_date', '')} to {plan.get('end_date', '')}",
        f"- Shards: {summary.get('shard_count', 0)}",
        f"- Estimated endpoint calls: {summary.get('total_estimated_endpoint_calls', 0)}",
        f"- Promotion allowed: {plan.get('promotion_allowed', False)}",
        "",
        "## Blockers",
        "",
    ]
    blockers = plan.get("blockers", [])
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
    for shard in plan.get("shards", []):
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
    lines.extend(["", "## Required After Each Shard", ""])
    lines.extend(f"- {item}" for item in plan.get("required_after_each_shard", []))
    lines.append("")
    return "\n".join(lines)
