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

from quant_robot.ops.capacity_safe_price_volume_prescreen import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.dragon_tiger_pit_ic_prescreen import DRAGON_TIGER_DEFAULT_HORIZONS  # noqa: E402
from quant_robot.ops.dragon_tiger_size_residual_repair import (  # noqa: E402
    build_dragon_tiger_size_residual_repair_prescreen,
    write_dragon_tiger_size_residual_repair_prescreen,
)


DEFAULT_PROCESSED_ROOT = Path("data/processed/round232_dragon_tiger_attention_reversal_20260624")
DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_STOCK_BASIC = Path("data/processed/cn_stock_metadata")
DEFAULT_OUTPUT_DIR = Path("data/reports/round233_dragon_tiger_size_residual_repair_20260625")


def run_dragon_tiger_size_residual_repair_cli(
    *,
    processed_root: str | Path = DEFAULT_PROCESSED_ROOT,
    bars_roots: list[str | Path] | tuple[str | Path, ...] = DEFAULT_BARS_ROOTS,
    stock_basic_path: str | Path | None = DEFAULT_STOCK_BASIC,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: list[int] | tuple[int, ...] = DRAGON_TIGER_DEFAULT_HORIZONS,
    execution_lag: int = 1,
    pit_lag_trade_days: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 8,
    min_neutral_rank_ic: float = 0.01,
    min_neutral_ic_t_stat: float = 2.0,
    min_neutral_retention: float = 0.50,
    alpha: float = 0.05,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    result = build_dragon_tiger_size_residual_repair_prescreen(
        processed_root=Path(processed_root),
        bars_roots=[Path(root) for root in bars_roots],
        stock_basic_path=Path(stock_basic_path) if stock_basic_path else None,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        horizons=tuple(horizons),
        execution_lag=execution_lag,
        pit_lag_trade_days=pit_lag_trade_days,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_neutral_rank_ic=min_neutral_rank_ic,
        min_neutral_ic_t_stat=min_neutral_ic_t_stat,
        min_neutral_retention=min_neutral_retention,
        alpha=alpha,
    )
    write_dragon_tiger_size_residual_repair_prescreen(output_dir, result)
    if not allow_not_ready and result["summary"].get("factor_rows", 0) == 0:
        raise RuntimeError("Dragon-Tiger size residual repair produced no factor rows")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Round233 Dragon-Tiger size residual repair PIT IC prescreen.")
    parser.add_argument("--processed-root", default=str(DEFAULT_PROCESSED_ROOT))
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--stock-basic", default=str(DEFAULT_STOCK_BASIC))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--horizon", action="append", type=int, default=[])
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--pit-lag-trade-days", type=int, default=1)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=8)
    parser.add_argument("--min-neutral-rank-ic", type=float, default=0.01)
    parser.add_argument("--min-neutral-ic-t-stat", type=float, default=2.0)
    parser.add_argument("--min-neutral-retention", type=float, default=0.50)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    result = run_dragon_tiger_size_residual_repair_cli(
        processed_root=Path(args.processed_root),
        bars_roots=[Path(root) for root in (args.bars_root or DEFAULT_BARS_ROOTS)],
        stock_basic_path=Path(args.stock_basic) if args.stock_basic else None,
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        horizons=args.horizon or list(DRAGON_TIGER_DEFAULT_HORIZONS),
        execution_lag=args.execution_lag,
        pit_lag_trade_days=args.pit_lag_trade_days,
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        min_neutral_rank_ic=args.min_neutral_rank_ic,
        min_neutral_ic_t_stat=args.min_neutral_ic_t_stat,
        min_neutral_retention=args.min_neutral_retention,
        alpha=args.alpha,
        allow_not_ready=args.allow_not_ready,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "data_window": result.get("data_window", {}),
                "residual_repair_policy": result.get("residual_repair_policy", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
