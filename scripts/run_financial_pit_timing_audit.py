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

from quant_robot.ops.financial_pit_timing_audit import (  # noqa: E402
    build_financial_pit_timing_audit,
    write_financial_pit_timing_audit,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/financial_pit_timing_audit")


def run_financial_pit_timing_audit_cli(
    *,
    financial_root: str | Path,
    bars_roots: list[str | Path],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    allow_not_ready: bool = False,
    max_timing_rows: int = 5000,
    max_signal_lag_calendar_days: int = 30,
) -> dict[str, Any]:
    result = build_financial_pit_timing_audit(
        financial_root=Path(financial_root),
        bars_roots=[Path(root) for root in bars_roots],
        max_timing_rows=max_timing_rows,
        max_signal_lag_calendar_days=max_signal_lag_calendar_days,
    )
    write_financial_pit_timing_audit(output_dir, result)
    if not allow_not_ready and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Financial PIT timing audit is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit CN stock financial inputs for PIT timing and revision safety.")
    parser.add_argument("--financial-root", required=True)
    parser.add_argument("--bars-root", action="append", default=[], help="Bars root to scan. Can be provided multiple times.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--allow-not-ready", action="store_true")
    parser.add_argument("--max-timing-rows", type=int, default=5000)
    parser.add_argument("--max-signal-lag-calendar-days", type=int, default=30)
    args = parser.parse_args()
    result = run_financial_pit_timing_audit_cli(
        financial_root=Path(args.financial_root),
        bars_roots=[Path(root) for root in args.bars_root],
        output_dir=Path(args.output_dir),
        allow_not_ready=args.allow_not_ready,
        max_timing_rows=args.max_timing_rows,
        max_signal_lag_calendar_days=args.max_signal_lag_calendar_days,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "availability_policy": result["availability_policy"],
                "revision_policy": result["revision_policy"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
