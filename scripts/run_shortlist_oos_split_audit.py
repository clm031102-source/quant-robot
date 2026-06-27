from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.shortlist_oos_split_audit import (  # noqa: E402
    build_shortlist_oos_split_audit,
    write_shortlist_oos_split_audit,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run rolling OOS split audit for event-return sources.")
    parser.add_argument(
        "--candidate",
        action="append",
        required=True,
        help="Candidate spec as name=path or name=path:return_column.",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--train-years", default="2,3,4,5")
    parser.add_argument("--test-years", type=int, default=1)
    parser.add_argument("--step-years", type=int, default=1)
    parser.add_argument("--return-column", default=None)
    parser.add_argument("--date-column", default="date")
    parser.add_argument("--periods-per-year", type=float, default=252.0 / 5.0)
    parser.add_argument("--holding-period", type=int, default=20)
    parser.add_argument("--strict-min-annualized-return", type=float, default=0.0)
    parser.add_argument("--strict-min-overlap-sharpe", type=float, default=0.0)
    parser.add_argument("--strict-max-drawdown", type=float, default=-0.20)
    args = parser.parse_args()

    sources = _parse_candidates(args.candidate)
    audit = build_shortlist_oos_split_audit(
        sources,
        train_years=tuple(int(item.strip()) for item in args.train_years.split(",") if item.strip()),
        test_years=args.test_years,
        step_years=args.step_years,
        return_column=args.return_column,
        date_column=args.date_column,
        periods_per_year=args.periods_per_year,
        holding_period=args.holding_period,
        strict_min_annualized_return=args.strict_min_annualized_return,
        strict_min_overlap_sharpe=args.strict_min_overlap_sharpe,
        strict_max_drawdown=args.strict_max_drawdown,
    )
    write_shortlist_oos_split_audit(Path(args.output_dir), audit)
    print(
        json.dumps(
            {
                "summary": audit["summary"],
                "rows": audit["rows"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _parse_candidates(values: list[str]) -> dict[str, dict[str, str]]:
    sources: dict[str, dict[str, str]] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"candidate spec must be name=path or name=path:return_column: {value}")
        name, rest = value.split("=", 1)
        if not name:
            raise ValueError(f"candidate name is empty: {value}")
        path, return_column = _split_path_return_column(rest)
        spec = {"path": path}
        if return_column:
            spec["return_column"] = return_column
        sources[name] = spec
    return sources


def _split_path_return_column(value: str) -> tuple[str, str | None]:
    path = value
    return_column = None
    suffix = Path(value).suffix.lower()
    if ":" in value and suffix not in {".csv:period_return", ".csv:overlay_return", ".csv:period_return_variant"}:
        path, return_column = value.rsplit(":", 1)
    elif ":" in value:
        path, return_column = value.rsplit(":", 1)
    return path, return_column


if __name__ == "__main__":
    main()
