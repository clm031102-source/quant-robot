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

from quant_robot.ops.financial_statement_symbol_shard_plan import (  # noqa: E402
    build_financial_statement_symbol_shard_plan,
    write_financial_statement_symbol_shard_plan,
)
from scripts.run_fina_indicator_symbol_shard_plan import (  # noqa: E402
    _parse_symbols,
    _read_stock_basic_metadata,
    _read_symbols_file,
    _symbols_from_metadata,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/financial_statement_symbol_shard_plan")


def run_financial_statement_symbol_shard_plan_cli(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    start_period: str = "2015-03-31",
    end_period: str = "2025-12-31",
    symbols: list[str] | None = None,
    symbols_file: str | Path | None = None,
    stock_basic_root: str | Path | None = None,
    symbols_per_shard: int = 50,
    max_endpoint_requests_per_shard: int = 3000,
    exclude_suffixes: list[str] | None = None,
    stratify_by: list[str] | None = None,
    allow_blocked_plan: bool = False,
) -> dict[str, Any]:
    all_symbols = list(symbols or [])
    all_symbols.extend(_read_symbols_file(symbols_file))
    stock_basic_metadata = _read_stock_basic_metadata(stock_basic_root)
    all_symbols.extend(_symbols_from_metadata(stock_basic_metadata))
    result = build_financial_statement_symbol_shard_plan(
        symbols=all_symbols,
        start_period=start_period,
        end_period=end_period,
        symbols_per_shard=symbols_per_shard,
        max_endpoint_requests_per_shard=max_endpoint_requests_per_shard,
        exclude_suffixes=exclude_suffixes,
        symbol_metadata=stock_basic_metadata,
        stratify_by=stratify_by,
    )
    write_financial_statement_symbol_shard_plan(output_dir, result)
    if not allow_blocked_plan and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Financial statement symbol shard plan is blocked: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a symbol-universe shard plan for Tushare income/balance/cashflow backfill."
    )
    parser.add_argument("--symbols", default="", help="Comma-separated Tushare symbols.")
    parser.add_argument("--symbols-file", default="", help="CSV/text file with symbol or ts_code values.")
    parser.add_argument("--stock-basic-root", default="", help="Local stock_basic dataset root to scan.")
    parser.add_argument("--start-period", default="2015-03-31")
    parser.add_argument("--end-period", default="2025-12-31")
    parser.add_argument("--symbols-per-shard", type=int, default=50)
    parser.add_argument("--max-endpoint-requests-per-shard", type=int, default=3000)
    parser.add_argument("--exclude-suffixes", default="", help="Comma-separated suffixes to exclude, for example BJ.")
    parser.add_argument(
        "--stratify-by",
        default="",
        help="Comma-separated metadata columns used to round-robin symbols, for example industry,exchange,list_year.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--allow-blocked-plan", action="store_true")
    args = parser.parse_args()
    result = run_financial_statement_symbol_shard_plan_cli(
        symbols=_parse_symbols(args.symbols),
        symbols_file=Path(args.symbols_file) if args.symbols_file else None,
        stock_basic_root=Path(args.stock_basic_root) if args.stock_basic_root else None,
        start_period=args.start_period,
        end_period=args.end_period,
        symbols_per_shard=args.symbols_per_shard,
        max_endpoint_requests_per_shard=args.max_endpoint_requests_per_shard,
        exclude_suffixes=_parse_symbols(args.exclude_suffixes),
        stratify_by=_parse_symbols(args.stratify_by),
        output_dir=Path(args.output_dir),
        allow_blocked_plan=args.allow_blocked_plan,
    )
    print(json.dumps({"summary": result["summary"], "output_dir": args.output_dir}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
