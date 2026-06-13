from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_robot.ops.residual_blocker_focus import (
    build_residual_blocker_focus_pack,
    write_residual_blocker_focus_pack,
)


DEFAULT_READINESS_PROJECTION = Path("data/reports/readiness_projection/readiness_projection_pack.json")
DEFAULT_BLOCKER_WORKLIST = Path("data/reports/blocker_worklist/blocker_resolution_worklist.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/residual_blocker_focus")


def run_residual_blocker_focus(
    readiness_projection: str | Path = DEFAULT_READINESS_PROJECTION,
    blocker_worklist: str | Path = DEFAULT_BLOCKER_WORKLIST,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    projection = _read_json(readiness_projection)
    worklist = _read_json(blocker_worklist)
    pack = build_residual_blocker_focus_pack(projection, worklist)
    write_residual_blocker_focus_pack(output_dir, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Phase 4.13 residual blocker focus pack.")
    parser.add_argument("--readiness-projection", default=str(DEFAULT_READINESS_PROJECTION))
    parser.add_argument("--blocker-worklist", default=str(DEFAULT_BLOCKER_WORKLIST))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    pack = run_residual_blocker_focus(
        readiness_projection=Path(args.readiness_projection),
        blocker_worklist=Path(args.blocker_worklist),
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


if __name__ == "__main__":
    main()
