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

from quant_robot.ops.lowvol_reversal_liquidity_incremental_residual_prescreen import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    build_lowvol_reversal_liquidity_incremental_residual_prescreen,
    write_lowvol_reversal_liquidity_incremental_residual_prescreen,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/lowvol_reversal_liquidity_incremental_residual_prescreen")


def run_lowvol_reversal_liquidity_incremental_residual_prescreen_cli(
    *,
    bars_roots: list[str | Path],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = (5, 10, 20),
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    sample_every_n_dates: int = 5,
) -> dict[str, Any]:
    result = build_lowvol_reversal_liquidity_incremental_residual_prescreen(
        bars_roots=bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        horizons=horizons,
        execution_lag=execution_lag,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_signal_date_amount=min_signal_date_amount,
        sample_every_n_dates=sample_every_n_dates,
    )
    write_lowvol_reversal_liquidity_incremental_residual_prescreen(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run CN stock low-vol/reversal/liquidity incremental residual prescreen."
    )
    parser.add_argument("--bars-root", action="append", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--horizon", type=int, action="append", dest="horizons")
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=20)
    parser.add_argument("--min-signal-date-amount", type=float, default=10_000_000)
    parser.add_argument("--sample-every-n-dates", type=int, default=5)
    args = parser.parse_args()
    result = run_lowvol_reversal_liquidity_incremental_residual_prescreen_cli(
        bars_roots=[Path(root) for root in args.bars_root],
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        horizons=tuple(args.horizons or (5, 10, 20)),
        execution_lag=args.execution_lag,
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        min_signal_date_amount=args.min_signal_date_amount,
        sample_every_n_dates=args.sample_every_n_dates,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "gate": result.get("gate", {}),
                "recommended_post_review_direction": result.get("recommended_post_review_direction"),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
