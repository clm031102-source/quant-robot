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

from quant_robot.ops.public_reference_multi_family_preregistration import (  # noqa: E402
    build_public_reference_multi_family_preregistration,
    write_public_reference_multi_family_preregistration,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/public_reference_multi_family_preregistration_round127_20260622")


def run_public_reference_multi_family_preregistration_cli(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    min_candidates: int = 18,
    min_families: int = 6,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    result = build_public_reference_multi_family_preregistration(
        min_candidates=min_candidates,
        min_families=min_families,
    )
    write_public_reference_multi_family_preregistration(output_dir, result)
    if not allow_not_ready and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Public-reference multi-family preregistration is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pre-register CN stock public-reference multi-family candidates after turnover hibernation."
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-candidates", type=int, default=18)
    parser.add_argument("--min-families", type=int, default=6)
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    result = run_public_reference_multi_family_preregistration_cli(
        output_dir=Path(args.output_dir),
        min_candidates=args.min_candidates,
        min_families=args.min_families,
        allow_not_ready=args.allow_not_ready,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "family_rotation_context": result["family_rotation_context"],
                "public_reference_review": result["public_reference_review"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
