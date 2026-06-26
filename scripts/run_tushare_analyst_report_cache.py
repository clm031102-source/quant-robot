from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.adapters.tushare_adapter import TushareAdapter  # noqa: E402
from quant_robot.data.ingest.tushare_analyst_reports import run_tushare_analyst_report_cache  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("data/reports/tushare_analyst_report_cache")


def main() -> None:
    parser = argparse.ArgumentParser(description="Cache Tushare report_rc analyst reports with resume and PIT-safe normalization.")
    parser.add_argument("--start-date", default="2015-01-01")
    parser.add_argument("--end-date", default="2025-12-31")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--processed-output-dir", default="")
    parser.add_argument("--window-frequency", default="MS")
    parser.add_argument("--request-sleep-seconds", type=float, default=3660.0)
    parser.add_argument("--max-rows-per-window", type=int, default=5000)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--no-write-processed", action="store_true")
    args = parser.parse_args()

    result = run_tushare_analyst_report_cache(
        TushareAdapter(max_retries=1, retry_sleep_seconds=3.0),
        args.start_date,
        args.end_date,
        Path(args.output_dir),
        processed_output_dir=Path(args.processed_output_dir) if args.processed_output_dir else None,
        execute_write_processed=not args.no_write_processed,
        resume=not args.no_resume,
        window_frequency=args.window_frequency,
        request_sleep_seconds=args.request_sleep_seconds,
        max_rows_per_window=args.max_rows_per_window,
        progress_callback=lambda item: print(json.dumps(item, ensure_ascii=False, sort_keys=True), flush=True),
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "processed_output_dir": result["processed_output_dir"],
                "output_dir": str(Path(args.output_dir)),
                "safety": result["safety"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
