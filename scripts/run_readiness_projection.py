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

from quant_robot.ops.readiness_projection import build_readiness_projection_pack, write_readiness_projection_pack


DEFAULT_READINESS_BOARD = Path("data/reports/pre_api_readiness_board/pre_api_readiness_board.json")
DEFAULT_DATA_GAP_REHEARSAL = Path("data/reports/data_gap_rehearsal/data_gap_rehearsal.json")
DEFAULT_PROVIDER_REMEDIATION_REHEARSAL = Path("data/reports/provider_remediation_rehearsal/provider_remediation_rehearsal.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/readiness_projection")


def run_readiness_projection(
    readiness_board: str | Path = DEFAULT_READINESS_BOARD,
    data_gap_rehearsal: str | Path | None = DEFAULT_DATA_GAP_REHEARSAL,
    provider_remediation_rehearsal: str | Path | None = DEFAULT_PROVIDER_REMEDIATION_REHEARSAL,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    board = _read_json(readiness_board)
    pack = build_readiness_projection_pack(
        board,
        data_gap_rehearsal=_read_optional_json(data_gap_rehearsal),
        provider_remediation_rehearsal=_read_optional_json(provider_remediation_rehearsal),
    )
    write_readiness_projection_pack(output_dir, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Phase 4.12 pre-API readiness projection pack.")
    parser.add_argument("--readiness-board", default=str(DEFAULT_READINESS_BOARD))
    parser.add_argument("--data-gap-rehearsal", default=str(DEFAULT_DATA_GAP_REHEARSAL))
    parser.add_argument("--provider-remediation-rehearsal", default=str(DEFAULT_PROVIDER_REMEDIATION_REHEARSAL))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    pack = run_readiness_projection(
        readiness_board=Path(args.readiness_board),
        data_gap_rehearsal=Path(args.data_gap_rehearsal) if args.data_gap_rehearsal else None,
        provider_remediation_rehearsal=Path(args.provider_remediation_rehearsal) if args.provider_remediation_rehearsal else None,
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
