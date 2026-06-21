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
from quant_robot.data.ingest.tushare_financial_inputs import run_tushare_fina_indicator_ingest  # noqa: E402
from quant_robot.ops.fina_indicator_backfill_plan import build_fina_indicator_backfill_plan  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("data/processed/tushare_fina_indicator_limited_backfill_smoke")


def run_fina_indicator_limited_backfill_smoke_cli(
    *,
    symbols: list[str],
    start_period: str,
    end_period: str,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    batch_size: int = 500,
    max_requests: int = 200,
    adapter: object | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    plan = build_fina_indicator_backfill_plan(
        symbols=symbols,
        start_period=start_period,
        end_period=end_period,
        batch_size=batch_size,
        max_requests=max_requests,
    )
    if not plan["summary"]["passes"]:
        blockers = ", ".join(plan["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Fina indicator limited smoke request budget blocked: {blockers}")
    ingest = run_tushare_fina_indicator_ingest(
        adapter or TushareAdapter(),
        list(plan["periods"]),
        output_path,
        resume=True,
        market="CN",
        ts_codes=list(plan["symbols"]),
        empty_response_policy="record",
    )
    result = {
        "stage": "tushare_fina_indicator_limited_backfill_smoke",
        "plan": _without_markdown(plan),
        "ingest": ingest,
        "summary": {
            "passes": True,
            "symbol_count": plan["summary"]["symbol_count"],
            "period_count": plan["summary"]["period_count"],
            "request_count": plan["summary"]["request_count"],
            "processed_rows": ingest["processed_rows"],
            "empty_request_count": len(ingest.get("empty_requests", []) or []),
            "skipped_request_count": len(ingest.get("skipped_requests", []) or []),
        },
        "live_boundary_allowed": False,
        "safety": "Research-to-review only. No broker connection, no account reads, no order placement, no live trading.",
    }
    _write_report(output_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a limited-symbol Tushare fina_indicator long-history backfill smoke.")
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols, for example 000001.SZ,600519.SH.")
    parser.add_argument("--start-period", default="2015-03-31")
    parser.add_argument("--end-period", default="2025-12-31")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--max-requests", type=int, default=200)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    result = run_fina_indicator_limited_backfill_smoke_cli(
        symbols=_parse_symbols(args.symbols),
        start_period=args.start_period,
        end_period=args.end_period,
        batch_size=args.batch_size,
        max_requests=args.max_requests,
        output_dir=Path(args.output_dir),
    )
    print(json.dumps({"summary": result["summary"], "output_dir": args.output_dir}, indent=2, sort_keys=True))


def _parse_symbols(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _write_report(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "limited_backfill_smoke.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    (output_dir / "limited_backfill_smoke.md").write_text(_render_markdown(result), encoding="utf-8")


def _render_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Fina Indicator Limited Backfill Smoke",
        "",
        f"- Stage: {result['stage']}",
        f"- Passes: {summary['passes']}",
        f"- Symbols: {summary['symbol_count']}",
        f"- Periods: {summary['period_count']}",
        f"- Requests: {summary['request_count']}",
        f"- Processed rows: {summary['processed_rows']}",
        f"- Empty requests: {summary['empty_request_count']}",
        f"- Skipped requests: {summary['skipped_request_count']}",
        f"- Live boundary allowed: {result['live_boundary_allowed']}",
        f"- Safety: {result['safety']}",
        "",
        "## Empty Request Preview",
        "",
    ]
    empty_requests = result["ingest"].get("empty_requests", []) or []
    if not empty_requests:
        lines.append("- none")
    else:
        for request in empty_requests[:20]:
            lines.append(f"- `{request}`")
    return "\n".join(lines) + "\n"


def _without_markdown(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "markdown"}


if __name__ == "__main__":
    main()
