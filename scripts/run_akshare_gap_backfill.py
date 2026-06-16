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

from quant_robot.data.akshare_gap_backfill import GapBackfillAdapter, run_akshare_gap_backfill


DEFAULT_GAP_ROWS = Path("data/reports/data_gap_evidence/data_gap_evidence_rows.csv")
DEFAULT_PROCESSED_ROOT = Path("data/processed/etf_csv")
DEFAULT_OUTPUT_DIR = Path("data/reports/akshare_gap_backfill")


def run_akshare_gap_backfill_cli(
    gap_rows: str | Path = DEFAULT_GAP_ROWS,
    processed_root: str | Path = DEFAULT_PROCESSED_ROOT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    adapter: GapBackfillAdapter | None = None,
) -> dict[str, Any]:
    rows = _read_gap_rows(gap_rows)
    return run_akshare_gap_backfill(
        gap_rows=rows,
        processed_root=processed_root,
        output_dir=output_dir,
        adapter=adapter,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Attempt local CN ETF data-gap backfill through AKShare.")
    parser.add_argument("--gap-rows", default=str(DEFAULT_GAP_ROWS))
    parser.add_argument("--processed-root", default=str(DEFAULT_PROCESSED_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    report = run_akshare_gap_backfill_cli(
        gap_rows=Path(args.gap_rows),
        processed_root=Path(args.processed_root),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps({"stage": report["stage"], "summary": report["summary"], "output_dir": args.output_dir}, indent=2, sort_keys=True))


def _read_gap_rows(path: str | Path) -> list[dict[str, Any]]:
    frame = pd.read_csv(path).fillna("")
    return [dict(row) for row in frame.to_dict(orient="records")]


if __name__ == "__main__":
    main()
