from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.analyst_report_quota_preflight import (  # noqa: E402
    DEFAULT_MAX_DAILY_REQUESTS,
    build_analyst_report_quota_preflight,
    write_analyst_report_quota_preflight,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/analyst_report_quota_preflight")


def run_analyst_report_quota_preflight(
    *,
    report_root: list[str | Path],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    target_date: str | None = None,
    max_daily_requests: int = DEFAULT_MAX_DAILY_REQUESTS,
) -> dict[str, Any]:
    packet = build_analyst_report_quota_preflight(
        report_roots=report_root,
        target_date=target_date,
        max_daily_requests=max_daily_requests,
    )
    write_analyst_report_quota_preflight(output_dir, packet)
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description="Preflight local Tushare report_rc cache quota before fetching analyst reports.")
    parser.add_argument("--report-root", action="append", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--target-date")
    parser.add_argument("--max-daily-requests", type=int, default=DEFAULT_MAX_DAILY_REQUESTS)
    args = parser.parse_args()
    packet = run_analyst_report_quota_preflight(
        report_root=args.report_root or ["data/reports"],
        output_dir=args.output_dir,
        target_date=args.target_date,
        max_daily_requests=args.max_daily_requests,
    )
    print(
        json.dumps(
            {
                "status": "allowed" if packet["decision"]["request_allowed"] else "blocked",
                "summary": packet["summary"],
                "decision": packet["decision"],
                "output_dir": str(Path(args.output_dir)),
                "safety": packet["safety"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
