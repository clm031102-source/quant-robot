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

from quant_robot.ops.daily_basic_non_price_public_carry_prescreen import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
    build_daily_basic_non_price_public_carry_prescreen,
    write_daily_basic_non_price_public_carry_prescreen,
)
from quant_robot.ops.daily_basic_non_price_public_carry_preregistration import (  # noqa: E402
    DailyBasicNonPricePublicCarryCandidateSpec,
    default_daily_basic_non_price_public_carry_specs,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_DAILY_BASIC_ROOTS = (
    Path("data/processed/office_desktop_20260617_daily_basic_factor_inputs"),
)
DEFAULT_OUTPUT_DIR = Path("data/reports/daily_basic_non_price_public_carry_prescreen")


def run_daily_basic_non_price_public_carry_prescreen_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    daily_basic_roots: Iterable[str | Path] = DEFAULT_DAILY_BASIC_ROOTS,
    candidate_spec_json: str | Path | None = None,
    candidate_names: Iterable[str] | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_field_coverage_ratio: float = 0.80,
    min_field_coverage_clean_ratio: float = 0.80,
    min_capacity_clean_ratio: float = 0.80,
    min_signal_date_amount: float = 10_000_000,
) -> dict[str, Any]:
    candidate_specs = _resolve_candidate_specs(candidate_spec_json, candidate_names)
    result = build_daily_basic_non_price_public_carry_prescreen(
        bars_roots=bars_roots,
        daily_basic_roots=daily_basic_roots,
        candidate_specs=candidate_specs,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        horizons=horizons,
        execution_lag=execution_lag,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_field_coverage_ratio=min_field_coverage_ratio,
        min_field_coverage_clean_ratio=min_field_coverage_clean_ratio,
        min_capacity_clean_ratio=min_capacity_clean_ratio,
        min_signal_date_amount=min_signal_date_amount,
    )
    write_daily_basic_non_price_public_carry_prescreen(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run daily-basic non-price public carry coverage, IC, quantile, turnover, and capacity prescreen for CN stocks."
    )
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--daily-basic-root", action="append", default=None)
    parser.add_argument("--candidate-spec-json")
    parser.add_argument("--candidate-name", action="append", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--horizons", default=",".join(str(horizon) for horizon in DEFAULT_HORIZONS))
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=20)
    parser.add_argument("--min-field-coverage-ratio", type=float, default=0.80)
    parser.add_argument("--min-field-coverage-clean-ratio", type=float, default=0.80)
    parser.add_argument("--min-capacity-clean-ratio", type=float, default=0.80)
    parser.add_argument("--min-signal-date-amount", type=float, default=10_000_000)
    args = parser.parse_args()
    bars_roots = tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS))
    daily_basic_roots = tuple(Path(path) for path in (args.daily_basic_root or DEFAULT_DAILY_BASIC_ROOTS))
    horizons = tuple(int(item.strip()) for item in args.horizons.split(",") if item.strip())
    result = run_daily_basic_non_price_public_carry_prescreen_cli(
        bars_roots=bars_roots,
        daily_basic_roots=daily_basic_roots,
        candidate_spec_json=Path(args.candidate_spec_json) if args.candidate_spec_json else None,
        candidate_names=args.candidate_name,
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        horizons=horizons,
        execution_lag=args.execution_lag,
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        min_field_coverage_ratio=args.min_field_coverage_ratio,
        min_field_coverage_clean_ratio=args.min_field_coverage_clean_ratio,
        min_capacity_clean_ratio=args.min_capacity_clean_ratio,
        min_signal_date_amount=args.min_signal_date_amount,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "data_window": result.get("data_window", {}),
                "coverage_preflight": {
                    key: value
                    for key, value in result.get("coverage_preflight", {}).items()
                    if key != "field_coverage"
                },
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_candidate_specs(candidate_spec_json: str | Path | None) -> tuple[DailyBasicNonPricePublicCarryCandidateSpec, ...] | None:
    if not candidate_spec_json:
        return None
    data = json.loads(Path(candidate_spec_json).read_text(encoding="utf-8"))
    raw_specs = data.get("candidate_specs", data) if isinstance(data, dict) else data
    return tuple(_coerce_candidate_spec(row) for row in raw_specs)


def _resolve_candidate_specs(
    candidate_spec_json: str | Path | None,
    candidate_names: Iterable[str] | None,
) -> tuple[DailyBasicNonPricePublicCarryCandidateSpec, ...] | None:
    specs = _load_candidate_specs(candidate_spec_json)
    names = {str(item) for item in (candidate_names or [])}
    if not names:
        return specs
    base_specs = tuple(specs or default_daily_basic_non_price_public_carry_specs())
    available = {spec.factor_name for spec in base_specs}
    missing = sorted(names - available)
    if missing:
        raise ValueError(f"Unknown daily-basic candidate names: {', '.join(missing)}")
    return tuple(spec for spec in base_specs if spec.factor_name in names)


def _coerce_candidate_spec(row: dict[str, Any]) -> DailyBasicNonPricePublicCarryCandidateSpec:
    return DailyBasicNonPricePublicCarryCandidateSpec(
        factor_name=str(row["factor_name"]),
        family=str(row["family"]),
        formula_template=str(row["formula_template"]),
        direction=str(row.get("direction", "higher_is_better")),
        windows=tuple(int(item) for item in row.get("windows", ())),
        required_fields=tuple(str(item) for item in row.get("required_fields", ())),
        economic_rationale=str(row.get("economic_rationale", "")),
        public_reference_tags=tuple(str(item) for item in row.get("public_reference_tags", ())),
        expected_failure_modes=tuple(str(item) for item in row.get("expected_failure_modes", ())),
        source_evidence_status=str(
            row.get("source_evidence_status", "daily_basic_public_carry_preregistered_not_empirical_alpha")
        ),
        portfolio_backtest_allowed=bool(row.get("portfolio_backtest_allowed", False)),
        promotion_allowed=bool(row.get("promotion_allowed", False)),
    )


if __name__ == "__main__":
    main()
