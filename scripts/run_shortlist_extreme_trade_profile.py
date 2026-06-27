from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.shortlist_extreme_trade_profile import (  # noqa: E402
    build_extreme_trade_profile,
    write_extreme_trade_profile,
)


DEFAULT_GROUP_COLUMNS = (
    "stock_market",
    "exchange",
    "industry",
    "entry_allowed",
    "exit_allowed",
    "fully_tradeable_roundtrip",
    "dragon_cash_filter",
    "public_factor_tilt",
)
DEFAULT_NUMERIC_COLUMNS = (
    "entry_amount",
    "participation_rate",
    "turnover_rate",
    "turnover_rate_f",
    "volume_ratio",
    "pe_ttm",
    "pb",
    "ps_ttm",
    "total_mv",
    "circ_mv",
    "target_weight",
    "entry_tilt_multiplier",
    "final_exposure",
    "final_target_weight",
)
DEFAULT_OUTPUT_DIR = Path("data/reports/shortlist_extreme_trade_profile")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Profile active extreme trade returns by entry-known attributes."
    )
    parser.add_argument("--trades", required=True, help="Trade-level CSV/Parquet.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--group-column", action="append", default=None)
    parser.add_argument("--numeric-column", action="append", default=None)
    parser.add_argument("--threshold", type=float, default=0.50)
    parser.add_argument("--gross-return-column", default="gross_return")
    parser.add_argument("--contribution-column", default="final_return_contribution")
    parser.add_argument("--active-weight-column", default="final_target_weight")
    parser.add_argument("--top-n", type=int, default=50)
    parser.add_argument("--min-group-extreme-count", type=int, default=3)
    parser.add_argument("--min-extreme-rate-lift", type=float, default=2.0)
    args = parser.parse_args()

    audit = build_extreme_trade_profile(
        Path(args.trades),
        group_columns=tuple(args.group_column or DEFAULT_GROUP_COLUMNS),
        numeric_columns=tuple(args.numeric_column or DEFAULT_NUMERIC_COLUMNS),
        threshold=args.threshold,
        gross_return_column=args.gross_return_column,
        contribution_column=args.contribution_column,
        active_weight_column=args.active_weight_column,
        top_n=args.top_n,
        min_group_extreme_count=args.min_group_extreme_count,
        min_extreme_rate_lift=args.min_extreme_rate_lift,
    )
    write_extreme_trade_profile(args.output_dir, audit)
    print(
        json.dumps(
            {
                "summary": audit["summary"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
