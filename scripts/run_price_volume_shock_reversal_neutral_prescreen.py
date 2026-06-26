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
from quant_robot.ops.price_volume_shock_reversal_neutral_prescreen import (  # noqa: E402
    build_price_volume_shock_reversal_neutral_prescreen,
    write_price_volume_shock_reversal_neutral_prescreen,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_STOCK_BASIC = Path("data/processed/cn_stock_metadata")
DEFAULT_PREREGISTRATION_JSON = Path(
    "data/reports/price_volume_shock_reversal_preregistration_round157_20260623/price_volume_shock_reversal_preregistration.json"
)
DEFAULT_OUTPUT_DIR = Path("data/reports/price_volume_shock_reversal_neutral_prescreen_round158_20260623")


def run_price_volume_shock_reversal_neutral_prescreen_cli(
    *,
    bars_roots: list[str | Path] | tuple[str | Path, ...] = DEFAULT_BARS_ROOTS,
    stock_basic: str | Path | None = DEFAULT_STOCK_BASIC,
    preregistration_json: str | Path | None = DEFAULT_PREREGISTRATION_JSON,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: list[int] | tuple[int, ...] = (5,),
    execution_lag: int = 1,
    sample_every_n_dates: int = 5,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
) -> dict[str, Any]:
    result = build_price_volume_shock_reversal_neutral_prescreen(
        bars_roots=[Path(root) for root in bars_roots],
        stock_basic=Path(stock_basic) if stock_basic else None,
        preregistration_json=Path(preregistration_json) if preregistration_json else None,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        horizons=tuple(horizons),
        execution_lag=execution_lag,
        sample_every_n_dates=sample_every_n_dates,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_signal_date_amount=min_signal_date_amount,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
    )
    write_price_volume_shock_reversal_neutral_prescreen(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Round158 price-volume shock reversal neutral prescreen.")
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--stock-basic", default=str(DEFAULT_STOCK_BASIC))
    parser.add_argument("--preregistration-json", default=str(DEFAULT_PREREGISTRATION_JSON))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--horizon", type=int, action="append", dest="horizons")
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--sample-every-n-dates", type=int, default=5)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=20)
    parser.add_argument("--min-signal-date-amount", type=float, default=10_000_000)
    parser.add_argument("--min-industries", type=int, default=2)
    parser.add_argument("--min-assets-per-industry", type=int, default=2)
    args = parser.parse_args()
    result = run_price_volume_shock_reversal_neutral_prescreen_cli(
        bars_roots=[Path(root) for root in (args.bars_root or DEFAULT_BARS_ROOTS)],
        stock_basic=Path(args.stock_basic) if args.stock_basic else None,
        preregistration_json=Path(args.preregistration_json) if args.preregistration_json else None,
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        horizons=tuple(args.horizons or (5,)),
        execution_lag=args.execution_lag,
        sample_every_n_dates=args.sample_every_n_dates,
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        min_signal_date_amount=args.min_signal_date_amount,
        min_industries=args.min_industries,
        min_assets_per_industry=args.min_assets_per_industry,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "data_window": result.get("data_window", {}),
                "promotion_policy": result.get("promotion_policy", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
