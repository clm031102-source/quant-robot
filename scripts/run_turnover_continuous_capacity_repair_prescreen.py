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
    DEFAULT_HORIZONS,
)
from quant_robot.ops.turnover_continuous_capacity_repair_prescreen import (  # noqa: E402
    DEFAULT_MAX_PARTICIPATION,
    DEFAULT_PORTFOLIO_CAPITAL,
    DEFAULT_TOP_N,
    build_turnover_continuous_capacity_repair_prescreen,
    write_turnover_continuous_capacity_repair_prescreen,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_FACTOR_INPUT_ROOT = Path("configs/cn_stock_authority_daily_basic_inputs_2015_2025.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/turnover_continuous_capacity_repair_prescreen")


def run_turnover_continuous_capacity_repair_prescreen_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    factor_input_root: str | Path = DEFAULT_FACTOR_INPUT_ROOT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    portfolio_capital: float = DEFAULT_PORTFOLIO_CAPITAL,
    top_n: int = DEFAULT_TOP_N,
    max_participation: float = DEFAULT_MAX_PARTICIPATION,
) -> dict[str, Any]:
    result = build_turnover_continuous_capacity_repair_prescreen(
        bars_roots=bars_roots,
        factor_input_root=factor_input_root,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        horizons=horizons,
        execution_lag=execution_lag,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_signal_date_amount=min_signal_date_amount,
        portfolio_capital=portfolio_capital,
        top_n=top_n,
        max_participation=max_participation,
    )
    write_turnover_continuous_capacity_repair_prescreen(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Round124 IC, quantile, turnover, and capacity prescreen for continuous low-turnover capacity repairs."
    )
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--factor-input-root", default=str(DEFAULT_FACTOR_INPUT_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--horizons", default=",".join(str(horizon) for horizon in DEFAULT_HORIZONS))
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=20)
    parser.add_argument("--min-signal-date-amount", type=float, default=10_000_000)
    parser.add_argument("--portfolio-capital", type=float, default=DEFAULT_PORTFOLIO_CAPITAL)
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    parser.add_argument("--max-participation", type=float, default=DEFAULT_MAX_PARTICIPATION)
    args = parser.parse_args()
    bars_roots = tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS))
    horizons = tuple(int(item.strip()) for item in args.horizons.split(",") if item.strip())
    result = run_turnover_continuous_capacity_repair_prescreen_cli(
        bars_roots=bars_roots,
        factor_input_root=Path(args.factor_input_root),
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        horizons=horizons,
        execution_lag=args.execution_lag,
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        min_signal_date_amount=args.min_signal_date_amount,
        portfolio_capital=args.portfolio_capital,
        top_n=args.top_n,
        max_participation=args.max_participation,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "data_window": result.get("data_window", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
