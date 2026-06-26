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

from quant_robot.ops.daily_basic_free_float_supply_quality_residual_stability_audit import (  # noqa: E402
    build_daily_basic_free_float_supply_quality_residual_stability_audit,
    write_daily_basic_free_float_supply_quality_residual_stability_audit,
)
from quant_robot.ops.daily_basic_non_price_public_carry_lead_dedup import (  # noqa: E402
    DEFAULT_HORIZON,
    DEFAULT_LEAD_FACTOR_NAME,
)
from quant_robot.ops.daily_basic_non_price_public_carry_prescreen import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_DAILY_BASIC_ROOTS = (
    Path("data/processed/office_desktop_20260617_daily_basic_factor_inputs"),
)
DEFAULT_PRESCREEN_REPORT = Path(
    "data/reports/daily_basic_non_price_public_carry_prescreen_round132_20260622/"
    "daily_basic_non_price_public_carry_prescreen.json"
)
DEFAULT_OUTPUT_DIR = Path("data/reports/daily_basic_free_float_supply_quality_residual_stability_audit")


def run_daily_basic_free_float_supply_quality_residual_stability_audit_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    daily_basic_roots: Iterable[str | Path] = DEFAULT_DAILY_BASIC_ROOTS,
    prescreen_report: str | Path = DEFAULT_PRESCREEN_REPORT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    lead_factor_name: str = DEFAULT_LEAD_FACTOR_NAME,
    horizon: int = DEFAULT_HORIZON,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    min_field_coverage_ratio: float = 0.95,
    coverage_onset_observations: int = 63,
) -> dict[str, Any]:
    result = build_daily_basic_free_float_supply_quality_residual_stability_audit(
        bars_roots=bars_roots,
        daily_basic_roots=daily_basic_roots,
        prescreen_report=prescreen_report,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        lead_factor_name=lead_factor_name,
        horizon=horizon,
        execution_lag=execution_lag,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_signal_date_amount=min_signal_date_amount,
        min_field_coverage_ratio=min_field_coverage_ratio,
        coverage_onset_observations=coverage_onset_observations,
    )
    write_daily_basic_free_float_supply_quality_residual_stability_audit(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run Round134 daily-basic free-float supply quality residual stability audit for CN stocks."
        )
    )
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--daily-basic-root", action="append", default=None)
    parser.add_argument("--prescreen-report", default=str(DEFAULT_PRESCREEN_REPORT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--lead-factor-name", default=DEFAULT_LEAD_FACTOR_NAME)
    parser.add_argument("--horizon", type=int, default=DEFAULT_HORIZON)
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=20)
    parser.add_argument("--min-signal-date-amount", type=float, default=10_000_000)
    parser.add_argument("--min-field-coverage-ratio", type=float, default=0.95)
    parser.add_argument("--coverage-onset-observations", type=int, default=63)
    args = parser.parse_args()
    result = run_daily_basic_free_float_supply_quality_residual_stability_audit_cli(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        daily_basic_roots=tuple(Path(path) for path in (args.daily_basic_root or DEFAULT_DAILY_BASIC_ROOTS)),
        prescreen_report=Path(args.prescreen_report),
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        lead_factor_name=args.lead_factor_name,
        horizon=args.horizon,
        execution_lag=args.execution_lag,
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        min_signal_date_amount=args.min_signal_date_amount,
        min_field_coverage_ratio=args.min_field_coverage_ratio,
        coverage_onset_observations=args.coverage_onset_observations,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "residual_ic_summary": result.get("residual_ic_summary", {}),
                "strict_clean_residual_ic_summary": result.get("strict_clean_residual_ic_summary", {}),
                "gate": result.get("gate", {}),
                "next_direction": result.get("next_direction"),
                "recommended_post_review_direction": result.get("recommended_post_review_direction"),
                "data_window": result.get("data_window", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
