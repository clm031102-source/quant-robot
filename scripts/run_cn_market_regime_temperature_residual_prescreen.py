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

from quant_robot.ops.cn_market_regime_temperature_residual_prescreen import (  # noqa: E402
    build_cn_market_regime_temperature_residual_prescreen,
    write_cn_market_regime_temperature_residual_prescreen,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/cn_market_regime_temperature_residual_prescreen_round162_20260623")
DEFAULT_BARS_ROOTS = [
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
]
DEFAULT_FACTOR_INPUTS_ROOT = Path("data/processed/office_desktop_20260617_daily_basic_factor_inputs")
DEFAULT_STOCK_BASIC = Path("data/processed/cn_stock_metadata")
DEFAULT_PREREGISTRATION = Path("data/reports/cn_market_regime_temperature_preregistration_round161_20260623/cn_market_regime_temperature_preregistration.json")


def run_cn_market_regime_temperature_residual_prescreen_cli(
    *,
    bars_roots: list[str | Path] | None = None,
    factor_inputs_root: str | Path | None = DEFAULT_FACTOR_INPUTS_ROOT,
    stock_basic: str | Path | None = DEFAULT_STOCK_BASIC,
    preregistration_json: str | Path | None = DEFAULT_PREREGISTRATION,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    horizon: int = 5,
    execution_lag: int = 1,
    sample_every_n_dates: int = 5,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
) -> dict[str, Any]:
    roots = bars_roots if bars_roots is not None else DEFAULT_BARS_ROOTS
    result = build_cn_market_regime_temperature_residual_prescreen(
        bars_roots=roots,
        factor_inputs_root=factor_inputs_root,
        stock_basic=stock_basic,
        preregistration_json=preregistration_json,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        horizons=(int(horizon),),
        execution_lag=execution_lag,
        sample_every_n_dates=sample_every_n_dates,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_signal_date_amount=min_signal_date_amount,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
    )
    write_cn_market_regime_temperature_residual_prescreen(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Round162 CN market regime-temperature residual prescreen.")
    parser.add_argument("--bars-root", action="append", dest="bars_roots")
    parser.add_argument("--factor-inputs-root", default=str(DEFAULT_FACTOR_INPUTS_ROOT))
    parser.add_argument("--stock-basic", default=str(DEFAULT_STOCK_BASIC))
    parser.add_argument("--preregistration-json", default=str(DEFAULT_PREREGISTRATION))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default="2015-01-01")
    parser.add_argument("--analysis-end-date", default="2025-12-31")
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--sample-every-n-dates", type=int, default=5)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=20)
    parser.add_argument("--min-signal-date-amount", type=float, default=10_000_000)
    parser.add_argument("--min-industries", type=int, default=2)
    parser.add_argument("--min-assets-per-industry", type=int, default=2)
    args = parser.parse_args()
    result = run_cn_market_regime_temperature_residual_prescreen_cli(
        bars_roots=[Path(root) for root in args.bars_roots] if args.bars_roots else None,
        factor_inputs_root=Path(args.factor_inputs_root) if args.factor_inputs_root else None,
        stock_basic=Path(args.stock_basic) if args.stock_basic else None,
        preregistration_json=Path(args.preregistration_json) if args.preregistration_json else None,
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        horizon=args.horizon,
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
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
