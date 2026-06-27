from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.shortlist_return_block_audit import (  # noqa: E402
    build_shortlist_return_block_audit,
    write_shortlist_return_block_audit,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/shortlist_return_block_audit")


def parse_return_sources(values: list[str]) -> dict[str, dict[str, str]]:
    sources: dict[str, dict[str, str]] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--return-source must use candidate_name=path")
        name, path = value.split("=", 1)
        name = name.strip()
        if not name:
            raise ValueError("--return-source candidate_name cannot be empty")
        path = path.strip()
        return_column = None
        if "|" in path:
            path, return_column = path.rsplit("|", 1)
            path = path.strip()
            return_column = return_column.strip() or None
        spec = {"path": str(Path(path))}
        if return_column:
            spec["return_column"] = return_column
        sources[name] = spec
    return sources


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit shortlisted candidate returns for block dependence.")
    parser.add_argument(
        "--return-source",
        action="append",
        required=True,
        help="Candidate return CSV as candidate_name=path. Repeat for multiple candidates.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--return-column")
    parser.add_argument("--date-column", default="date")
    parser.add_argument("--periods-per-year", type=float, default=252.0 / 5.0)
    parser.add_argument("--holding-period", type=int, default=20)
    parser.add_argument("--concentration-months", type=int, default=3)
    parser.add_argument("--max-best-month-log-share", type=float, default=0.60)
    parser.add_argument("--min-leave-one-year-annualized-return", type=float, default=0.0)
    parser.add_argument("--min-leave-one-year-overlap-sharpe", type=float, default=0.0)
    args = parser.parse_args()

    audit = build_shortlist_return_block_audit(
        parse_return_sources(args.return_source),
        return_column=args.return_column,
        date_column=args.date_column,
        periods_per_year=args.periods_per_year,
        holding_period=args.holding_period,
        concentration_months=args.concentration_months,
        max_best_month_log_share=args.max_best_month_log_share,
        min_leave_one_year_annualized_return=args.min_leave_one_year_annualized_return,
        min_leave_one_year_overlap_sharpe=args.min_leave_one_year_overlap_sharpe,
    )
    write_shortlist_return_block_audit(Path(args.output_dir), audit)
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
