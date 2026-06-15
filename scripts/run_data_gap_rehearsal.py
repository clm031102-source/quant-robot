from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_robot.ops.data_gap_rehearsal import build_data_gap_rehearsal, write_data_gap_rehearsal


DEFAULT_DATA_QUALITY_AUDIT = Path("data/reports/data_quality_gap_audit/data_quality_gap_audit.json")
DEFAULT_DATA_GAP_RESOLUTION = Path("data/reports/data_gap_resolution/data_gap_resolution_ledger.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/data_gap_rehearsal")


def run_data_gap_rehearsal(
    data_quality_audit: str | Path = DEFAULT_DATA_QUALITY_AUDIT,
    data_gap_resolution: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    sample_size: int = 2,
) -> dict[str, Any]:
    audit = _read_json(data_quality_audit)
    baseline = _read_optional_json(data_gap_resolution)
    rehearsal = build_data_gap_rehearsal(audit, sample_size=sample_size, baseline_ledger=baseline)
    write_data_gap_rehearsal(output_dir, rehearsal)
    return rehearsal


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Phase 4.6 data-gap resolution rehearsal pack.")
    parser.add_argument("--data-quality-audit", default=str(DEFAULT_DATA_QUALITY_AUDIT))
    parser.add_argument("--data-gap-resolution", default=str(DEFAULT_DATA_GAP_RESOLUTION))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--sample-size", type=int, default=2)
    args = parser.parse_args()
    rehearsal = run_data_gap_rehearsal(
        data_quality_audit=Path(args.data_quality_audit),
        data_gap_resolution=Path(args.data_gap_resolution) if args.data_gap_resolution else None,
        output_dir=Path(args.output_dir),
        sample_size=args.sample_size,
    )
    print(
        json.dumps(
            {
                "stage": rehearsal["stage"],
                "summary": rehearsal["summary"],
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


def _read_optional_json(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    target = Path(path)
    if not target.exists():
        return None
    return _read_json(target)


if __name__ == "__main__":
    main()
