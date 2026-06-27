from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.shortlist_official_template_cash_filter import (  # noqa: E402
    DEFAULT_CANDIDATES,
    build_official_template_cash_filter_audit,
    write_official_template_cash_filter_audit,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/shortlist_official_template_cash_filter")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Project event-risk cash filters onto a frozen official event-return template."
    )
    parser.add_argument("--template-period-returns", required=True)
    parser.add_argument("--trades", required=True)
    parser.add_argument("--dragon-tiger-source", required=True)
    parser.add_argument("--candidate", action="append", default=[])
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--template-return-column", default="period_return")
    parser.add_argument("--trade-return-column", default="entry_cash_proxy_weighted_return")
    parser.add_argument("--date-column", default="date")
    parser.add_argument("--trade-entry-date-column", default="entry_date")
    parser.add_argument("--trade-exit-date-column", default="exit_date")
    parser.add_argument("--lookback-anchor-column", default="available_date")
    parser.add_argument("--periods-per-year", type=float, default=252.0 / 5.0)
    parser.add_argument("--holding-period", type=int, default=20)
    parser.add_argument("--max-unmatched-abs-contribution", type=float, default=0.005)
    parser.add_argument("--require-candidate-improvement", action="store_true")
    args = parser.parse_args()

    audit = build_official_template_cash_filter_audit(
        template_period_returns=Path(args.template_period_returns),
        trades_source=Path(args.trades),
        dragon_tiger_source=Path(args.dragon_tiger_source),
        candidates=tuple(args.candidate or DEFAULT_CANDIDATES),
        template_return_column=args.template_return_column,
        trade_return_column=args.trade_return_column,
        date_column=args.date_column,
        trade_entry_date_column=args.trade_entry_date_column,
        trade_exit_date_column=args.trade_exit_date_column,
        lookback_anchor_column=args.lookback_anchor_column,
        periods_per_year=args.periods_per_year,
        holding_period=args.holding_period,
        max_unmatched_abs_contribution=args.max_unmatched_abs_contribution,
        require_candidate_improvement=args.require_candidate_improvement,
    )
    write_official_template_cash_filter_audit(Path(args.output_dir), audit)
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
