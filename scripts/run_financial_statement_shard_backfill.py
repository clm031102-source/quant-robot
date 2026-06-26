from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.adapters.tushare_adapter import TushareAdapter  # noqa: E402
from quant_robot.data.ingest.tushare_financial_statements import (  # noqa: E402
    ENDPOINT_COLUMNS,
    REQUIRED_COLUMN_GROUPS,
    run_tushare_financial_statement_ingest,
)
from quant_robot.ops.tushare_financial_pit_readiness import audit_tushare_financial_pit_readiness  # noqa: E402


DEFAULT_PLAN_JSON = Path("data/reports/round236_financial_statement_symbol_shard_plan_20260625/financial_statement_symbol_shard_plan.json")
DEFAULT_OUTPUT_DIR = Path("data/processed/round236_financial_statement_shard_backfill")
STAGE = "tushare_financial_statement_shard_backfill"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def run_financial_statement_shard_backfill_cli(
    *,
    plan_json: str | Path = DEFAULT_PLAN_JSON,
    shard_id: int,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    symbol_offset: int = 0,
    symbol_limit: int | None = None,
    max_endpoint_requests: int = 3000,
    adapter_max_retries: int = 3,
    adapter_retry_sleep_seconds: float = 1.0,
    adapter_request_sleep_seconds: float = 0.0,
    adapter: object | None = None,
) -> dict[str, Any]:
    plan = _read_plan(plan_json)
    shard = _select_shard(plan, shard_id)
    periods = [str(period) for period in plan.get("periods", []) or []]
    symbols = _slice_symbols([str(symbol) for symbol in shard.get("symbols", []) or []], symbol_offset, symbol_limit)
    endpoint_request_count = len(symbols) * len(periods) * len(ENDPOINT_COLUMNS)
    if endpoint_request_count > max_endpoint_requests:
        raise RuntimeError(
            "Financial statement shard endpoint request budget blocked: "
            f"{endpoint_request_count} exceeds {max_endpoint_requests}"
        )
    if not symbols:
        raise RuntimeError("Financial statement shard backfill has no symbols after offset/limit slicing")
    if not periods:
        raise RuntimeError("Financial statement shard backfill plan has no periods")

    output_path = Path(output_dir)
    active_adapter = adapter or TushareAdapter(
        max_retries=adapter_max_retries,
        retry_sleep_seconds=adapter_retry_sleep_seconds,
        request_sleep_seconds=adapter_request_sleep_seconds,
    )
    ingest = run_tushare_financial_statement_ingest(
        active_adapter,
        periods,
        output_path,
        resume=True,
        market="CN",
        ts_codes=symbols,
        empty_response_policy="record",
    )
    readiness = audit_tushare_financial_pit_readiness(
        [output_path],
        required_column_groups=REQUIRED_COLUMN_GROUPS,
    )
    result = {
        "stage": STAGE,
        "plan_json": str(plan_json),
        "shard": _shard_without_symbols(shard),
        "selected_symbols": symbols,
        "periods": periods,
        "ingest": ingest,
        "readiness": _without_markdown(readiness),
        "summary": {
            "passes": bool(readiness["summary"]["passes"]),
            "shard_id": shard_id,
            "symbol_offset": symbol_offset,
            "symbol_limit": symbol_limit,
            "symbol_count": len(symbols),
            "period_count": len(periods),
            "endpoint_count": len(ENDPOINT_COLUMNS),
            "endpoint_request_count": endpoint_request_count,
            "max_endpoint_requests": max_endpoint_requests,
            "processed_rows": ingest["processed_rows"],
            "empty_request_count": len(ingest.get("empty_requests", []) or []),
            "skipped_request_count": len(ingest.get("skipped_requests", []) or []),
            "required_column_group_count": readiness["summary"]["required_column_group_count"],
            "required_column_groups_passing": readiness["summary"]["required_column_groups_passing"],
            "readiness_blockers": readiness["summary"]["blockers"],
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    _write_report(output_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Tushare financial statement backfill shard or subshard.")
    parser.add_argument("--plan-json", default=str(DEFAULT_PLAN_JSON))
    parser.add_argument("--shard-id", type=int, required=True)
    parser.add_argument("--symbol-offset", type=int, default=0)
    parser.add_argument("--symbol-limit", type=int, default=0)
    parser.add_argument("--max-endpoint-requests", type=int, default=3000)
    parser.add_argument("--adapter-max-retries", type=int, default=3)
    parser.add_argument("--adapter-retry-sleep-seconds", type=float, default=1.0)
    parser.add_argument("--adapter-request-sleep-seconds", type=float, default=0.0)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    result = run_financial_statement_shard_backfill_cli(
        plan_json=Path(args.plan_json),
        shard_id=args.shard_id,
        symbol_offset=args.symbol_offset,
        symbol_limit=args.symbol_limit or None,
        max_endpoint_requests=args.max_endpoint_requests,
        adapter_max_retries=args.adapter_max_retries,
        adapter_retry_sleep_seconds=args.adapter_retry_sleep_seconds,
        adapter_request_sleep_seconds=args.adapter_request_sleep_seconds,
        output_dir=Path(args.output_dir),
    )
    print(json.dumps({"summary": result["summary"], "output_dir": args.output_dir}, indent=2, sort_keys=True))


def _read_plan(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _select_shard(plan: dict[str, Any], shard_id: int) -> dict[str, Any]:
    for shard in plan.get("shards", []) or []:
        if int(shard.get("shard_id", -1)) == shard_id:
            return dict(shard)
    raise RuntimeError(f"Financial statement shard id not found in plan: {shard_id}")


def _slice_symbols(symbols: list[str], offset: int, limit: int | None) -> list[str]:
    if offset < 0:
        raise ValueError("symbol_offset must be non-negative")
    sliced = symbols[offset:]
    if limit is not None:
        if limit < 0:
            raise ValueError("symbol_limit must be non-negative")
        sliced = sliced[:limit]
    return sliced


def _shard_without_symbols(shard: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in shard.items() if key != "symbols"}


def _write_report(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "financial_statement_shard_backfill.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    (output_dir / "financial_statement_shard_backfill.md").write_text(
        _render_markdown(result),
        encoding="utf-8",
    )


def _render_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Financial Statement Shard Backfill",
        "",
        f"- Stage: {result['stage']}",
        f"- Passes: {summary['passes']}",
        f"- Shard id: {summary['shard_id']}",
        f"- Symbol offset: {summary['symbol_offset']}",
        f"- Symbol limit: {summary['symbol_limit']}",
        f"- Symbols: {summary['symbol_count']}",
        f"- Periods: {summary['period_count']}",
        f"- Endpoint requests: {summary['endpoint_request_count']}",
        f"- Max endpoint requests: {summary['max_endpoint_requests']}",
        f"- Processed rows: {summary['processed_rows']}",
        f"- Required column groups passing: {summary['required_column_groups_passing']} / {summary['required_column_group_count']}",
        f"- Empty requests: {summary['empty_request_count']}",
        f"- Skipped requests: {summary['skipped_request_count']}",
        f"- Readiness blockers: {', '.join(summary['readiness_blockers']) or 'none'}",
        f"- Live boundary allowed: {result['live_boundary_allowed']}",
        f"- Safety: {result['safety']}",
        "",
        "## Selected Symbols",
        "",
    ]
    for symbol in result.get("selected_symbols", []) or []:
        lines.append(f"- `{symbol}`")
    return "\n".join(lines) + "\n"


def _without_markdown(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "markdown"}


if __name__ == "__main__":
    main()
