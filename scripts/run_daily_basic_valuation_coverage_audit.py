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

from quant_robot.ops.daily_basic_valuation_coverage_audit import (  # noqa: E402
    DEFAULT_MIN_DATE_PASS_RATIO,
    DEFAULT_MIN_FIELD_NON_NULL_RATIO,
    DEFAULT_MIN_FULL_COVERAGE_RATIO,
    build_daily_basic_valuation_coverage_audit,
    write_daily_basic_valuation_coverage_audit,
)


DEFAULT_DAILY_BASIC_ROOTS = (Path("data/processed/office_desktop_20260617_daily_basic_factor_inputs"),)
DEFAULT_OUTPUT_DIR = Path("data/reports/round210_daily_basic_valuation_coverage_audit_20260624")


def run_daily_basic_valuation_coverage_audit_cli(
    *,
    daily_basic_roots: Iterable[str | Path] = DEFAULT_DAILY_BASIC_ROOTS,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    market: str = "CN",
    analysis_start_date: str | None = None,
    analysis_end_date: str | None = None,
    min_full_coverage_ratio: float = DEFAULT_MIN_FULL_COVERAGE_RATIO,
    min_field_non_null_ratio: float = DEFAULT_MIN_FIELD_NON_NULL_RATIO,
    min_date_pass_ratio: float = DEFAULT_MIN_DATE_PASS_RATIO,
) -> dict[str, Any]:
    result = build_daily_basic_valuation_coverage_audit(
        daily_basic_roots=tuple(Path(path) for path in daily_basic_roots),
        market=market,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        min_full_coverage_ratio=min_full_coverage_ratio,
        min_field_non_null_ratio=min_field_non_null_ratio,
        min_date_pass_ratio=min_date_pass_ratio,
    )
    write_daily_basic_valuation_coverage_audit(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Round210 daily-basic valuation field coverage audit.")
    parser.add_argument("--daily-basic-root", action="append", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--market", default="CN")
    parser.add_argument("--analysis-start-date", default=None)
    parser.add_argument("--analysis-end-date", default=None)
    parser.add_argument("--min-full-coverage-ratio", type=float, default=DEFAULT_MIN_FULL_COVERAGE_RATIO)
    parser.add_argument("--min-field-non-null-ratio", type=float, default=DEFAULT_MIN_FIELD_NON_NULL_RATIO)
    parser.add_argument("--min-date-pass-ratio", type=float, default=DEFAULT_MIN_DATE_PASS_RATIO)
    args = parser.parse_args()

    result = run_daily_basic_valuation_coverage_audit_cli(
        daily_basic_roots=tuple(Path(path) for path in (args.daily_basic_root or DEFAULT_DAILY_BASIC_ROOTS)),
        output_dir=Path(args.output_dir),
        market=args.market,
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        min_full_coverage_ratio=args.min_full_coverage_ratio,
        min_field_non_null_ratio=args.min_field_non_null_ratio,
        min_date_pass_ratio=args.min_date_pass_ratio,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "gate": result["gate"],
                "promotion_policy": result["promotion_policy"],
                "next_direction": result["next_direction"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
