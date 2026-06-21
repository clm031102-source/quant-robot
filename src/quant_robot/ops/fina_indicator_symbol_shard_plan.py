from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "tushare_fina_indicator_symbol_universe_shard_plan"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def build_fina_indicator_symbol_shard_plan(
    *,
    symbols: list[str],
    start_period: str,
    end_period: str,
    symbols_per_shard: int = 100,
    max_requests_per_shard: int = 5000,
    exclude_suffixes: list[str] | None = None,
) -> dict[str, Any]:
    normalized = _normalize_symbols(symbols)
    excluded_suffix_set = {suffix.upper().lstrip(".") for suffix in (exclude_suffixes or [])}
    included = [symbol for symbol in normalized if _suffix(symbol) not in excluded_suffix_set]
    excluded = [symbol for symbol in normalized if _suffix(symbol) in excluded_suffix_set]
    periods = _quarter_end_periods(start_period, end_period)
    shards = _build_shards(included, periods, symbols_per_shard)
    blockers = _blockers(
        symbols=included,
        periods=periods,
        symbols_per_shard=symbols_per_shard,
        max_requests_per_shard=max_requests_per_shard,
        shards=shards,
    )
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "symbol_count": len(included),
            "excluded_symbol_count": len(excluded),
            "period_count": len(periods),
            "total_request_count": len(included) * len(periods),
            "shard_count": len(shards),
            "symbols_per_shard": symbols_per_shard,
            "max_requests_per_shard": max_requests_per_shard,
        },
        "periods": periods,
        "excluded_symbols": excluded,
        "shards": shards,
        "execution_policy": {
            "planner_calls_tushare": False,
            "commit_data_allowed": False,
            "requires_resume": True,
            "requires_empty_response_recording": True,
            "requires_duplicate_row_gate": True,
            "requires_pit_readiness_after_each_shard": True,
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_fina_indicator_symbol_shard_plan_markdown(result)
    return result


def write_fina_indicator_symbol_shard_plan(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "fina_indicator_symbol_shard_plan.json").write_text(
        json.dumps(_without_markdown(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "fina_indicator_symbol_shard_plan.md").write_text(
        render_fina_indicator_symbol_shard_plan_markdown(result),
        encoding="utf-8",
    )


def render_fina_indicator_symbol_shard_plan_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Fina Indicator Symbol Universe Shard Plan",
        "",
        f"- Stage: {result['stage']}",
        f"- Passes: {summary['passes']}",
        f"- Symbols: {summary['symbol_count']}",
        f"- Excluded symbols: {summary['excluded_symbol_count']}",
        f"- Periods: {summary['period_count']}",
        f"- Total requests: {summary['total_request_count']}",
        f"- Shards: {summary['shard_count']}",
        f"- Symbols per shard: {summary['symbols_per_shard']}",
        f"- Max requests per shard: {summary['max_requests_per_shard']}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Live boundary allowed: {result['live_boundary_allowed']}",
        f"- Safety: {result['safety']}",
        "",
        "## First Shards",
        "",
    ]
    for shard in result.get("shards", [])[:10]:
        lines.append(
            "- shard {shard_id}: symbols={symbol_count}, requests={request_count}, first={first_symbol}, last={last_symbol}".format(
                **shard
            )
        )
    return "\n".join(lines) + "\n"


def _normalize_symbols(symbols: list[str]) -> list[str]:
    seen = set()
    normalized = []
    for symbol in symbols:
        value = str(symbol).strip().upper()
        if not value or value in seen:
            continue
        normalized.append(value)
        seen.add(value)
    return sorted(normalized)


def _quarter_end_periods(start_period: str, end_period: str) -> list[str]:
    quarters = pd.period_range(start=pd.to_datetime(start_period), end=pd.to_datetime(end_period), freq="Q")
    return [period.end_time.strftime("%Y%m%d") for period in quarters]


def _build_shards(symbols: list[str], periods: list[str], symbols_per_shard: int) -> list[dict[str, Any]]:
    if symbols_per_shard < 1:
        return []
    shards = []
    for index in range(0, len(symbols), symbols_per_shard):
        shard_symbols = symbols[index : index + symbols_per_shard]
        shards.append(
            {
                "shard_id": len(shards) + 1,
                "symbol_count": len(shard_symbols),
                "period_count": len(periods),
                "request_count": len(shard_symbols) * len(periods),
                "first_symbol": shard_symbols[0] if shard_symbols else "",
                "last_symbol": shard_symbols[-1] if shard_symbols else "",
                "symbols": shard_symbols,
            }
        )
    return shards


def _blockers(
    *,
    symbols: list[str],
    periods: list[str],
    symbols_per_shard: int,
    max_requests_per_shard: int,
    shards: list[dict[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if not symbols:
        blockers.append("missing_symbols")
    if not periods:
        blockers.append("missing_periods")
    if symbols_per_shard < 1:
        blockers.append("invalid_symbols_per_shard")
    if max_requests_per_shard < 1:
        blockers.append("invalid_max_requests_per_shard")
    if any(shard["request_count"] > max_requests_per_shard for shard in shards):
        blockers.append("shard_request_count_exceeds_budget")
    return blockers


def _suffix(symbol: str) -> str:
    parts = symbol.split(".")
    return parts[-1].upper() if len(parts) > 1 else ""


def _without_markdown(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "markdown"}
