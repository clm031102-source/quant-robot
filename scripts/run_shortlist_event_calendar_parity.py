from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.shortlist_event_calendar_parity import (  # noqa: E402
    build_event_calendar_parity_audit,
    write_event_calendar_parity_audit,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/shortlist_event_calendar_parity")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit event-calendar parity between reference and generated returns.")
    parser.add_argument("--reference", required=True)
    parser.add_argument("--generated", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--reference-return-column", default="period_return")
    parser.add_argument("--generated-return-column", default="period_return")
    parser.add_argument("--date-column", default="date")
    parser.add_argument("--periods-per-year", type=float, default=252.0 / 5.0)
    parser.add_argument("--holding-period", type=int, default=20)
    parser.add_argument("--metric-tolerance", type=float, default=0.005)
    parser.add_argument("--date-return-tolerance", type=float, default=0.0001)
    args = parser.parse_args()

    audit = build_event_calendar_parity_audit(
        Path(args.reference),
        Path(args.generated),
        reference_return_column=args.reference_return_column,
        generated_return_column=args.generated_return_column,
        date_column=args.date_column,
        periods_per_year=args.periods_per_year,
        holding_period=args.holding_period,
        metric_tolerance=args.metric_tolerance,
        date_return_tolerance=args.date_return_tolerance,
    )
    write_event_calendar_parity_audit(args.output_dir, audit)
    print(
        json.dumps(
            {
                "summary": audit["summary"],
                "metric_diffs": audit["metric_diffs"],
                "blockers": audit["blockers"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
