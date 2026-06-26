from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.event_factor_pit_ic_prescreen import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    build_event_factor_pit_ic_prescreen,
    write_event_factor_pit_ic_prescreen,
)
from quant_robot.ops.event_factor_preregistration import EventFactorCandidateSpec  # noqa: E402
from scripts.run_event_factor_pit_ic_prescreen import (  # noqa: E402
    DEFAULT_BARS_ROOTS,
    DEFAULT_STOCK_BASIC,
    load_cached_forecast_express_event_frames,
    _load_frame,
    _split_csv,
)


DEFAULT_EVENT_CACHE_ROOT = Path("data/processed/round255_forecast_express_event_cache_20260625")
DEFAULT_OUTPUT_DIR = Path("data/reports/round256_forecast_guidance_uncertainty_pit_ic_prescreen_20260626")
REPORT_TITLE = "Round256 Forecast Guidance Uncertainty PIT/IC Prescreen"
NEXT_DIRECTION_WITH_LEADS = "round257_forecast_guidance_uncertainty_dedup_coverage_walk_forward_preflight"
NEXT_DIRECTION_WITHOUT_LEADS = "round257_rotate_after_forecast_guidance_uncertainty_zero_research_leads"


def forecast_guidance_uncertainty_candidate_specs() -> tuple[EventFactorCandidateSpec, ...]:
    base = {
        "family": "forecast_guidance_uncertainty",
        "direction": "higher_is_better",
        "required_endpoints": ("forecast",),
        "required_fields": ("ann_date", "end_date", "p_change_min", "p_change_max", "net_profit_min", "net_profit_max"),
        "event_date_fields": ("ann_date",),
        "windows": (1,),
        "public_reference_tags": ("earnings_guidance", "forecast_uncertainty", "post_earnings_announcement_drift"),
        "expected_failure_modes": ("forecast_range_sparse_coverage", "management_guidance_bias", "industry_cycle_beta"),
    }
    return (
        EventFactorCandidateSpec(
            factor_name="event_forecast_guidance_confidence_1q",
            formula_template="positive guidance midpoint divided by guidance range width",
            economic_rationale=(
                "Positive narrow guidance tests management confidence and forecast precision instead of raw "
                "forecast direction or sign flips."
            ),
            **base,
        ),
        EventFactorCandidateSpec(
            factor_name="event_forecast_uncertainty_compression_1q",
            formula_template="negative guidance range width normalized by midpoint magnitude",
            economic_rationale=(
                "Narrow forecast ranges can proxy lower information uncertainty after an earnings forecast event."
            ),
            **base,
        ),
        EventFactorCandidateSpec(
            factor_name="event_forecast_positive_floor_skew_1q",
            formula_template="lower-bound positive forecast skew normalized by upper-bound magnitude",
            economic_rationale=(
                "A positive lower guidance bound tests asymmetric management confidence, not the old forecast "
                "revision level."
            ),
            **base,
        ),
    )


def run_forecast_guidance_uncertainty_pit_ic_prescreen_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    stock_basic_path: str | Path = DEFAULT_STOCK_BASIC,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    event_frames: dict[str, pd.DataFrame] | None = None,
    event_cache_root: str | Path = DEFAULT_EVENT_CACHE_ROOT,
    event_start_year: int = 2015,
    event_end_year: int = 2025,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = (5, 20),
    execution_lag: int = 1,
    pit_lag_trade_days: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 8,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
) -> dict[str, Any]:
    stock_basic = _load_frame(Path(stock_basic_path))
    frames = event_frames
    if frames is None:
        frames = load_cached_forecast_express_event_frames(
            event_cache_root,
            start_year=event_start_year,
            end_year=event_end_year,
            endpoints=("forecast",),
        )
    result = build_event_factor_pit_ic_prescreen(
        bars_roots=tuple(Path(path) for path in bars_roots),
        stock_basic=stock_basic,
        event_frames=frames,
        candidate_specs=forecast_guidance_uncertainty_candidate_specs(),
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        horizons=horizons,
        execution_lag=execution_lag,
        pit_lag_trade_days=pit_lag_trade_days,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
        report_title=REPORT_TITLE,
        next_direction_with_leads=NEXT_DIRECTION_WITH_LEADS,
        next_direction_without_leads=NEXT_DIRECTION_WITHOUT_LEADS,
    )
    write_event_factor_pit_ic_prescreen(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Round256 forecast-guidance uncertainty PIT/IC prescreen for CN stock factors."
    )
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--stock-basic", default=str(DEFAULT_STOCK_BASIC))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--event-cache-root", default=str(DEFAULT_EVENT_CACHE_ROOT))
    parser.add_argument("--event-start-year", type=int, default=2015)
    parser.add_argument("--event-end-year", type=int, default=2025)
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--horizons", default="5,20")
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--pit-lag-trade-days", type=int, default=1)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=8)
    parser.add_argument("--min-industries", type=int, default=2)
    parser.add_argument("--min-assets-per-industry", type=int, default=2)
    args = parser.parse_args()
    result = run_forecast_guidance_uncertainty_pit_ic_prescreen_cli(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        stock_basic_path=Path(args.stock_basic),
        output_dir=Path(args.output_dir),
        event_cache_root=Path(args.event_cache_root),
        event_start_year=args.event_start_year,
        event_end_year=args.event_end_year,
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        horizons=tuple(int(item) for item in _split_csv(args.horizons)),
        execution_lag=args.execution_lag,
        pit_lag_trade_days=args.pit_lag_trade_days,
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        min_industries=args.min_industries,
        min_assets_per_industry=args.min_assets_per_industry,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "data_window": result.get("data_window", {}),
                "holdout_policy": result.get("holdout_policy", {}),
                "pit_policy": result.get("pit_policy", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
