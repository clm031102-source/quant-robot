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

from quant_robot.ops.index_rebalance_event_audit import (
    build_index_rebalance_event_audit,
    write_index_rebalance_event_audit,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/index_rebalance_event_audit")


def run_index_rebalance_event_audit_cli(
    *,
    index_weight_path: str | Path,
    trade_calendar_path: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    min_abs_weight_change: float = 0.5,
) -> dict[str, Any]:
    result = build_index_rebalance_event_audit(
        index_weight=_read_frame(index_weight_path),
        trade_calendar=_read_frame(trade_calendar_path),
        min_abs_weight_change=min_abs_weight_change,
    )
    write_index_rebalance_event_audit(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CN stock index rebalance event audit.")
    parser.add_argument("--index-weight", required=True)
    parser.add_argument("--trade-calendar", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-abs-weight-change", type=float, default=0.5)
    args = parser.parse_args()
    result = run_index_rebalance_event_audit_cli(
        index_weight_path=args.index_weight,
        trade_calendar_path=args.trade_calendar,
        output_dir=args.output_dir,
        min_abs_weight_change=args.min_abs_weight_change,
    )
    print(json.dumps(_sanitize(result), indent=2, sort_keys=True))


def _read_frame(path: str | Path) -> pd.DataFrame:
    input_path = Path(path)
    if input_path.suffix.lower() == ".parquet":
        return pd.read_parquet(input_path)
    return pd.read_csv(input_path)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


if __name__ == "__main__":
    main()
