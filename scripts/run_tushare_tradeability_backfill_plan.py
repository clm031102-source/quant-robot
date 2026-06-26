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
from quant_robot.ops.tushare_tradeability_backfill_plan import run_tushare_tradeability_backfill


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or execute a sharded Tushare CN-stock tradeability backfill.")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--processed-root", required=True)
    parser.add_argument("--output-dir", default="data/reports/tushare_tradeability_long_cycle_backfill_plan")
    parser.add_argument("--report-root")
    parser.add_argument("--max-shards", type=int)
    parser.add_argument("--max-estimated-business-days-per-shard", type=int, default=25)
    parser.add_argument("--market", default="CN")
    parser.add_argument("--snapshot")
    parser.add_argument("--skip-covered", action="store_true", help="Skip shards already covered by the processed-root coverage manifest.")
    parser.add_argument("--execute", action="store_true", help="Execute selected shards. Default is plan-only.")
    parser.add_argument(
        "--execute-write-processed",
        action="store_true",
        help="Write processed tradeability datasets during execution. Default is report-only.",
    )
    args = parser.parse_args(argv)

    adapter = TushareAdapter() if args.execute else None

    def runner(**kwargs):
        if adapter is None:  # pragma: no cover - guarded by execute flag
            raise RuntimeError("TushareAdapter is required for execution")
        processed_root = kwargs.pop("processed_root")
        return run_tushare_tradeability_feed_ingest(
            adapter,
            start_date=kwargs.pop("start_date"),
            end_date=kwargs.pop("end_date"),
            output_dir=kwargs.pop("output_dir"),
            processed_output_dir=processed_root,
            execute_write_processed=kwargs.pop("execute_write_processed"),
            market=kwargs.pop("market"),
            snapshot=kwargs.pop("snapshot"),
        )

    result = run_tushare_tradeability_backfill(
        start_date=args.start_date,
        end_date=args.end_date,
        processed_root=Path(args.processed_root),
        output_dir=Path(args.output_dir),
        report_root=Path(args.report_root) if args.report_root else None,
        max_shards=args.max_shards,
        max_estimated_business_days_per_shard=args.max_estimated_business_days_per_shard,
        execute=args.execute,
        execute_write_processed=args.execute_write_processed,
        market=args.market,
        snapshot=args.snapshot,
        skip_covered=args.skip_covered,
        runner=runner if args.execute else None,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "summary": result["summary"],
                "execution_summary": result["execution_summary"],
                "output_dir": str(Path(args.output_dir)),
                "processed_root": str(Path(args.processed_root)),
                "blockers": result["blockers"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
