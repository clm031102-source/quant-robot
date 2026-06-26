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

from quant_robot.ops.capacity_safe_price_volume_prescreen import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.public_technical_failure_reversal_neutral_dedup import (  # noqa: E402
    DEFAULT_HORIZON,
    DEFAULT_LEAD_FACTOR_NAME,
    build_public_technical_failure_reversal_neutral_dedup,
    summarize_public_technical_failure_reversal_neutral_dedup,
    write_public_technical_failure_reversal_neutral_dedup,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_STOCK_BASIC = Path("data/processed/cn_stock_metadata")
DEFAULT_PRESCREEN_REPORT = Path(
    "data/reports/public_technical_failure_reversal_prescreen_round155_20260623/public_technical_failure_reversal_prescreen.json"
)
DEFAULT_OUTPUT_DIR = Path("data/reports/public_technical_failure_reversal_neutral_dedup_round156_20260623")


def run_public_technical_failure_reversal_neutral_dedup_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    stock_basic_path: str | Path | None = DEFAULT_STOCK_BASIC,
    prescreen_report: str | Path = DEFAULT_PRESCREEN_REPORT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    horizon: int = DEFAULT_HORIZON,
    execution_lag: int = 1,
    sample_every_n_dates: int = 5,
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
    lead_factor_frame: pd.DataFrame | None = None,
    labels: pd.DataFrame | None = None,
    reference_factor_frame: pd.DataFrame | None = None,
    exposure_frame: pd.DataFrame | None = None,
    prescreen_report_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if lead_factor_frame is not None and labels is not None:
        result = summarize_public_technical_failure_reversal_neutral_dedup(
            lead_factor_frame,
            labels,
            reference_factor_frame=reference_factor_frame,
            exposure_frame=exposure_frame,
            prescreen_report=prescreen_report_payload or _load_report(Path(prescreen_report)),
            lead_factor_name=lead_factor_name,
            horizon=horizon,
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
    else:
        result = build_public_technical_failure_reversal_neutral_dedup(
            bars_roots=tuple(Path(path) for path in bars_roots),
            stock_basic_path=Path(stock_basic_path) if stock_basic_path is not None else None,
            prescreen_report=prescreen_report_payload or Path(prescreen_report),
            analysis_start_date=analysis_start_date,
            analysis_end_date=analysis_end_date,
            include_final_holdout=include_final_holdout,
            lead_factor_name=lead_factor_name,
            horizon=horizon,
            execution_lag=execution_lag,
            sample_every_n_dates=sample_every_n_dates,
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
    write_public_technical_failure_reversal_neutral_dedup(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Round156 public technical failure-reversal neutralization and reference de-duplication audit."
    )
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--stock-basic", default=str(DEFAULT_STOCK_BASIC))
    parser.add_argument("--prescreen-report", default=str(DEFAULT_PRESCREEN_REPORT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--lead-factor-name", default=DEFAULT_LEAD_FACTOR_NAME)
    parser.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--sample-every-n-dates", type=int, default=5)
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
    result = run_public_technical_failure_reversal_neutral_dedup_cli(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        stock_basic_path=Path(args.stock_basic) if args.stock_basic else None,
        prescreen_report=Path(args.prescreen_report),
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        lead_factor_name=args.lead_factor_name,
        horizon=args.horizon,
        execution_lag=args.execution_lag,
        sample_every_n_dates=args.sample_every_n_dates,
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
                "raw_ic_summary": result.get("raw_ic_summary", {}),
                "industry_neutral_ic_summary": result.get("industry_neutral_ic_summary", {}),
                "residual_ic_summary": result.get("residual_ic_summary", {}),
                "gate": result.get("gate", {}),
                "next_direction": result.get("next_direction"),
                "data_window": result.get("data_window", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
