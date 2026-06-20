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
) -> dict[str, Any]:
    root = Path(data_root)
    if bars is not None:
        frame = bars
    elif root.is_file():
        frame = load_authority_processed_bars_from_config(root, (market,))
    else:
        frame = load_processed_bars(root, market)
    audit = build_data_quality_gap_audit(frame, source_root=root)
    write_data_quality_gap_audit(output_dir, audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Phase 3.1 data-quality gap audit for processed bars.")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--market", default="CN_ETF")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    result = run_data_quality_audit(
        data_root=Path(args.data_root),
        market=args.market,
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "missing_dates": result["missing_dates"][:20],
                "repair_actions": result["repair_actions"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
