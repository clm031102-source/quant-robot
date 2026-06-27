from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.shortlist_self_risk_overlay import (  # noqa: E402
    build_shortlist_self_risk_overlay,
    write_shortlist_self_risk_overlay,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/shortlist_self_risk_overlay")


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
    parser = argparse.ArgumentParser(description="Apply PIT self-risk overlays to shortlisted event-return sources.")
    parser.add_argument(
        "--return-source",
        action="append",
        required=True,
        help="Candidate return CSV as candidate_name=path or candidate_name=path|return_column. Repeat for multiple candidates.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--policy",
        action="append",
        default=None,
        help="Policy name to run. Repeat for a subset; omit to run the default policy suite.",
    )
    parser.add_argument("--return-column")
    parser.add_argument("--date-column", default="date")
    parser.add_argument("--periods-per-year", type=float, default=252.0 / 5.0)
    parser.add_argument("--holding-period", type=int, default=20)
    args = parser.parse_args()

    audit = build_shortlist_self_risk_overlay(
        parse_return_sources(args.return_source),
        policy_names=args.policy,
        return_column=args.return_column,
        date_column=args.date_column,
        periods_per_year=args.periods_per_year,
        holding_period=args.holding_period,
    )
    write_shortlist_self_risk_overlay(Path(args.output_dir), audit)
    rows = [
        {
            key: row[key]
            for key in (
                "candidate_name",
                "policy",
                "annualized_return",
                "overlap_autocorr_adjusted_sharpe",
                "max_drawdown",
                "average_self_risk_exposure",
                "guard_event_share",
                "event_path",
            )
        }
        for row in audit["rows"][:10]
    ]
    print(
        json.dumps(
            {
                "summary": {key: value for key, value in audit["summary"].items() if key != "best_candidate"},
                "top": rows,
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
