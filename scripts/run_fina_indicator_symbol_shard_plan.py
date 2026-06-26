from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.fina_indicator_symbol_shard_plan import (  # noqa: E402
    build_fina_indicator_symbol_shard_plan,
    write_fina_indicator_symbol_shard_plan,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/fina_indicator_symbol_shard_plan")


def run_fina_indicator_symbol_shard_plan_cli(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    start_period: str = "2015-03-31",
    end_period: str = "2025-12-31",
    symbols: list[str] | None = None,
    symbols_file: str | Path | None = None,
    stock_basic_root: str | Path | None = None,
    symbols_per_shard: int = 100,
    max_requests_per_shard: int = 5000,
    exclude_suffixes: list[str] | None = None,
    stratify_by: list[str] | None = None,
    allow_blocked_plan: bool = False,
) -> dict[str, Any]:
    all_symbols = list(symbols or [])
    all_symbols.extend(_read_symbols_file(symbols_file))
    stock_basic_metadata = _read_stock_basic_metadata(stock_basic_root)
    all_symbols.extend(_symbols_from_metadata(stock_basic_metadata))
    result = build_fina_indicator_symbol_shard_plan(
        symbols=all_symbols,
        start_period=start_period,
        end_period=end_period,
        symbols_per_shard=symbols_per_shard,
        max_requests_per_shard=max_requests_per_shard,
        exclude_suffixes=exclude_suffixes,
        symbol_metadata=stock_basic_metadata,
        stratify_by=stratify_by,
    )
    write_fina_indicator_symbol_shard_plan(output_dir, result)
    if not allow_blocked_plan and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Fina indicator symbol shard plan is blocked: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a compact symbol-universe shard plan for Tushare fina_indicator backfill.")
    parser.add_argument("--symbols", default="", help="Comma-separated Tushare symbols.")
    parser.add_argument("--symbols-file", default="", help="CSV/text file with symbol or ts_code values.")
    parser.add_argument("--stock-basic-root", default="", help="Local stock_basic dataset root to scan.")
    parser.add_argument("--start-period", default="2015-03-31")
    parser.add_argument("--end-period", default="2025-12-31")
    parser.add_argument("--symbols-per-shard", type=int, default=100)
    parser.add_argument("--max-requests-per-shard", type=int, default=5000)
    parser.add_argument("--exclude-suffixes", default="", help="Comma-separated suffixes to exclude, for example BJ.")
    parser.add_argument(
        "--stratify-by",
        default="",
        help="Comma-separated metadata columns used to round-robin symbols, for example industry,exchange,list_year.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--allow-blocked-plan", action="store_true")
    args = parser.parse_args()
    result = run_fina_indicator_symbol_shard_plan_cli(
        symbols=_parse_symbols(args.symbols),
        symbols_file=Path(args.symbols_file) if args.symbols_file else None,
        stock_basic_root=Path(args.stock_basic_root) if args.stock_basic_root else None,
        start_period=args.start_period,
        end_period=args.end_period,
        symbols_per_shard=args.symbols_per_shard,
        max_requests_per_shard=args.max_requests_per_shard,
        exclude_suffixes=_parse_symbols(args.exclude_suffixes),
        stratify_by=_parse_symbols(args.stratify_by),
        output_dir=Path(args.output_dir),
        allow_blocked_plan=args.allow_blocked_plan,
    )
    print(json.dumps({"summary": result["summary"], "output_dir": args.output_dir}, indent=2, sort_keys=True))


def _parse_symbols(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _read_symbols_file(path: str | Path | None) -> list[str]:
    if not path:
        return []
    symbol_path = Path(path)
    text = symbol_path.read_text(encoding="utf-8-sig")
    first_line = text.splitlines()[0] if text.splitlines() else ""
    if "," in first_line or first_line.lower() in {"symbol", "ts_code"}:
        rows = csv.DictReader(text.splitlines())
        if rows.fieldnames and "symbol" in rows.fieldnames:
            return [row["symbol"] for row in rows if row.get("symbol")]
        if rows.fieldnames and "ts_code" in rows.fieldnames:
            return [row["ts_code"] for row in rows if row.get("ts_code")]
    return [line.strip() for line in text.splitlines() if line.strip()]


def _read_stock_basic_metadata(root: str | Path | None) -> pd.DataFrame | None:
    if not root:
        return None
    root_path = Path(root)
    files = [root_path] if root_path.is_file() else sorted(root_path.rglob("*"))
    frames: list[pd.DataFrame] = []
    for path in files:
        if not path.is_file():
            continue
        if path.suffix.lower() == ".parquet":
            frame = pd.read_parquet(path, columns=None)
        elif path.suffix.lower() == ".csv":
            frame = pd.read_csv(path)
        else:
            continue
        frames.append(frame)
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


def _symbols_from_metadata(metadata: pd.DataFrame | None) -> list[str]:
    if metadata is None or metadata.empty:
        return []
    if "symbol" in metadata.columns:
        return [str(value) for value in metadata["symbol"].dropna()]
    if "ts_code" in metadata.columns:
        return [str(value) for value in metadata["ts_code"].dropna()]
    return []


if __name__ == "__main__":
    main()
