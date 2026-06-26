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
from quant_robot.ops.dragon_tiger_coverage_audit import run_dragon_tiger_coverage_audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit Tushare Dragon-Tiger top_list/top_inst coverage before PIT IC work."
    )
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--market", default="CN")
    parser.add_argument("--processed-root")
    parser.add_argument("--min-non-empty-ratio", type=float, default=0.8)
    parser.add_argument("--progress-jsonl")
    parser.add_argument(
        "--execute-write-processed",
        action="store_true",
        help="Write normalized processed Dragon-Tiger datasets. Default is report-only.",
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

    result = run_dragon_tiger_coverage_audit(
        TushareAdapter(),
        args.start_date,
        args.end_date,
        Path(args.output_dir),
        market=args.market,
        processed_root=Path(args.processed_root) if args.processed_root else None,
        execute_write_processed=args.execute_write_processed,
        min_non_empty_ratio=args.min_non_empty_ratio,
        progress_callback=progress_callback,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
