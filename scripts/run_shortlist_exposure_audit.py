from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.shortlist_exposure_audit import (  # noqa: E402
    DEFAULT_GROUP_COLUMNS,
    build_shortlist_exposure_audit,
    write_shortlist_exposure_audit,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/shortlist_exposure_audit")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit shortlisted trade exposure by industry/board groups.")
    parser.add_argument("--trades", required=True, help="Trade-level CSV/Parquet with weights and returns.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--group-column", action="append", default=None)
    parser.add_argument("--date-column", default="signal_date")
    parser.add_argument("--weight-column", default="target_weight")
    parser.add_argument("--return-column", default="entry_cash_proxy_weighted_return")
    parser.add_argument("--max-missing-weight-share", type=float, default=0.20)
    parser.add_argument("--max-top-weight-share-p95", type=float, default=0.45)
    parser.add_argument("--max-mean-hhi", type=float, default=0.20)
    parser.add_argument("--max-abs-return-contribution-share", type=float, default=0.45)
    args = parser.parse_args()

    audit = build_shortlist_exposure_audit(
        Path(args.trades),
        group_columns=tuple(args.group_column or DEFAULT_GROUP_COLUMNS),
        date_column=args.date_column,
        weight_column=args.weight_column,
        return_column=args.return_column,
        max_missing_weight_share=args.max_missing_weight_share,
        max_top_weight_share_p95=args.max_top_weight_share_p95,
        max_mean_hhi=args.max_mean_hhi,
        max_abs_return_contribution_share=args.max_abs_return_contribution_share,
    )
    write_shortlist_exposure_audit(args.output_dir, audit)
    print(
        json.dumps(
            {
                "summary": audit["summary"],
                "dimension_summaries": audit["dimension_summaries"],
                "blockers": audit["blockers"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
