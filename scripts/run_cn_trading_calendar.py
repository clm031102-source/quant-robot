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

from quant_robot.data.adapters.tushare_adapter import TushareAdapter  # noqa: E402
from quant_robot.data.cn_trading_calendar import (  # noqa: E402
    CALENDAR_FILENAME,
    MANIFEST_FILENAME,
    REQUIRED_EXCHANGES,
    build_cn_trading_calendar,
    validate_cn_trading_calendar_artifact,
    write_cn_trading_calendar,
)


DEFAULT_OUTPUT_DIR = Path("data/processed/trading_calendars/cn_tushare_2015_2025")
DEFAULT_START_DATE = "2015-01-01"
DEFAULT_END_DATE = "2025-12-31"


def run_cn_trading_calendar(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    adapter: Any | None = None,
    validate_only: bool = False,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    calendar_path = output_path / CALENDAR_FILENAME
    manifest_path = output_path / MANIFEST_FILENAME
    if validate_only:
        manifest = validate_cn_trading_calendar_artifact(
            calendar_path,
            manifest_path,
            expected_start_date=start_date,
            expected_end_date=end_date,
        )
        return {
            "calendar_path": str(calendar_path),
            "manifest_path": str(manifest_path),
            "manifest": manifest,
        }

    source = adapter if adapter is not None else TushareAdapter()
    frames = {
        exchange: source.fetch_trade_calendar(start_date, end_date, exchange=exchange)
        for exchange in REQUIRED_EXCHANGES
    }
    calendar, manifest = build_cn_trading_calendar(frames, start_date=start_date, end_date=end_date)
    return write_cn_trading_calendar(output_path, calendar, manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch or validate the provider-backed CN trading calendar.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        result = run_cn_trading_calendar(
            output_dir=Path(args.output_dir),
            start_date=args.start_date,
            end_date=args.end_date,
            validate_only=args.validate_only,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    manifest = result["manifest"]
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "summary": manifest["summary"],
                "calendar_path": result["calendar_path"],
                "manifest_path": result["manifest_path"],
                "safety": manifest["safety"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
