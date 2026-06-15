from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_robot.ops.blocker_worklist import build_blocker_worklist, write_blocker_worklist


DEFAULT_READINESS_BOARD = Path("data/reports/pre_api_readiness_board/pre_api_readiness_board.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/blocker_worklist")


def run_blocker_worklist(
    readiness_board: str | Path = DEFAULT_READINESS_BOARD,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    board = _read_json(readiness_board)
    worklist = build_blocker_worklist(board)
    write_blocker_worklist(output_dir, worklist)
    return worklist


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Phase 4.1 blocker resolution worklist.")
    parser.add_argument("--readiness-board", default=str(DEFAULT_READINESS_BOARD))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    worklist = run_blocker_worklist(
        readiness_board=Path(args.readiness_board),
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "stage": worklist["stage"],
                "summary": worklist["summary"],
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
