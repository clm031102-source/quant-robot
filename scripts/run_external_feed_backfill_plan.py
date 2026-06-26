from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.external_feed_backfill_plan import (  # noqa: E402
    build_external_feed_backfill_plan,
    write_external_feed_backfill_plan,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a sharded Tushare external-feed backfill plan.")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--report-root")
    parser.add_argument("--output-dir", default="data/reports/external_feed_long_cycle_backfill_plan")
    parser.add_argument("--shard-months", type=int, default=1)
    parser.add_argument("--max-estimated-business-days-per-shard", type=int, default=25)
    parser.add_argument("--market", default="CN")
    args = parser.parse_args(argv)
    plan = build_external_feed_backfill_plan(
        start_date=args.start_date,
        end_date=args.end_date,
        output_root=args.output_root,
        report_root=args.report_root,
        shard_months=args.shard_months,
        max_estimated_business_days_per_shard=args.max_estimated_business_days_per_shard,
        market=args.market,
    )
    write_external_feed_backfill_plan(plan, Path(args.output_dir))
    print(
        json.dumps(
            {
                "status": plan["status"],
                "summary": plan["summary"],
                "blockers": plan["blockers"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
