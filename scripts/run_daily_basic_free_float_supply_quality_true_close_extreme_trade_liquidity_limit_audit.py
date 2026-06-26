from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.capacity_safe_price_volume_prescreen import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit import (  # noqa: E402
    DEFAULT_LIMIT_DETECTION_RATIO,
    DEFAULT_MIN_ENTRY_AMOUNT,
    DEFAULT_MIN_LISTING_DAYS,
    DEFAULT_REPAIRED_RERUN_REPORT,
    build_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit,
    write_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_STOCK_METADATA_ROOTS = (Path("data/processed/cn_stock_metadata"),)
DEFAULT_OUTPUT_DIR = Path(
    "data/reports/daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit_round139_20260622"
)


def run_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    stock_metadata_roots: Iterable[str | Path] = DEFAULT_STOCK_METADATA_ROOTS,
    repaired_rerun_report: str | Path = DEFAULT_REPAIRED_RERUN_REPORT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    min_listing_days: int = DEFAULT_MIN_LISTING_DAYS,
    min_entry_amount: float = DEFAULT_MIN_ENTRY_AMOUNT,
    limit_detection_ratio: float = DEFAULT_LIMIT_DETECTION_RATIO,
) -> dict[str, Any]:
    result = build_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit(
        bars_roots=bars_roots,
        stock_metadata_roots=stock_metadata_roots,
        repaired_rerun_report=repaired_rerun_report,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        min_listing_days=min_listing_days,
        min_entry_amount=min_entry_amount,
        limit_detection_ratio=limit_detection_ratio,
    )
    write_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run Round139 tradeability audit for true-close extreme trades from the Round138 repaired rerun."
        )
    )
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--stock-metadata-root", action="append", default=None)
    parser.add_argument("--repaired-rerun-report", default=str(DEFAULT_REPAIRED_RERUN_REPORT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--min-listing-days", type=int, default=DEFAULT_MIN_LISTING_DAYS)
    parser.add_argument("--min-entry-amount", type=float, default=DEFAULT_MIN_ENTRY_AMOUNT)
    parser.add_argument("--limit-detection-ratio", type=float, default=DEFAULT_LIMIT_DETECTION_RATIO)
    args = parser.parse_args()
    result = run_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit_cli(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        stock_metadata_roots=tuple(Path(path) for path in (args.stock_metadata_root or DEFAULT_STOCK_METADATA_ROOTS)),
        repaired_rerun_report=Path(args.repaired_rerun_report),
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        min_listing_days=args.min_listing_days,
        min_entry_amount=args.min_entry_amount,
        limit_detection_ratio=args.limit_detection_ratio,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "gate": result["gate"],
                "promotion_policy": result["promotion_policy"],
                "next_direction": result["next_direction"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
