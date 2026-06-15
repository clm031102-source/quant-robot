from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_robot.ops.residual_provider_review import (
    build_residual_provider_review_pack,
    write_residual_provider_review_pack,
)


DEFAULT_PROVIDER_REMEDIATION_REHEARSAL = Path("data/reports/provider_remediation_rehearsal/provider_remediation_rehearsal.json")
DEFAULT_PROVIDER_REMEDIATION_MATRIX = Path("data/reports/provider_remediation/provider_remediation_matrix.json")
DEFAULT_RESIDUAL_FOCUS = Path("data/reports/residual_blocker_focus/residual_blocker_focus_pack.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/residual_provider_review")


def run_residual_provider_review(
    provider_remediation_rehearsal: str | Path = DEFAULT_PROVIDER_REMEDIATION_REHEARSAL,
    provider_remediation_matrix: str | Path | None = DEFAULT_PROVIDER_REMEDIATION_MATRIX,
    residual_focus: str | Path | None = DEFAULT_RESIDUAL_FOCUS,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    rehearsal = _read_json(provider_remediation_rehearsal)
    matrix = _read_optional_json(provider_remediation_matrix)
    focus_pack = _read_optional_json(residual_focus)
    pack = build_residual_provider_review_pack(
        rehearsal,
        residual_focus_pack=focus_pack,
        provider_remediation_matrix=matrix,
    )
    write_residual_provider_review_pack(output_dir, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local Phase 4.15 residual provider review pack.")
    parser.add_argument("--provider-remediation-rehearsal", default=str(DEFAULT_PROVIDER_REMEDIATION_REHEARSAL))
    parser.add_argument("--provider-remediation-matrix", default=str(DEFAULT_PROVIDER_REMEDIATION_MATRIX))
    parser.add_argument("--residual-focus", default=str(DEFAULT_RESIDUAL_FOCUS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    pack = run_residual_provider_review(
        provider_remediation_rehearsal=Path(args.provider_remediation_rehearsal),
        provider_remediation_matrix=Path(args.provider_remediation_matrix) if args.provider_remediation_matrix else None,
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
