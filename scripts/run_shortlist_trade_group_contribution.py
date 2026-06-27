from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.shortlist_trade_group_contribution import (  # noqa: E402
    build_trade_group_contribution_audit,
    write_trade_group_contribution_audit,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/shortlist_trade_group_contribution")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit selected-trade contribution by industry, board, exchange, HS status, or other attributes."
    )
    parser.add_argument("--trades", required=True)
    parser.add_argument("--group-column", action="append", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--contribution-column", default="entry_cash_proxy_weighted_return")
    parser.add_argument("--date-column", default="exit_date")
    parser.add_argument("--allowed-column", default="entry_allowed")
    parser.add_argument("--top-n", type=int, default=10)
    args = parser.parse_args()

    audit = build_trade_group_contribution_audit(
        trades_source=Path(args.trades),
        group_columns=tuple(args.group_column),
        contribution_column=args.contribution_column,
        date_column=args.date_column,
        allowed_column=args.allowed_column or None,
        top_n=args.top_n,
    )
    write_trade_group_contribution_audit(Path(args.output_dir), audit)
    print(
        json.dumps(
            {
                "summary": audit["summary"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
