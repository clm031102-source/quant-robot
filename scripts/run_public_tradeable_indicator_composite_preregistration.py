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

from quant_robot.ops.factor_mining_candidate_plan_gate import (  # noqa: E402
    build_factor_mining_candidate_plan_gate,
    write_factor_mining_candidate_plan_gate,
)
from quant_robot.ops.public_tradeable_indicator_composite_preregistration import (  # noqa: E402
    build_public_tradeable_indicator_composite_preregistration,
    write_public_tradeable_indicator_composite_preregistration,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/round264_public_tradeable_indicator_composite_preregistration_20260626")


def run_public_tradeable_indicator_composite_preregistration_cli(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    min_candidates: int = 8,
    min_families: int = 4,
    allow_blocked: bool = False,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    result = build_public_tradeable_indicator_composite_preregistration(
        min_candidates=min_candidates,
        min_families=min_families,
    )
    write_public_tradeable_indicator_composite_preregistration(output_path, result)
    gate = build_factor_mining_candidate_plan_gate(result, gate_stage="discovery")
    write_factor_mining_candidate_plan_gate(output_path, gate)
    if not allow_blocked and not gate["decision"]["candidate_plan_gate_cleared"]:
        blockers = ", ".join(gate["decision"].get("blockers", []) or [])
        raise RuntimeError(f"Public tradeable indicator composite candidate plan gate is blocked: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pre-register Round264 CN stock public tradeable indicator composite candidates."
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-candidates", type=int, default=8)
    parser.add_argument("--min-families", type=int, default=4)
    parser.add_argument("--allow-blocked", action="store_true")
    args = parser.parse_args()
    result = run_public_tradeable_indicator_composite_preregistration_cli(
        output_dir=args.output_dir,
        min_candidates=args.min_candidates,
        min_families=args.min_families,
        allow_blocked=args.allow_blocked,
    )
    print(
        json.dumps(
            {
                "stage": result["stage"],
                "summary": result["summary"],
                "promotion_policy": result["promotion_policy"],
                "live_boundary_allowed": result["live_boundary_allowed"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
