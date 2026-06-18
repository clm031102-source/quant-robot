from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.cn_stock_long_history_backfill import run_cn_stock_long_history_backfill


DEFAULT_OUTPUT_DIR = Path("data/processed/cn_stock_long_history_2015_202306")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill CN stock long-history Tushare inputs by monthly chunks.")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--market", default="CN")
    parser.add_argument(
        "--interfaces",
        default="daily,daily_basic,moneyflow",
        help="Comma-separated interfaces: daily,daily_basic,moneyflow",
    )
    parser.add_argument("--daily-adjustment-retries", type=int, default=2)
    parser.add_argument("--empty-raw-retries", type=int, default=2)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    interfaces = tuple(item.strip() for item in args.interfaces.split(",") if item.strip())
    pack = run_cn_stock_long_history_backfill(
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=Path(args.output_dir),
        execute=args.execute,
        interfaces=interfaces,
        market=args.market,
        daily_adjustment_retries=args.daily_adjustment_retries,
        empty_raw_retries=args.empty_raw_retries,
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "mode": pack["mode"],
                "market": pack["market"],
                "start_date": pack["start_date"],
                "end_date": pack["end_date"],
                "output_dir": pack["output_dir"],
                "summary": pack["summary"],
                "live_boundary_allowed": pack["live_boundary_allowed"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
