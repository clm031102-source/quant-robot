from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "tushare_fina_indicator_backfill_plan"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def build_fina_indicator_backfill_plan(
    *,
    symbols: list[str],
    start_period: str,
    end_period: str,
    batch_size: int = 500,
    max_requests: int | None = None,
) -> dict[str, Any]:
    normalized_symbols = _normalize_symbols(symbols)
    periods = _quarter_end_periods(start_period, end_period)
    requests = [{"ts_code": symbol, "period": period} for period in periods for symbol in normalized_symbols]
    blockers = _blockers(
        symbol_count=len(normalized_symbols),
        period_count=len(periods),
        request_count=len(requests),
        batch_size=batch_size,
        max_requests=max_requests,
    )
    batches = _request_batches(requests, batch_size) if batch_size > 0 else []
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "symbol_count": len(normalized_symbols),
            "period_count": len(periods),
            "request_count": len(requests),
            "batch_count": len(batches),
            "batch_size": batch_size,
            "max_requests": max_requests,
        },
        "periods": periods,
        "symbols": normalized_symbols,
        "request_batches": batches,
        "execution_policy": {
            "planner_calls_tushare": False,
            "requires_resume": True,
            "requires_rate_limit": True,
            "requires_pit_readiness_audit_after_backfill": True,
            "commit_data_allowed": False,
            "final_holdout_touched": False,
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_fina_indicator_backfill_plan_markdown(result)
    return result


def write_fina_indicator_backfill_plan(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "fina_indicator_backfill_plan.json").write_text(
        json.dumps(_without_markdown(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "fina_indicator_backfill_plan.md").write_text(
        render_fina_indicator_backfill_plan_markdown(result),
        encoding="utf-8",
    )


def render_fina_indicator_backfill_plan_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    policy = result.get("execution_policy", {})
    lines = [
        "# Tushare Fina Indicator Backfill Plan",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Symbols: {summary.get('symbol_count', 0)}",
        f"- Periods: {summary.get('period_count', 0)}",
        f"- Requests: {summary.get('request_count', 0)}",
        f"- Batches: {summary.get('batch_count', 0)}",
        f"- Batch size: {summary.get('batch_size', 0)}",
        f"- Max requests: {summary.get('max_requests')}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Execution Policy",
        "",
    ]
    for key in sorted(policy):
        lines.append(f"- {key}: {policy[key]}")
    lines.extend(["", "## Period Range", ""])
    periods = result.get("periods", []) or []
    if periods:
        lines.append(f"- First period: `{periods[0]}`")
        lines.append(f"- Last period: `{periods[-1]}`")
    else:
        lines.append("- none")
    lines.extend(["", "## First Batch Preview", ""])
    batches = result.get("request_batches", []) or []
    if not batches:
        lines.append("- none")
    else:
        for request in batches[0].get("requests", [])[:10]:
            lines.append(f"- `{request.get('ts_code')}` period `{request.get('period')}`")
    return "\n".join(lines) + "\n"


def _normalize_symbols(symbols: list[str]) -> list[str]:
    normalized: list[str] = []
    seen = set()
    for symbol in symbols:
        value = str(symbol).strip().upper()
        if not value or value in seen:
            continue
        normalized.append(value)
        seen.add(value)
    return normalized


def _quarter_end_periods(start_period: str, end_period: str) -> list[str]:
    quarters = pd.period_range(start=pd.to_datetime(start_period), end=pd.to_datetime(end_period), freq="Q")
    return [period.end_time.strftime("%Y%m%d") for period in quarters]


def _blockers(
    *,
    symbol_count: int,
    period_count: int,
    request_count: int,
    batch_size: int,
    max_requests: int | None,
) -> list[str]:
    blockers: list[str] = []
    if symbol_count == 0:
        blockers.append("missing_symbols")
    if period_count == 0:
        blockers.append("missing_quarterly_periods")
    if batch_size < 1:
        blockers.append("invalid_batch_size")
    if max_requests is not None and request_count > max_requests:
        blockers.append("request_count_exceeds_max_requests")
    return blockers


def _request_batches(requests: list[dict[str, str]], batch_size: int) -> list[dict[str, Any]]:
    batches = []
    for index in range(0, len(requests), batch_size):
        batch_requests = requests[index : index + batch_size]
        batches.append(
            {
                "batch_id": len(batches) + 1,
                "request_count": len(batch_requests),
                "requests": batch_requests,
            }
        )
    return batches


def _without_markdown(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "markdown"}
