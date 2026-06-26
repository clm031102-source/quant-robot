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
from quant_robot.ops.financial_pit_post_announcement_gap_reversal_residual_prescreen import (  # noqa: E402
    build_financial_pit_post_announcement_gap_reversal_residual_prescreen,
    write_financial_pit_post_announcement_gap_reversal_residual_prescreen,
)


DEFAULT_FINANCIAL_ROOT = Path("data/processed/round202_financial_pit_signal_filtered_20260623")
DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_DAILY_BASIC_ROOTS = (Path("data/processed/office_desktop_20260617_daily_basic_factor_inputs"),)
DEFAULT_STOCK_BASIC = Path("data/processed/cn_stock_metadata")
DEFAULT_PREREGISTRATION_JSON = Path(
    "data/reports/financial_pit_post_announcement_gap_reversal_preregistration_round223_20260624/"
    "financial_pit_post_announcement_gap_reversal_preregistration.json"
)
DEFAULT_OUTPUT_DIR = Path("data/reports/financial_pit_post_announcement_gap_reversal_residual_prescreen_round223_20260624")


def run_financial_pit_post_announcement_gap_reversal_residual_prescreen_cli(
    *,
    financial_root: str | Path = DEFAULT_FINANCIAL_ROOT,
    bars_roots: list[str | Path] | tuple[str | Path, ...] = DEFAULT_BARS_ROOTS,
    preregistration_json: str | Path = DEFAULT_PREREGISTRATION_JSON,
    candidate_plan_gate_json: str | Path | None = None,
    stock_basic_path: str | Path | None = DEFAULT_STOCK_BASIC,
    daily_basic_roots: list[str | Path] | tuple[str | Path, ...] = DEFAULT_DAILY_BASIC_ROOTS,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: list[int] | tuple[int, ...] = (5,),
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 8,
    min_neutral_rank_ic: float = 0.01,
    min_neutral_ic_t_stat: float = 2.0,
    min_neutral_retention: float = 0.35,
    reference_high_corr_threshold: float = 0.90,
    reference_mean_abs_corr_threshold: float = 0.70,
    alpha: float = 0.05,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    result = build_financial_pit_post_announcement_gap_reversal_residual_prescreen(
        financial_root=Path(financial_root),
        bars_roots=[Path(root) for root in bars_roots],
        preregistration_json=Path(preregistration_json),
        candidate_plan_gate_json=Path(candidate_plan_gate_json) if candidate_plan_gate_json else None,
        stock_basic_path=Path(stock_basic_path) if stock_basic_path else None,
        daily_basic_roots=[Path(root) for root in daily_basic_roots],
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        horizons=tuple(horizons),
        execution_lag=execution_lag,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_neutral_rank_ic=min_neutral_rank_ic,
        min_neutral_ic_t_stat=min_neutral_ic_t_stat,
        min_neutral_retention=min_neutral_retention,
        reference_high_corr_threshold=reference_high_corr_threshold,
        reference_mean_abs_corr_threshold=reference_mean_abs_corr_threshold,
        alpha=alpha,
    )
    write_financial_pit_post_announcement_gap_reversal_residual_prescreen(output_dir, result)
    if not allow_not_ready and not result["summary"].get("passes", False):
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Financial PIT post-announcement gap reversal residual prescreen is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Round223 financial PIT post-announcement gap reversal residual IC and neutralization prescreen."
    )
    parser.add_argument("--financial-root", default=str(DEFAULT_FINANCIAL_ROOT))
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--preregistration-json", default=str(DEFAULT_PREREGISTRATION_JSON))
    parser.add_argument("--candidate-plan-gate-json")
    parser.add_argument("--stock-basic", default=str(DEFAULT_STOCK_BASIC))
    parser.add_argument("--daily-basic-root", action="append", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--horizon", action="append", type=int, default=[])
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=8)
    parser.add_argument("--min-neutral-rank-ic", type=float, default=0.01)
    parser.add_argument("--min-neutral-ic-t-stat", type=float, default=2.0)
    parser.add_argument("--min-neutral-retention", type=float, default=0.35)
    parser.add_argument("--reference-high-corr-threshold", type=float, default=0.90)
    parser.add_argument("--reference-mean-abs-corr-threshold", type=float, default=0.70)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    result = run_financial_pit_post_announcement_gap_reversal_residual_prescreen_cli(
        financial_root=Path(args.financial_root),
        bars_roots=[Path(root) for root in (args.bars_root or DEFAULT_BARS_ROOTS)],
        preregistration_json=Path(args.preregistration_json),
        candidate_plan_gate_json=Path(args.candidate_plan_gate_json) if args.candidate_plan_gate_json else None,
        stock_basic_path=Path(args.stock_basic) if args.stock_basic else None,
        daily_basic_roots=[Path(root) for root in (args.daily_basic_root or DEFAULT_DAILY_BASIC_ROOTS)],
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        horizons=args.horizon or [5],
        execution_lag=args.execution_lag,
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        min_neutral_rank_ic=args.min_neutral_rank_ic,
        min_neutral_ic_t_stat=args.min_neutral_ic_t_stat,
        min_neutral_retention=args.min_neutral_retention,
        reference_high_corr_threshold=args.reference_high_corr_threshold,
        reference_mean_abs_corr_threshold=args.reference_mean_abs_corr_threshold,
        alpha=args.alpha,
        allow_not_ready=args.allow_not_ready,
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
