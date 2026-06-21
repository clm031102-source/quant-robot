from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.fina_indicator_backfill_plan import (  # noqa: E402
    build_fina_indicator_backfill_plan,
    write_fina_indicator_backfill_plan,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/fina_indicator_backfill_plan")


def run_fina_indicator_backfill_plan_cli(
    *,
    symbols: list[str],
    start_period: str,
    end_period: str,
    batch_size: int = 500,
    max_requests: int | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    symbols_file: str | Path | None = None,
    allow_blocked_plan: bool = False,
) -> dict[str, Any]:
    all_symbols = list(symbols) + _read_symbols_file(symbols_file)
    result = build_fina_indicator_backfill_plan(
        symbols=all_symbols,
        start_period=start_period,
        end_period=end_period,
        batch_size=batch_size,
        max_requests=max_requests,
    )
    write_fina_indicator_backfill_plan(output_dir, result)
    if not allow_blocked_plan and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Fina indicator backfill plan is blocked: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan a resume-safe Tushare fina_indicator long-history backfill.")
    parser.add_argument("--symbols", default="", help="Comma-separated Tushare symbols, for example 000001.SZ,600519.SH.")
    parser.add_argument("--symbols-file", default="", help="CSV/text file with symbol or ts_code values.")
    parser.add_argument("--start-period", default="2015-03-31")
    parser.add_argument("--end-period", default="2025-12-31")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--max-requests", type=int, default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--allow-blocked-plan", action="store_true")
    args = parser.parse_args()
    result = run_fina_indicator_backfill_plan_cli(
        symbols=_parse_symbols(args.symbols),
        symbols_file=Path(args.symbols_file) if args.symbols_file else None,
        start_period=args.start_period,
        end_period=args.end_period,
        batch_size=args.batch_size,
        max_requests=args.max_requests,
        output_dir=Path(args.output_dir),
        allow_blocked_plan=args.allow_blocked_plan,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _parse_symbols(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _read_symbols_file(path: str | Path | None) -> list[str]:
    if not path:
        return []
    symbol_path = Path(path)
    if not symbol_path.exists():
        raise FileNotFoundError(f"Symbols file does not exist: {symbol_path}")
    text = symbol_path.read_text(encoding="utf-8-sig")
    first_line = text.splitlines()[0] if text.splitlines() else ""
    if "," in first_line or first_line.lower() in {"symbol", "ts_code"}:
        rows = csv.DictReader(text.splitlines())
        if rows.fieldnames and "symbol" in rows.fieldnames:
            return [row["symbol"] for row in rows if row.get("symbol")]
        if rows.fieldnames and "ts_code" in rows.fieldnames:
            return [row["ts_code"] for row in rows if row.get("ts_code")]
    return [line.strip() for line in text.splitlines() if line.strip()]


if __name__ == "__main__":
    main()
