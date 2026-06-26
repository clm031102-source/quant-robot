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
from quant_robot.ops.daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit import (  # noqa: E402
    DEFAULT_EXTREME_ADJ_RETURN_ABS_THRESHOLD,
    DEFAULT_PLAUSIBLE_CLOSE_RETURN_ABS_THRESHOLD,
    DEFAULT_PREFLIGHT_REPORT,
    DEFAULT_PRICE_RATIO_JUMP_THRESHOLD,
    build_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit,
    write_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_OUTPUT_DIR = Path(
    "data/reports/daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit_round137_20260622"
)


def run_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    preflight_report: str | Path = DEFAULT_PREFLIGHT_REPORT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    price_ratio_jump_threshold: float = DEFAULT_PRICE_RATIO_JUMP_THRESHOLD,
    plausible_close_return_abs_threshold: float = DEFAULT_PLAUSIBLE_CLOSE_RETURN_ABS_THRESHOLD,
    extreme_adj_return_abs_threshold: float = DEFAULT_EXTREME_ADJ_RETURN_ABS_THRESHOLD,
) -> dict[str, Any]:
    result = build_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit(
        bars_roots=bars_roots,
        preflight_report=preflight_report,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        price_ratio_jump_threshold=price_ratio_jump_threshold,
        plausible_close_return_abs_threshold=plausible_close_return_abs_threshold,
        extreme_adj_return_abs_threshold=extreme_adj_return_abs_threshold,
    )
    write_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Round137 extreme trade data-quality audit for daily-basic free-float supply quality."
    )
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--preflight-report", default=str(DEFAULT_PREFLIGHT_REPORT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--price-ratio-jump-threshold", type=float, default=DEFAULT_PRICE_RATIO_JUMP_THRESHOLD)
    parser.add_argument(
        "--plausible-close-return-abs-threshold",
        type=float,
        default=DEFAULT_PLAUSIBLE_CLOSE_RETURN_ABS_THRESHOLD,
    )
    parser.add_argument(
        "--extreme-adj-return-abs-threshold",
        type=float,
        default=DEFAULT_EXTREME_ADJ_RETURN_ABS_THRESHOLD,
    )
    args = parser.parse_args()
    result = run_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit_cli(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        preflight_report=Path(args.preflight_report),
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        price_ratio_jump_threshold=args.price_ratio_jump_threshold,
        plausible_close_return_abs_threshold=args.plausible_close_return_abs_threshold,
        extreme_adj_return_abs_threshold=args.extreme_adj_return_abs_threshold,
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
