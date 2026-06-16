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

from quant_robot.ops.residual_data_gap_review import (
    build_residual_data_gap_review_pack,
    write_residual_data_gap_review_pack,
)


DEFAULT_DATA_GAP_REHEARSAL = Path("data/reports/data_gap_rehearsal/data_gap_rehearsal.json")
DEFAULT_DATA_GAP_LEDGER = Path("data/reports/data_gap_resolution/data_gap_resolution_ledger.json")
DEFAULT_RESIDUAL_FOCUS = Path("data/reports/residual_blocker_focus/residual_blocker_focus_pack.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/residual_data_gap_review")


def run_residual_data_gap_review(
    data_gap_rehearsal: str | Path = DEFAULT_DATA_GAP_REHEARSAL,
    data_gap_ledger: str | Path | None = DEFAULT_DATA_GAP_LEDGER,
    residual_focus: str | Path | None = DEFAULT_RESIDUAL_FOCUS,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    rehearsal = _read_json(data_gap_rehearsal)
    ledger = _read_optional_json(data_gap_ledger)
    focus_pack = _read_optional_json(residual_focus)
    pack = build_residual_data_gap_review_pack(rehearsal, residual_focus_pack=focus_pack, data_gap_ledger=ledger)
    write_residual_data_gap_review_pack(output_dir, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Phase 4.14 residual data-gap review pack.")
    parser.add_argument("--data-gap-rehearsal", default=str(DEFAULT_DATA_GAP_REHEARSAL))
    parser.add_argument("--data-gap-ledger", default=str(DEFAULT_DATA_GAP_LEDGER))
    parser.add_argument("--residual-focus", default=str(DEFAULT_RESIDUAL_FOCUS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    pack = run_residual_data_gap_review(
        data_gap_rehearsal=Path(args.data_gap_rehearsal),
        data_gap_ledger=Path(args.data_gap_ledger) if args.data_gap_ledger else None,
        residual_focus=Path(args.residual_focus) if args.residual_focus else None,
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
