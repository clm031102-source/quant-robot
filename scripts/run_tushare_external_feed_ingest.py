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
from quant_robot.data.ingest.tushare_external_feeds import run_tushare_external_feed_ingest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Tushare external CN-stock feed ingestion with report-only default.",
        epilog=(
            "Safety: Report-only still may call Tushare when fetching source data or refreshing a missing, empty, "
            "or invalid LPR cache. Use --execute-write-processed only when intentionally writing ignored data outputs."
        ),
    )
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--output-dir", default="data/reports/tushare_external_feed_ingest")
    parser.add_argument("--market", default="CN")
    parser.add_argument("--index-symbol", default="000001.SH")
    parser.add_argument("--lpr-cache-path", help="Optional JSON cache path for the Tushare shibor_lpr endpoint.")
    parser.add_argument("--report-copy-dir", help="Optional directory to copy this shard's ingestion report JSON.")
    parser.add_argument("--progress-jsonl", help="Optional JSONL file for per-endpoint ingestion progress events.")
    parser.add_argument(
        "--execute-write-processed",
        action="store_true",
        help="Write processed external feed datasets. Default is report-only.",
    )
    args = parser.parse_args(argv)
    progress_callback = None
    if args.progress_jsonl:
        progress_path = Path(args.progress_jsonl)
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        progress_path.write_text("", encoding="utf-8")

        def progress_callback(event: dict[str, object]) -> None:
            with progress_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, sort_keys=True) + "\n")

    result = run_tushare_external_feed_ingest(
        TushareAdapter(),
        args.start_date,
        args.end_date,
        Path(args.output_dir),
        execute_write_processed=args.execute_write_processed,
        market=args.market,
        index_symbol=args.index_symbol,
        lpr_cache_path=Path(args.lpr_cache_path) if args.lpr_cache_path else None,
        progress_callback=progress_callback,
    )
    if args.report_copy_dir:
        report_copy_dir = Path(args.report_copy_dir)
        report_copy_dir.mkdir(parents=True, exist_ok=True)
        (report_copy_dir / "external_feed_ingestion_report.json").write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
