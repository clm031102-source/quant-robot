from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.ops.data_gap_resolution import build_data_gap_resolution_ledger, write_data_gap_resolution_ledger


DEFAULT_DATA_QUALITY_AUDIT = Path("data/reports/data_quality_gap_audit/data_quality_gap_audit.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/data_gap_resolution")
DEFAULT_RESOLUTION_FILE = Path("configs/data_gap_resolutions_cn_etf.csv")
DEFAULT_REVIEW_FILENAME = "gap_resolutions_review.csv"


def run_data_gap_resolution(
    data_quality_audit: str | Path = DEFAULT_DATA_QUALITY_AUDIT,
    resolution_file: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    audit = _read_json(data_quality_audit)
    output_path = Path(output_dir)
    selected_resolution_file = (
        Path(resolution_file) if resolution_file is not None else _default_resolution_file(output_path)
    )
    resolution_rows = _read_resolution_rows(selected_resolution_file) if selected_resolution_file is not None else []
    ledger = build_data_gap_resolution_ledger(audit, resolution_rows=resolution_rows)
    write_data_gap_resolution_ledger(output_path, ledger)
    return ledger


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Phase 4.2 data-gap resolution ledger.")
    parser.add_argument("--data-quality-audit", default=str(DEFAULT_DATA_QUALITY_AUDIT))
    parser.add_argument("--resolution-file", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    ledger = run_data_gap_resolution(
        data_quality_audit=Path(args.data_quality_audit),
        resolution_file=Path(args.resolution_file) if args.resolution_file else None,
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "stage": ledger["stage"],
                "summary": ledger["summary"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _read_resolution_rows(path: str | Path) -> list[dict[str, Any]]:
    frame = pd.read_csv(path).fillna("")
    return [dict(row) for row in frame.to_dict(orient="records")]


def _default_resolution_file(output_dir: Path) -> Path | None:
    if DEFAULT_RESOLUTION_FILE.exists():
        return DEFAULT_RESOLUTION_FILE
    review_path = output_dir / DEFAULT_REVIEW_FILENAME
    if review_path.exists():
        return review_path
    return None


if __name__ == "__main__":
    main()
