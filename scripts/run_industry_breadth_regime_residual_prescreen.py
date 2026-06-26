from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.factors.industry_breadth_regime import INDUSTRY_BREADTH_REGIME_FACTOR_NAMES  # noqa: E402
from quant_robot.ops.capacity_safe_price_volume_prescreen import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.industry_breadth_regime_residual_prescreen import (  # noqa: E402
    build_industry_breadth_regime_residual_prescreen,
    build_industry_breadth_regime_sharded_residual_prescreen,
    summarize_industry_breadth_regime_residual_prescreen,
    write_industry_breadth_regime_residual_prescreen,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_STOCK_BASIC = Path("data/processed/round198_tradeability_long_cycle_official_backfill_20260623/metadata/tushare_stock_basic")
DEFAULT_OUTPUT_DIR = Path("data/reports/industry_breadth_regime_residual_prescreen_round261_20260626")


def run_industry_breadth_regime_residual_prescreen_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    stock_basic: str | Path | pd.DataFrame | None = DEFAULT_STOCK_BASIC,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    sharded: bool = False,
    lookback_calendar_days: int = 140,
    forward_calendar_days: int | None = None,
    candidate_factor_names: Sequence[str] = INDUSTRY_BREADTH_REGIME_FACTOR_NAMES,
    horizons: Sequence[int] = (5, 20),
    execution_lag: int = 1,
    sample_every_n_dates: int = 5,
    include_reference_factors: bool = True,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
    min_industry_neutral_mean_ic: float = 0.02,
    min_industry_neutral_icir: float = 0.20,
    min_industry_neutral_positive_ic_rate: float = 0.55,
    min_residual_mean_ic: float = 0.02,
    min_residual_icir: float = 0.20,
    min_residual_positive_ic_rate: float = 0.55,
    factor_frame: pd.DataFrame | None = None,
    labels: pd.DataFrame | None = None,
    reference_factor_frame: pd.DataFrame | None = None,
    exposure_frame: pd.DataFrame | None = None,
) -> dict[str, Any]:
    if factor_frame is not None and labels is not None:
        result = summarize_industry_breadth_regime_residual_prescreen(
            factor_frame,
            labels,
            reference_factor_frame=reference_factor_frame,
            exposure_frame=exposure_frame,
            candidate_factor_names=candidate_factor_names,
            horizons=tuple(int(horizon) for horizon in horizons),
            sample_every_n_dates=sample_every_n_dates,
            min_cross_section=min_cross_section,
            min_ic_observations=min_ic_observations,
            min_industries=min_industries,
            min_assets_per_industry=min_assets_per_industry,
            min_industry_neutral_mean_ic=min_industry_neutral_mean_ic,
            min_industry_neutral_icir=min_industry_neutral_icir,
            min_industry_neutral_positive_ic_rate=min_industry_neutral_positive_ic_rate,
            min_residual_mean_ic=min_residual_mean_ic,
            min_residual_icir=min_residual_icir,
            min_residual_positive_ic_rate=min_residual_positive_ic_rate,
        )
    elif sharded:
        result = build_industry_breadth_regime_sharded_residual_prescreen(
            bars_roots=tuple(Path(path) for path in bars_roots),
            stock_basic=Path(stock_basic) if isinstance(stock_basic, (str, Path)) else stock_basic,
            candidate_factor_names=candidate_factor_names,
            analysis_start_date=analysis_start_date,
            analysis_end_date=analysis_end_date,
            include_final_holdout=include_final_holdout,
            horizons=tuple(int(horizon) for horizon in horizons),
            execution_lag=execution_lag,
            lookback_calendar_days=lookback_calendar_days,
            forward_calendar_days=forward_calendar_days,
            sample_every_n_dates=sample_every_n_dates,
            include_reference_factors=include_reference_factors,
            min_cross_section=min_cross_section,
            min_ic_observations=min_ic_observations,
            min_signal_date_amount=min_signal_date_amount,
            min_industries=min_industries,
            min_assets_per_industry=min_assets_per_industry,
            min_industry_neutral_mean_ic=min_industry_neutral_mean_ic,
            min_industry_neutral_icir=min_industry_neutral_icir,
            min_industry_neutral_positive_ic_rate=min_industry_neutral_positive_ic_rate,
            min_residual_mean_ic=min_residual_mean_ic,
            min_residual_icir=min_residual_icir,
            min_residual_positive_ic_rate=min_residual_positive_ic_rate,
        )
    else:
        result = build_industry_breadth_regime_residual_prescreen(
            bars_roots=tuple(Path(path) for path in bars_roots),
            stock_basic=Path(stock_basic) if isinstance(stock_basic, (str, Path)) else stock_basic,
            candidate_factor_names=candidate_factor_names,
            analysis_start_date=analysis_start_date,
            analysis_end_date=analysis_end_date,
            include_final_holdout=include_final_holdout,
            horizons=tuple(int(horizon) for horizon in horizons),
            execution_lag=execution_lag,
            sample_every_n_dates=sample_every_n_dates,
            include_reference_factors=include_reference_factors,
            min_cross_section=min_cross_section,
            min_ic_observations=min_ic_observations,
            min_signal_date_amount=min_signal_date_amount,
            min_industries=min_industries,
            min_assets_per_industry=min_assets_per_industry,
            min_industry_neutral_mean_ic=min_industry_neutral_mean_ic,
            min_industry_neutral_icir=min_industry_neutral_icir,
            min_industry_neutral_positive_ic_rate=min_industry_neutral_positive_ic_rate,
            min_residual_mean_ic=min_residual_mean_ic,
            min_residual_icir=min_residual_icir,
            min_residual_positive_ic_rate=min_residual_positive_ic_rate,
        )
    write_industry_breadth_regime_residual_prescreen(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Round261 industry breadth-regime residual IC and reference de-duplication prescreen."
    )
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--stock-basic", default=str(DEFAULT_STOCK_BASIC))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--sharded", action="store_true")
    parser.add_argument("--lookback-calendar-days", type=int, default=140)
    parser.add_argument("--forward-calendar-days", type=int)
    parser.add_argument("--candidate-factor-name", action="append", dest="candidate_factor_names")
    parser.add_argument("--horizon", type=int, action="append", dest="horizons")
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--sample-every-n-dates", type=int, default=5)
    parser.add_argument("--skip-reference-factors", action="store_true")
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=20)
    parser.add_argument("--min-signal-date-amount", type=float, default=10_000_000)
    parser.add_argument("--min-industries", type=int, default=2)
    parser.add_argument("--min-assets-per-industry", type=int, default=2)
    parser.add_argument("--min-industry-neutral-mean-ic", type=float, default=0.02)
    parser.add_argument("--min-industry-neutral-icir", type=float, default=0.20)
    parser.add_argument("--min-industry-neutral-positive-ic-rate", type=float, default=0.55)
    parser.add_argument("--min-residual-mean-ic", type=float, default=0.02)
    parser.add_argument("--min-residual-icir", type=float, default=0.20)
    parser.add_argument("--min-residual-positive-ic-rate", type=float, default=0.55)
    args = parser.parse_args()
    result = run_industry_breadth_regime_residual_prescreen_cli(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        stock_basic=Path(args.stock_basic) if args.stock_basic else None,
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        sharded=args.sharded,
        lookback_calendar_days=args.lookback_calendar_days,
        forward_calendar_days=args.forward_calendar_days,
        candidate_factor_names=tuple(args.candidate_factor_names or INDUSTRY_BREADTH_REGIME_FACTOR_NAMES),
        horizons=tuple(args.horizons or (5, 20)),
        execution_lag=args.execution_lag,
        sample_every_n_dates=args.sample_every_n_dates,
        include_reference_factors=not args.skip_reference_factors,
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        min_signal_date_amount=args.min_signal_date_amount,
        min_industries=args.min_industries,
        min_assets_per_industry=args.min_assets_per_industry,
        min_industry_neutral_mean_ic=args.min_industry_neutral_mean_ic,
        min_industry_neutral_icir=args.min_industry_neutral_icir,
        min_industry_neutral_positive_ic_rate=args.min_industry_neutral_positive_ic_rate,
        min_residual_mean_ic=args.min_residual_mean_ic,
        min_residual_icir=args.min_residual_icir,
        min_residual_positive_ic_rate=args.min_residual_positive_ic_rate,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "promotion_policy": result.get("promotion_policy", {}),
                "data_window": result.get("data_window", {}),
                "next_direction": result["summary"].get("next_direction"),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

