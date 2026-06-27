from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.simulation_shortlist_entry_timed_overlay import (  # noqa: E402
    build_simulation_shortlist_entry_timed_overlay,
    write_simulation_shortlist_entry_timed_overlay,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/simulation_shortlist_entry_timed_overlay")


def run_simulation_shortlist_entry_timed_overlay_cli(
    *,
    period_events: str | Path,
    candidate_name: str,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    return_column: str = "period_return",
    date_column: str = "date",
    decision_date_column: str = "entry_date",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    target_annual_vol: float = 0.06,
    lookback_events: int = 84,
    min_exposure: float = 0.25,
    max_exposure: float = 1.0,
    self_risk_window: int = 21,
    self_risk_threshold: float = 0.0,
    self_risk_exposure: float = 0.5,
) -> dict[str, Any]:
    result = build_simulation_shortlist_entry_timed_overlay(
        Path(period_events),
        candidate_name=candidate_name,
        return_column=return_column,
        date_column=date_column,
        decision_date_column=decision_date_column,
        periods_per_year=periods_per_year,
        holding_period=holding_period,
        target_annual_vol=target_annual_vol,
        lookback_events=lookback_events,
        min_exposure=min_exposure,
        max_exposure=max_exposure,
        self_risk_window=self_risk_window,
        self_risk_threshold=self_risk_threshold,
        self_risk_exposure=self_risk_exposure,
    )
    write_simulation_shortlist_entry_timed_overlay(Path(output_dir), result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply entry-timed vol-target and self-risk overlays to period events."
    )
    parser.add_argument("--period-events", required=True)
    parser.add_argument("--candidate-name", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
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
    args = parser.parse_args()

    result = run_simulation_shortlist_entry_timed_overlay_cli(
        period_events=Path(args.period_events),
        candidate_name=args.candidate_name,
        output_dir=Path(args.output_dir),
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
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "paper_readiness": result["paper_readiness"],
                "metrics": result["metrics"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
