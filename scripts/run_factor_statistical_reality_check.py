from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.factor_statistical_reality_check import (
    build_factor_statistical_reality_check,
    write_factor_statistical_reality_check,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/factor_statistical_reality_check")


def run_factor_statistical_reality_check(
    *,
    experiments_path: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    metric_column: str | None = None,
    observations_column: str | None = None,
    p_value_column: str | None = None,
    case_column: str = "case_id",
    date_column: str | None = None,
    x_param: str | None = None,
    y_param: str | None = None,
    sensitivity_metric: str | None = None,
    alpha: float = 0.05,
    min_deflated_sharpe_probability: float = 0.95,
    cpcv_groups: int = 6,
    cpcv_test_group_count: int = 2,
    purge_observations: int = 0,
    embargo_observations: int = 0,
) -> dict[str, Any]:
    experiments = _load_table(experiments_path)
    report = build_factor_statistical_reality_check(
        experiments,
        metric_column=metric_column,
        observations_column=observations_column,
        p_value_column=p_value_column,
        case_column=case_column,
        date_column=date_column,
        x_param=x_param,
        y_param=y_param,
        sensitivity_metric=sensitivity_metric,
        alpha=alpha,
        min_deflated_sharpe_probability=min_deflated_sharpe_probability,
        cpcv_groups=cpcv_groups,
        cpcv_test_group_count=cpcv_test_group_count,
        purge_observations=purge_observations,
        embargo_observations=embargo_observations,
    )
    write_factor_statistical_reality_check(output_dir, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a strict statistical reality check for factor experiments.")
    parser.add_argument("--experiments-path", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--metric-column")
    parser.add_argument("--observations-column")
    parser.add_argument("--p-value-column")
    parser.add_argument("--case-column", default="case_id")
    parser.add_argument("--date-column")
    parser.add_argument("--x-param")
    parser.add_argument("--y-param")
    parser.add_argument("--sensitivity-metric")
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--min-deflated-sharpe-probability", type=float, default=0.95)
    parser.add_argument("--cpcv-groups", type=int, default=6)
    parser.add_argument("--cpcv-test-group-count", type=int, default=2)
    parser.add_argument("--purge-observations", type=int, default=0)
    parser.add_argument("--embargo-observations", type=int, default=0)
    args = parser.parse_args()
    report = run_factor_statistical_reality_check(
        experiments_path=args.experiments_path,
        output_dir=args.output_dir,
        metric_column=args.metric_column,
        observations_column=args.observations_column,
        p_value_column=args.p_value_column,
        case_column=args.case_column,
        date_column=args.date_column,
        x_param=args.x_param,
        y_param=args.y_param,
        sensitivity_metric=args.sensitivity_metric,
        alpha=args.alpha,
        min_deflated_sharpe_probability=args.min_deflated_sharpe_probability,
        cpcv_groups=args.cpcv_groups,
        cpcv_test_group_count=args.cpcv_test_group_count,
        purge_observations=args.purge_observations,
        embargo_observations=args.embargo_observations,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


def _load_table(path: str | Path) -> pd.DataFrame:
    table_path = Path(path)
    suffix = table_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(table_path)
    if suffix in {".json", ".jsonl"}:
        return pd.read_json(table_path, lines=suffix == ".jsonl")
    if suffix == ".parquet":
        return pd.read_parquet(table_path)
    raise ValueError(f"Unsupported experiments table format: {table_path}")


if __name__ == "__main__":
    main()
