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

from quant_robot.ops.financial_pit_signal_date_filter import (  # noqa: E402
    build_financial_pit_signal_date_filter,
    write_financial_pit_signal_date_filter,
)


DEFAULT_OUTPUT_ROOT = Path("data/processed/financial_pit_signal_date_filter")


def run_financial_pit_signal_date_filter_cli(
    *,
    financial_root: str | Path,
    bars_roots: list[str | Path],
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    max_signal_lag_calendar_days: int = 30,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    result = build_financial_pit_signal_date_filter(
        financial_root=Path(financial_root),
        bars_roots=[Path(root) for root in bars_roots],
        max_signal_lag_calendar_days=max_signal_lag_calendar_days,
    )
    write_financial_pit_signal_date_filter(output_root, result)
    if not allow_not_ready and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Financial PIT signal-date filter is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Create PIT-clean financial inputs with strict signal dates.")
    parser.add_argument("--financial-root", required=True)
    parser.add_argument("--bars-root", action="append", default=[])
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--max-signal-lag-calendar-days", type=int, default=30)
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    result = run_financial_pit_signal_date_filter_cli(
        financial_root=Path(args.financial_root),
        bars_roots=[Path(root) for root in args.bars_root],
        output_root=Path(args.output_root),
        max_signal_lag_calendar_days=args.max_signal_lag_calendar_days,
        allow_not_ready=args.allow_not_ready,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "output_root": str(Path(args.output_root)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
