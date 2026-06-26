from __future__ import annotations

from pathlib import Path
from typing import Any
import json

import pandas as pd

from quant_robot.ops.fina_indicator_symbol_shard_plan import build_fina_indicator_symbol_shard_plan


STAGE = "tushare_financial_statement_symbol_shard_plan"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
ENDPOINT_COUNT = 3


def build_financial_statement_symbol_shard_plan(
    *,
    symbols: list[str],
    start_period: str,
    end_period: str,
    symbols_per_shard: int = 50,
    max_endpoint_requests_per_shard: int = 3000,
    exclude_suffixes: list[str] | None = None,
    symbol_metadata: pd.DataFrame | None = None,
    stratify_by: list[str] | None = None,
) -> dict[str, Any]:
    base = build_fina_indicator_symbol_shard_plan(
        symbols=symbols,
        start_period=start_period,
        end_period=end_period,
        symbols_per_shard=symbols_per_shard,
        max_requests_per_shard=max_endpoint_requests_per_shard,
        exclude_suffixes=exclude_suffixes,
        symbol_metadata=symbol_metadata,
        stratify_by=stratify_by,
    )
    shards = [_statement_shard(row) for row in base.get("shards", []) or []]
    endpoint_blockers = []
    if any(int(shard["endpoint_request_count"]) > max_endpoint_requests_per_shard for shard in shards):
        endpoint_blockers.append("endpoint_request_count_exceeds_max_endpoint_requests_per_shard")
    base_blockers = list(base.get("summary", {}).get("blockers", []) or [])
    blockers = _dedupe_blockers(base_blockers + endpoint_blockers)
    total_base_requests = int(base.get("summary", {}).get("total_request_count", 0))
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": base.get("generated_at"),
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "symbol_count": base.get("summary", {}).get("symbol_count", 0),
            "excluded_symbol_count": base.get("summary", {}).get("excluded_symbol_count", 0),
            "period_count": base.get("summary", {}).get("period_count", 0),
            "endpoint_count": ENDPOINT_COUNT,
            "total_base_request_count": total_base_requests,
            "total_endpoint_request_count": total_base_requests * ENDPOINT_COUNT,
            "shard_count": len(shards),
            "symbols_per_shard": symbols_per_shard,
            "max_endpoint_requests_per_shard": max_endpoint_requests_per_shard,
            "stratification": base.get("summary", {}).get("stratification", {}),
        },
        "periods": base.get("periods", []),
        "excluded_symbols": base.get("excluded_symbols", []),
        "shards": shards,
        "execution_policy": {
            "planner_calls_tushare": False,
            "commit_data_allowed": False,
            "endpoint_count_per_symbol_period": ENDPOINT_COUNT,
            "requires_resume": True,
            "requires_empty_response_recording": True,
            "requires_pit_readiness_after_each_shard": True,
            "requires_required_column_group_readiness_after_each_shard": True,
            "factor_preregistration_allowed_before_full_readiness": False,
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_financial_statement_symbol_shard_plan_markdown(result)
    return result


def write_financial_statement_symbol_shard_plan(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "financial_statement_symbol_shard_plan.json").write_text(
        json.dumps(_without_markdown(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "financial_statement_symbol_shard_plan.md").write_text(
        render_financial_statement_symbol_shard_plan_markdown(result),
        encoding="utf-8",
    )


def render_financial_statement_symbol_shard_plan_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Financial Statement Symbol Shard Plan",
        "",
        f"- Stage: {result['stage']}",
        f"- Passes: {summary['passes']}",
        f"- Symbols: {summary['symbol_count']}",
        f"- Excluded symbols: {summary['excluded_symbol_count']}",
        f"- Periods: {summary['period_count']}",
        f"- Endpoint count: {summary['endpoint_count']}",
        f"- Total base requests: {summary['total_base_request_count']}",
        f"- Total endpoint requests: {summary['total_endpoint_request_count']}",
        f"- Shards: {summary['shard_count']}",
        f"- Symbols per shard: {summary['symbols_per_shard']}",
        f"- Max endpoint requests per shard: {summary['max_endpoint_requests_per_shard']}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Live boundary allowed: {result['live_boundary_allowed']}",
        f"- Safety: {result['safety']}",
        "",
        "## First Shards",
        "",
    ]
    for shard in result.get("shards", [])[:10]:
        lines.append(
            "- shard {shard_id}: symbols={symbol_count}, base_requests={base_request_count}, endpoint_requests={endpoint_request_count}, first={first_symbol}, last={last_symbol}".format(
                **shard
            )
        )
    return "\n".join(lines) + "\n"


def _statement_shard(row: dict[str, Any]) -> dict[str, Any]:
    shard = dict(row)
    base_request_count = int(shard.pop("request_count", 0))
    shard["base_request_count"] = base_request_count
    shard["endpoint_count"] = ENDPOINT_COUNT
    shard["endpoint_request_count"] = base_request_count * ENDPOINT_COUNT
    return shard


def _dedupe_blockers(blockers: list[str]) -> list[str]:
    output = []
    seen = set()
    for blocker in blockers:
        if blocker and blocker not in seen:
            output.append(blocker)
            seen.add(blocker)
    return output


def _without_markdown(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "markdown"}
