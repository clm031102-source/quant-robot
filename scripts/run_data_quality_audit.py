from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.gap_audit import build_data_quality_gap_audit, write_data_quality_gap_audit
from quant_robot.storage.authority_bars import load_authority_processed_bars_from_config
from quant_robot.storage.processed_bars import load_processed_bars


DEFAULT_DATA_ROOT = Path("data/processed/etf_csv")
DEFAULT_OUTPUT_DIR = Path("data/reports/data_quality_gap_audit")


def run_data_quality_audit(
    data_root: str | Path = DEFAULT_DATA_ROOT,
    market: str = "CN_ETF",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    bars: pd.DataFrame | None = None,
    calendar_path: str | Path | None = None,
    expected_dates: list[object] | None = None,
) -> dict[str, Any]:
    if calendar_path is not None and expected_dates is not None:
        raise ValueError("Provide calendar_path or expected_dates, not both")
    root = Path(data_root)
    if bars is not None:
        frame = bars
    elif root.is_file():
        frame = load_authority_processed_bars_from_config(root, (market,))
    else:
        frame = load_processed_bars(root, market)
    calendar_dates = expected_dates
    calendar_source = None
    if calendar_path is not None:
        calendar_source = str(Path(calendar_path))
        calendar_dates = _load_calendar_dates(calendar_path, market)
    audit = build_data_quality_gap_audit(
        frame,
        expected_dates=calendar_dates,
        source_root=root,
        calendar_source=calendar_source,
    )
    write_data_quality_gap_audit(output_dir, audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Phase 3.1 data-quality gap audit for processed bars.")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--market", default="CN_ETF")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--calendar-path", help="CSV or JSON file containing the explicit trading calendar")
    args = parser.parse_args()
    result = run_data_quality_audit(
        data_root=Path(args.data_root),
        market=args.market,
        output_dir=Path(args.output_dir),
        calendar_path=Path(args.calendar_path) if args.calendar_path else None,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "summary": result["summary"],
                "decision": result["decision"],
                "missing_dates": result["missing_dates"][:20],
                "repair_actions": result["repair_actions"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    if result["status"] != "cleared":
        raise SystemExit(3)


def _load_calendar_dates(path: str | Path, market: str) -> list[object]:
    calendar_path = Path(path)
    if not calendar_path.is_file():
        raise ValueError(f"Trading calendar file does not exist: {calendar_path}")
    suffix = calendar_path.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(calendar_path)
    elif suffix == ".json":
        payload = json.loads(calendar_path.read_text(encoding="utf-8-sig"))
        if isinstance(payload, dict):
            payload = payload.get(market) or payload.get(market.upper()) or payload.get("dates") or payload.get("rows")
        if isinstance(payload, list) and (not payload or not isinstance(payload[0], dict)):
            return list(payload)
        frame = pd.DataFrame(payload)
    else:
        raise ValueError("Trading calendar must be a CSV or JSON file")
    if "market" in frame.columns:
        frame = frame[frame["market"].astype(str).str.upper() == market.upper()]
    if "is_open" in frame.columns:
        frame = frame[_truthy_calendar_flag(frame["is_open"])]
    date_column = next(
        (column for column in ("date", "trade_date", "cal_date", "session_date") if column in frame.columns),
        None,
    )
    if date_column is None:
        raise ValueError("Trading calendar is missing a date column")
    return frame[date_column].dropna().tolist()


def _truthy_calendar_flag(series: pd.Series) -> pd.Series:
    normalized = series.astype(str).str.strip().str.lower()
    return normalized.isin({"1", "true", "yes", "y", "open"})


if __name__ == "__main__":
    main()
