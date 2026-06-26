from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.cn_stock_tradeability_gate import (
    CNStockTradeabilityPolicy,
    build_cn_stock_tradeability_report,
    write_tradeability_report,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/cn_stock_tradeability_gate")


def run_cn_stock_tradeability_gate(
    *,
    bars_path: str | Path,
    stock_basic_path: str | Path | None = None,
    stk_limit_path: str | Path | None = None,
    suspension_path: str | Path | None = None,
    namechange_path: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    allow_bse: bool = False,
    allow_star: bool = False,
    allow_chinext: bool = False,
    min_listing_days: int = 120,
) -> dict[str, Any]:
    bars = _read_frame(bars_path)
    stock_basic = _read_frame(stock_basic_path) if stock_basic_path is not None else None
    stk_limit = _read_frame(stk_limit_path) if stk_limit_path is not None else None
    suspension = _read_frame(suspension_path) if suspension_path is not None else None
    namechange = _read_frame(namechange_path) if namechange_path is not None else None
    report = build_cn_stock_tradeability_report(
        bars,
        stock_basic,
        CNStockTradeabilityPolicy(
            min_listing_days=min_listing_days,
            allow_bse=allow_bse,
            allow_star=allow_star,
            allow_chinext=allow_chinext,
        ),
        stk_limit=stk_limit,
        suspension=suspension,
        namechange=namechange,
    )
    write_tradeability_report(report, output_dir)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a CN stock tradeability gate report from bars and stock_basic metadata.")
    parser.add_argument("--bars-path", required=True)
    parser.add_argument("--stock-basic-path")
    parser.add_argument("--stk-limit-path")
    parser.add_argument("--suspension-path")
    parser.add_argument("--namechange-path")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--allow-bse", action="store_true")
    parser.add_argument("--allow-star", action="store_true")
    parser.add_argument("--allow-chinext", action="store_true")
    parser.add_argument("--min-listing-days", type=int, default=120)
    args = parser.parse_args()
    report = run_cn_stock_tradeability_gate(
        bars_path=args.bars_path,
        stock_basic_path=args.stock_basic_path,
        stk_limit_path=args.stk_limit_path,
        suspension_path=args.suspension_path,
        namechange_path=args.namechange_path,
        output_dir=args.output_dir,
        allow_bse=args.allow_bse,
        allow_star=args.allow_star,
        allow_chinext=args.allow_chinext,
        min_listing_days=args.min_listing_days,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


def _read_frame(path: str | Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame()
    source = Path(path)
    if source.is_dir():
        files = sorted(source.rglob("*.parquet")) or sorted(source.rglob("*.csv"))
        if not files:
            raise ValueError(f"No parquet or csv files found under {source}")
        return pd.concat([_read_frame(file) for file in files], ignore_index=True)
    suffix = source.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(source)
    if suffix == ".parquet":
        return pd.read_parquet(source)
    raise ValueError(f"Unsupported input file type for {source}")


if __name__ == "__main__":
    main()
