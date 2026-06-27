from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.shortlist_event_beta_audit import (  # noqa: E402
    build_shortlist_event_beta_audit,
    write_shortlist_event_beta_audit,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/shortlist_event_beta_audit")


def parse_return_sources(values: list[str]) -> dict[str, dict[str, str]]:
    sources: dict[str, dict[str, str]] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--return-source must use candidate_name=path or candidate_name=path|return_column")
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
    parser = argparse.ArgumentParser(description="Audit event-return sources against benchmark event returns.")
    parser.add_argument(
        "--return-source",
        action="append",
        required=True,
        help="Candidate return CSV as candidate_name=path or candidate_name=path|return_column. Repeat for multiple candidates.",
    )
    parser.add_argument("--benchmark-source", required=True)
    parser.add_argument("--benchmark", action="append", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--return-column")
    parser.add_argument("--date-column", default="date")
    parser.add_argument("--benchmark-column", default="benchmark")
    parser.add_argument("--benchmark-return-column", default="period_return_benchmark")
    parser.add_argument("--periods-per-year", type=float, default=252.0 / 5.0)
    parser.add_argument("--holding-period", type=int, default=20)
    args = parser.parse_args()

    audit = build_shortlist_event_beta_audit(
        parse_return_sources(args.return_source),
        benchmark_source=Path(args.benchmark_source),
        benchmarks=args.benchmark,
        return_column=args.return_column,
        date_column=args.date_column,
        benchmark_column=args.benchmark_column,
        benchmark_return_column=args.benchmark_return_column,
        periods_per_year=args.periods_per_year,
        holding_period=args.holding_period,
    )
    write_shortlist_event_beta_audit(Path(args.output_dir), audit)
    print(
        json.dumps(
            {
                "summary": audit["summary"],
                "top": audit["rows"][:12],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
