from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.simulation_shortlist_entry_timed_grid import (  # noqa: E402
    DEFAULT_PATTERN,
    build_simulation_shortlist_entry_timed_grid,
    discover_entry_timed_period_event_sources,
    write_simulation_shortlist_entry_timed_grid,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/simulation_shortlist_entry_timed_grid")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch rebuild period-return candidates with entry-timed exposure controls."
    )
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--pattern", default=DEFAULT_PATTERN)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--candidate-prefix", default="entry_timed")
    parser.add_argument("--return-column", default="period_return")
    parser.add_argument("--date-column", default="date")
    parser.add_argument("--decision-date-column", default="entry_date")
    parser.add_argument("--periods-per-year", type=float, default=252.0 / 5.0)
    parser.add_argument("--holding-period", type=int, default=20)
    parser.add_argument("--target-annual-vol", type=float, default=0.06)
    parser.add_argument("--lookback-events", type=int, default=84)
    parser.add_argument("--min-exposure", type=float, default=0.25)
    parser.add_argument("--max-exposure", type=float, default=1.0)
    parser.add_argument("--self-risk-window", type=int, default=21)
    parser.add_argument("--self-risk-threshold", type=float, default=0.0)
    parser.add_argument("--self-risk-exposure", type=float, default=0.5)
    parser.add_argument("--max-drawdown-limit", type=float, default=-0.30)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    sources = discover_entry_timed_period_event_sources(
        args.source_dir,
        pattern=args.pattern,
        limit=args.limit,
    )
    result = build_simulation_shortlist_entry_timed_grid(
        sources,
        candidate_prefix=args.candidate_prefix,
        return_column=args.return_column,
        date_column=args.date_column,
        decision_date_column=args.decision_date_column,
        periods_per_year=args.periods_per_year,
        holding_period=args.holding_period,
        target_annual_vol=args.target_annual_vol,
        lookback_events=args.lookback_events,
        min_exposure=args.min_exposure,
        max_exposure=args.max_exposure,
        self_risk_window=args.self_risk_window,
        self_risk_threshold=args.self_risk_threshold,
        self_risk_exposure=args.self_risk_exposure,
        max_drawdown_limit=args.max_drawdown_limit,
    )
    summary_result = write_simulation_shortlist_entry_timed_grid(args.output_dir, result)
    print(
        json.dumps(
            {
                "output_dir": str(Path(args.output_dir)),
                "summary": summary_result["summary"],
                "top": summary_result["rows"][: int(args.top)],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
