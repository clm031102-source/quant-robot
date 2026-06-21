from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from scripts.run_fina_indicator_limited_backfill_smoke import (  # noqa: E402
    run_fina_indicator_limited_backfill_smoke_cli,
)
from scripts.run_tushare_financial_pit_readiness import run_tushare_financial_pit_readiness_cli  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("data/processed/tushare_fina_indicator_shard_backfill_smoke")
DEFAULT_PIT_READINESS_OUTPUT_DIR = Path("data/reports/tushare_financial_pit_readiness_shard_backfill_smoke")
STAGE = "tushare_fina_indicator_shard_backfill_smoke"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def run_fina_indicator_shard_backfill_smoke_cli(
    *,
    shard_plan_json: str | Path,
    shard_id: int,
    max_symbols: int,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    pit_readiness_output_dir: str | Path = DEFAULT_PIT_READINESS_OUTPUT_DIR,
    batch_size: int = 500,
    max_requests: int = 500,
    adapter: object | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    pit_output_path = Path(pit_readiness_output_dir)
    plan = _read_shard_plan(shard_plan_json)
    periods = list(plan.get("periods", []) or [])
    shard = _find_shard(plan, shard_id)
    selected_symbols = list(shard.get("symbols", []) or [])[:max_symbols]
    selected_request_count = len(selected_symbols) * len(periods)
    if selected_request_count > max_requests:
        raise RuntimeError(
            "Fina indicator shard smoke request budget blocked: "
            f"selected_requests={selected_request_count} max_requests={max_requests}"
        )
    if not periods:
        raise RuntimeError("Fina indicator shard smoke request budget blocked: missing_periods")
    limited = run_fina_indicator_limited_backfill_smoke_cli(
        adapter=adapter,
        symbols=selected_symbols,
        start_period=_period_to_date_arg(periods[0]),
        end_period=_period_to_date_arg(periods[-1]),
        batch_size=batch_size,
        max_requests=max_requests,
        output_dir=output_path,
    )
    pit_readiness = run_tushare_financial_pit_readiness_cli(
        roots=[output_path],
        output_dir=pit_output_path,
        allow_not_ready=False,
    )
    result = {
        "stage": STAGE,
        "source_shard_plan": str(Path(shard_plan_json)),
        "shard": {
            "shard_id": shard_id,
            "source_symbol_count": shard.get("symbol_count", len(shard.get("symbols", []) or [])),
            "selected_symbols": selected_symbols,
        },
        "periods": periods,
        "limited_smoke": limited,
        "pit_readiness": pit_readiness,
        "summary": {
            "passes": bool(limited["summary"]["passes"] and pit_readiness["summary"]["passes"]),
            "shard_id": shard_id,
            "selected_symbol_count": len(selected_symbols),
            "period_count": len(periods),
            "request_count": selected_request_count,
            "processed_rows": limited["summary"]["processed_rows"],
            "empty_request_count": limited["summary"]["empty_request_count"],
            "skipped_request_count": limited["summary"]["skipped_request_count"],
            "pit_readiness_passes": pit_readiness["summary"]["passes"],
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    _write_report(output_path, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a first-N symbol smoke from a fina_indicator shard plan.")
    parser.add_argument("--shard-plan-json", required=True)
    parser.add_argument("--shard-id", type=int, default=1)
    parser.add_argument("--max-symbols", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--max-requests", type=int, default=500)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--pit-readiness-output-dir", default=str(DEFAULT_PIT_READINESS_OUTPUT_DIR))
    args = parser.parse_args()
    result = run_fina_indicator_shard_backfill_smoke_cli(
        shard_plan_json=Path(args.shard_plan_json),
        shard_id=args.shard_id,
        max_symbols=args.max_symbols,
        batch_size=args.batch_size,
        max_requests=args.max_requests,
        output_dir=Path(args.output_dir),
        pit_readiness_output_dir=Path(args.pit_readiness_output_dir),
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "output_dir": str(Path(args.output_dir)),
                "pit_readiness_output_dir": str(Path(args.pit_readiness_output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_shard_plan(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _find_shard(plan: dict[str, Any], shard_id: int) -> dict[str, Any]:
    for shard in plan.get("shards", []) or []:
        if int(shard.get("shard_id", -1)) == shard_id:
            return shard
    raise RuntimeError(f"Fina indicator shard smoke request budget blocked: missing_shard_{shard_id}")


def _period_to_date_arg(period: str) -> str:
    return datetime.strptime(period, "%Y%m%d").date().isoformat()


def _write_report(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "shard_backfill_smoke.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    (output_dir / "shard_backfill_smoke.md").write_text(_render_markdown(result), encoding="utf-8")


def _render_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Fina Indicator Shard Backfill Smoke",
        "",
        f"- Stage: {result['stage']}",
        f"- Passes: {summary['passes']}",
        f"- Source shard plan: `{result['source_shard_plan']}`",
        f"- Shard id: {summary['shard_id']}",
        f"- Selected symbols: {summary['selected_symbol_count']}",
        f"- Periods: {summary['period_count']}",
        f"- Requests: {summary['request_count']}",
        f"- Processed rows: {summary['processed_rows']}",
        f"- Empty requests: {summary['empty_request_count']}",
        f"- Skipped requests: {summary['skipped_request_count']}",
        f"- PIT readiness passes: {summary['pit_readiness_passes']}",
        f"- Live boundary allowed: {result['live_boundary_allowed']}",
        f"- Safety: {result['safety']}",
        "",
        "## Selected Symbols",
        "",
    ]
    for symbol in result["shard"].get("selected_symbols", []):
        lines.append(f"- `{symbol}`")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
