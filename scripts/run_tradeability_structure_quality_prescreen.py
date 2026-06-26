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
from quant_robot.ops.tradeability_structure_quality_prescreen import (  # noqa: E402
    DEFAULT_CANDIDATE_PLAN,
    DEFAULT_TRADEABILITY_MASK_ROOT,
    build_tradeability_structure_quality_prescreen,
    write_tradeability_structure_quality_prescreen,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_OUTPUT_DIR = Path("data/reports/tradeability_structure_quality_prescreen")


def run_tradeability_structure_quality_prescreen_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    tradeability_mask_root: str | Path = DEFAULT_TRADEABILITY_MASK_ROOT,
    candidate_plan_json: str | Path = DEFAULT_CANDIDATE_PLAN,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
) -> dict[str, Any]:
    result = build_tradeability_structure_quality_prescreen(
        bars_roots=bars_roots,
        tradeability_mask_root=tradeability_mask_root,
        candidate_plan_json=candidate_plan_json,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        horizons=horizons,
        execution_lag=execution_lag,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_signal_date_amount=min_signal_date_amount,
    )
    write_tradeability_structure_quality_prescreen(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run CN stock tradeability-structure IC, quintile, turnover, and multiple-testing prescreen."
    )
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--tradeability-mask-root", default=str(DEFAULT_TRADEABILITY_MASK_ROOT))
    parser.add_argument("--candidate-plan-json", default=str(DEFAULT_CANDIDATE_PLAN))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--horizons", default=",".join(str(horizon) for horizon in DEFAULT_HORIZONS))
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=20)
    parser.add_argument("--min-signal-date-amount", type=float, default=10_000_000)
    args = parser.parse_args()
    bars_roots = tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS))
    horizons = tuple(int(item.strip()) for item in args.horizons.split(",") if item.strip())
    result = run_tradeability_structure_quality_prescreen_cli(
        bars_roots=bars_roots,
        tradeability_mask_root=Path(args.tradeability_mask_root),
        candidate_plan_json=Path(args.candidate_plan_json),
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        horizons=horizons,
        execution_lag=args.execution_lag,
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        min_signal_date_amount=args.min_signal_date_amount,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "data_window": result.get("data_window", {}),
                "tradeability_mask_policy": result.get("tradeability_mask_policy", {}),
                "promotion_policy": result.get("promotion_policy", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
