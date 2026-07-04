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
from quant_robot.ops.analyst_report_quota_preflight import (  # noqa: E402
    DEFAULT_MAX_DAILY_REQUESTS,
    SAFETY as QUOTA_PREFLIGHT_SAFETY,
    build_analyst_report_quota_preflight,
    write_analyst_report_quota_preflight,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/tushare_analyst_report_cache")
DEFAULT_QUOTA_PREFLIGHT_OUTPUT_DIR = Path("data/reports/analyst_report_quota_preflight")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Cache Tushare report_rc analyst reports with resume and PIT-safe normalization. "
            "By default this command runs local quota preflight first and exits 3 when blocked."
        )
    )
    parser.add_argument("--start-date", default="2015-01-01", help="Inclusive report window start date.")
    parser.add_argument("--end-date", default="2025-12-31", help="Inclusive report window end date.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for cache summary reports.")
    parser.add_argument("--processed-output-dir", default="", help="Directory for normalized processed outputs.")
    parser.add_argument("--window-frequency", default="MS", help="Pandas window frequency for provider requests.")
    parser.add_argument("--request-sleep-seconds", type=float, default=3660.0, help="Sleep between provider request windows.")
    parser.add_argument("--max-rows-per-window", type=int, default=5000, help="Warn when a provider window reaches this row count.")
    parser.add_argument("--no-resume", action="store_true", help="Do not reuse existing processed window files.")
    parser.add_argument("--no-write-processed", action="store_true", help="Run without writing normalized processed outputs.")
    parser.add_argument("--continue-after-rate-limit", action="store_true", help="Continue later windows after a provider rate-limit error.")
    parser.add_argument(
        "--skip-quota-preflight",
        action="store_true",
        help="Exceptional offline or controlled local replay only; never use for normal provider-backed fetches.",
    )
    parser.add_argument(
        "--skip-quota-preflight-reason",
        default="",
        help="Required human-readable reason when --skip-quota-preflight is used.",
    )
    parser.add_argument(
        "--quota-report-root",
        action="append",
        default=None,
        help="Local report root scanned by quota preflight; repeat to include multiple roots.",
    )
    parser.add_argument(
        "--quota-output-dir",
        default=str(DEFAULT_QUOTA_PREFLIGHT_OUTPUT_DIR),
        help="Directory for quota preflight JSON/Markdown evidence.",
    )
    parser.add_argument("--quota-target-date", help="Local date to count same-day report_rc requests against.")
    parser.add_argument(
        "--quota-max-daily-requests",
        type=int,
        default=DEFAULT_MAX_DAILY_REQUESTS,
        help="Local same-day report_rc request budget before preflight blocks.",
    )
    parser.add_argument(
        "--quota-preflight-only",
        action="store_true",
        help="Run quota preflight and stop before cache execution; does not call Tushare.",
    )
    args = parser.parse_args()

    if args.quota_preflight_only and args.skip_quota_preflight:
        parser.error("--quota-preflight-only cannot be combined with --skip-quota-preflight")

    if args.skip_quota_preflight:
        skip_reason = str(args.skip_quota_preflight_reason).strip()
        if not skip_reason:
            parser.error("--skip-quota-preflight requires --skip-quota-preflight-reason")
        print(
            json.dumps(
                {
                    "status": "skipped",
                    "summary": {
                        "quota_preflight_skipped": True,
                        "output_dir": str(Path(args.output_dir)),
                        "processed_output_dir": str(Path(args.processed_output_dir)) if args.processed_output_dir else "",
                    },
                    "decision": {
                        "request_allowed": True,
                        "blockers": [],
                        "skip_reason": skip_reason,
                        "next_action": "run_cache_without_local_quota_preflight",
                    },
                    "safety": QUOTA_PREFLIGHT_SAFETY,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            flush=True,
        )
    else:
        quota_packet = build_analyst_report_quota_preflight(
            report_roots=args.quota_report_root or ["data/reports"],
            target_date=args.quota_target_date,
            max_daily_requests=args.quota_max_daily_requests,
        )
        write_analyst_report_quota_preflight(args.quota_output_dir, quota_packet)
        print(
            json.dumps(
                {
                    "status": "allowed" if quota_packet["decision"]["request_allowed"] else "blocked",
                    "summary": quota_packet["summary"],
                    "decision": quota_packet["decision"],
                    "output_dir": str(Path(args.quota_output_dir)),
                    "safety": quota_packet["safety"],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            flush=True,
        )
        if not quota_packet["decision"]["request_allowed"]:
            raise SystemExit(3)
        if args.quota_preflight_only:
            print(
                json.dumps(
                    {
                        "status": "preflight_only",
                        "summary": {
                            "cache_execution_skipped": True,
                            "output_dir": str(Path(args.output_dir)),
                            "processed_output_dir": str(Path(args.processed_output_dir)) if args.processed_output_dir else "",
                        },
                        "decision": {
                            "request_allowed": True,
                            "blockers": [],
                            "next_action": "rerun_without_quota_preflight_only_to_cache",
                        },
                        "safety": quota_packet["safety"],
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                flush=True,
            )
            return

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
        stop_on_rate_limit=not args.continue_after_rate_limit,
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
