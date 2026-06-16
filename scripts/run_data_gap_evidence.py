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

from quant_robot.ops.data_gap_evidence import build_data_gap_evidence_pack, write_data_gap_evidence_pack


DEFAULT_GAP_ROWS = Path("data/reports/data_gap_resolution/data_gap_resolution_rows.csv")
DEFAULT_RAW_DIR = Path("data/raw/tradingview_etf_csv")
DEFAULT_OUTPUT_DIR = Path("data/reports/data_gap_evidence")


def run_data_gap_evidence(
    gap_rows: str | Path = DEFAULT_GAP_ROWS,
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    rows = _read_gap_rows(gap_rows)
    pack = build_data_gap_evidence_pack(rows, raw_dir)
    write_data_gap_evidence_pack(output_dir, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local evidence pack for unresolved ETF data gaps.")
    parser.add_argument("--gap-rows", default=str(DEFAULT_GAP_ROWS))
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    pack = run_data_gap_evidence(
        gap_rows=Path(args.gap_rows),
        raw_dir=Path(args.raw_dir),
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "summary": pack["summary"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_gap_rows(path: str | Path) -> list[dict[str, Any]]:
    frame = pd.read_csv(path).fillna("")
    return [dict(row) for row in frame.to_dict(orient="records")]


if __name__ == "__main__":
    main()
