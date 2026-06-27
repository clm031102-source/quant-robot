from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.shortlist_event_return_wrapper import (  # noqa: E402
    build_event_return_wrapper_audit,
    write_event_return_wrapper_audit,
)


def parse_return_sources(values: list[str]) -> dict[str, dict[str, str]]:
    sources: dict[str, dict[str, str]] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--return-source must use candidate_name=path or candidate_name=path|return_column")
        name, rest = value.split("=", 1)
        spec = {"path": str(Path(rest))}
        if "|" in rest:
            path, return_column = rest.rsplit("|", 1)
            spec = {"path": str(Path(path)), "return_column": return_column}
        sources[name] = spec
    return sources


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply vol-target and reference risk-off wrappers to event returns.")
    parser.add_argument("--return-source", action="append", required=True)
    parser.add_argument("--reference-schema-source", default=None)
    parser.add_argument("--riskoff-multiplier", action="append", type=float, default=None)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--return-column")
    parser.add_argument("--date-column", default="date")
    parser.add_argument("--decision-date-column", default="entry_date")
    parser.add_argument("--periods-per-year", type=float, default=252.0 / 5.0)
    parser.add_argument("--holding-period", type=int, default=20)
    parser.add_argument("--target-annual-vol", type=float, default=0.06)
    parser.add_argument("--lookback-events", type=int, default=84)
    parser.add_argument("--min-exposure", type=float, default=0.25)
    parser.add_argument("--max-exposure", type=float, default=1.0)
    parser.add_argument("--reuse-reference-vol-target-exposure", action="store_true")
    args = parser.parse_args()

    audit = build_event_return_wrapper_audit(
        return_sources=parse_return_sources(args.return_source),
        reference_schema_source=Path(args.reference_schema_source) if args.reference_schema_source else None,
        riskoff_multipliers=tuple(args.riskoff_multiplier or [1.0]),
        return_column=args.return_column,
        date_column=args.date_column,
        decision_date_column=args.decision_date_column,
        periods_per_year=args.periods_per_year,
        holding_period=args.holding_period,
        target_annual_vol=args.target_annual_vol,
        lookback_events=args.lookback_events,
        min_exposure=args.min_exposure,
        max_exposure=args.max_exposure,
        reuse_reference_vol_target_exposure=args.reuse_reference_vol_target_exposure,
    )
    write_event_return_wrapper_audit(Path(args.output_dir), audit)
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


if __name__ == "__main__":
    main()
