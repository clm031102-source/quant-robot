from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.industry_style_exposure_audit import (
    DEFAULT_REQUIRED_STYLE_NAMES,
    build_industry_style_exposure_audit,
    write_industry_style_exposure_audit,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/industry_style_exposure_audit")


def run_industry_style_exposure_audit_cli(
    *,
    factors_path: str | Path,
    labels_path: str | Path,
    stock_basic_path: str | Path,
    style_factors_path: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    source_report: str | None = None,
    required_style_names: Sequence[str] = DEFAULT_REQUIRED_STYLE_NAMES,
    min_dates: int = 20,
    min_cross_section: int = 30,
    min_industries: int = 2,
    min_style_coverage_ratio: float = 0.90,
    max_missing_industry_fraction: float = 0.02,
    high_style_corr_threshold: float = 0.70,
    high_industry_r2_threshold: float = 0.50,
    min_residual_mean_ic: float = 0.02,
    min_residual_ic_t_stat: float = 2.0,
    min_residual_positive_rate: float = 0.55,
    min_residual_retention: float = 0.35,
) -> dict[str, Any]:
    result = build_industry_style_exposure_audit(
        factors=_read_frame(factors_path),
        labels=_read_frame(labels_path),
        stock_basic=_read_frame(stock_basic_path),
        style_factors=_read_frame(style_factors_path),
        source_report=source_report,
        required_style_names=required_style_names,
        min_dates=min_dates,
        min_cross_section=min_cross_section,
        min_industries=min_industries,
        min_style_coverage_ratio=min_style_coverage_ratio,
        max_missing_industry_fraction=max_missing_industry_fraction,
        high_style_corr_threshold=high_style_corr_threshold,
        high_industry_r2_threshold=high_industry_r2_threshold,
        min_residual_mean_ic=min_residual_mean_ic,
        min_residual_ic_t_stat=min_residual_ic_t_stat,
        min_residual_positive_rate=min_residual_positive_rate,
        min_residual_retention=min_residual_retention,
    )
    write_industry_style_exposure_audit(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the reusable CN stock industry/style exposure audit.")
    parser.add_argument("--factors", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--stock-basic", required=True)
    parser.add_argument("--style-factors", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--source-report")
    parser.add_argument("--required-style-names", default=",".join(DEFAULT_REQUIRED_STYLE_NAMES))
    parser.add_argument("--min-dates", type=int, default=20)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-industries", type=int, default=2)
    parser.add_argument("--min-style-coverage-ratio", type=float, default=0.90)
    parser.add_argument("--max-missing-industry-fraction", type=float, default=0.02)
    parser.add_argument("--high-style-corr-threshold", type=float, default=0.70)
    parser.add_argument("--high-industry-r2-threshold", type=float, default=0.50)
    parser.add_argument("--min-residual-mean-ic", type=float, default=0.02)
    parser.add_argument("--min-residual-ic-t-stat", type=float, default=2.0)
    parser.add_argument("--min-residual-positive-rate", type=float, default=0.55)
    parser.add_argument("--min-residual-retention", type=float, default=0.35)
    args = parser.parse_args()
    result = run_industry_style_exposure_audit_cli(
        factors_path=args.factors,
        labels_path=args.labels,
        stock_basic_path=args.stock_basic,
        style_factors_path=args.style_factors,
        output_dir=args.output_dir,
        source_report=args.source_report,
        required_style_names=_parse_list(args.required_style_names),
        min_dates=args.min_dates,
        min_cross_section=args.min_cross_section,
        min_industries=args.min_industries,
        min_style_coverage_ratio=args.min_style_coverage_ratio,
        max_missing_industry_fraction=args.max_missing_industry_fraction,
        high_style_corr_threshold=args.high_style_corr_threshold,
        high_industry_r2_threshold=args.high_industry_r2_threshold,
        min_residual_mean_ic=args.min_residual_mean_ic,
        min_residual_ic_t_stat=args.min_residual_ic_t_stat,
        min_residual_positive_rate=args.min_residual_positive_rate,
        min_residual_retention=args.min_residual_retention,
    )
    print(json.dumps(_sanitize(result), indent=2, sort_keys=True))


def _read_frame(path: str | Path) -> pd.DataFrame:
    input_path = Path(path)
    if input_path.suffix.lower() == ".parquet":
        return pd.read_parquet(input_path)
    return pd.read_csv(input_path)


def _parse_list(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


if __name__ == "__main__":
    main()
