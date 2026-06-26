from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.adapters.tushare_adapter import TushareAdapter
from quant_robot.data.ingest.tushare_tradeability_feeds import run_tushare_tradeability_feed_ingest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Tushare CN-stock tradeability feed ingestion.")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--output-dir", default="data/reports/tushare_tradeability_feed_ingest")
    parser.add_argument("--processed-output-dir")
    parser.add_argument("--market", default="CN")
    parser.add_argument("--snapshot", default=None)
    parser.add_argument(
        "--execute-write-processed",
        action="store_true",
        help="Write processed tradeability datasets. Default is report-only.",
    )
    args = parser.parse_args(argv)
    result = run_tushare_tradeability_feed_ingest(
        TushareAdapter(),
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=Path(args.output_dir),
        processed_output_dir=Path(args.processed_output_dir) if args.processed_output_dir else None,
        execute_write_processed=args.execute_write_processed,
        market=args.market,
        snapshot=args.snapshot,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
