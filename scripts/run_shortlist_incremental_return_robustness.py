from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.shortlist_incremental_return_robustness import (  # noqa: E402
    build_shortlist_incremental_return_robustness,
    write_shortlist_incremental_return_robustness,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/shortlist_incremental_return_robustness")


def parse_source_spec(value: str) -> dict[str, str]:
    path = value.strip()
    return_column = None
    if "|" in path:
        path, return_column = path.rsplit("|", 1)
        path = path.strip()
        return_column = return_column.strip() or None
    spec = {"path": str(Path(path))}
    if return_column:
        spec["return_column"] = return_column
    return spec


def parse_candidate_sources(values: list[str]) -> dict[str, dict[str, str]]:
    sources: dict[str, dict[str, str]] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--candidate-return-source must use candidate_name=path")
        name, path = value.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError("--candidate-return-source candidate_name cannot be empty")
        sources[name] = parse_source_spec(path)
    return sources


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit candidate return streams for incremental robustness against a base return stream."
    )
    parser.add_argument("--base-return-source", required=True)
    parser.add_argument(
        "--candidate-return-source",
        action="append",
        required=True,
        help="Candidate return CSV as candidate_name=path. Repeat for multiple candidates.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--base-return-column")
    parser.add_argument("--candidate-return-column")
    parser.add_argument("--date-column", default="date")
    parser.add_argument("--periods-per-year", type=float, default=252.0 / 5.0)
    parser.add_argument("--holding-period", type=int, default=20)
    parser.add_argument("--cpcv-groups", type=int, default=10)
    parser.add_argument("--cpcv-test-group-count", type=int, default=3)
    parser.add_argument("--purge-observations", type=int, default=0)
    parser.add_argument("--embargo-observations", type=int, default=0)
    parser.add_argument("--bootstrap-iterations", type=int, default=1000)
    parser.add_argument("--bootstrap-period", default="Q")
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--max-drawdown-floor", type=float, default=-0.30)
    parser.add_argument("--min-cpcv-annualized-win-rate", type=float, default=0.50)
    parser.add_argument("--min-bootstrap-annualized-win-rate", type=float, default=0.50)
    args = parser.parse_args()

    audit = build_shortlist_incremental_return_robustness(
        base_return_source=parse_source_spec(args.base_return_source),
        candidate_return_sources=parse_candidate_sources(args.candidate_return_source),
        base_return_column=args.base_return_column,
        candidate_return_column=args.candidate_return_column,
        date_column=args.date_column,
        periods_per_year=args.periods_per_year,
        holding_period=args.holding_period,
        cpcv_groups=args.cpcv_groups,
        cpcv_test_group_count=args.cpcv_test_group_count,
        purge_observations=args.purge_observations,
        embargo_observations=args.embargo_observations,
        bootstrap_iterations=args.bootstrap_iterations,
        bootstrap_period=args.bootstrap_period,
        random_seed=args.random_seed,
        max_drawdown_floor=args.max_drawdown_floor,
        min_cpcv_annualized_win_rate=args.min_cpcv_annualized_win_rate,
        min_bootstrap_annualized_win_rate=args.min_bootstrap_annualized_win_rate,
    )
    write_shortlist_incremental_return_robustness(Path(args.output_dir), audit)
    print(
        json.dumps(
            {
                "summary": audit["summary"],
                "top": audit["rows"][:10],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
