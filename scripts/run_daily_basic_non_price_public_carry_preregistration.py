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

from quant_robot.ops.daily_basic_non_price_public_carry_preregistration import (  # noqa: E402
    build_daily_basic_non_price_public_carry_preregistration,
    write_daily_basic_non_price_public_carry_preregistration,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/daily_basic_non_price_public_carry_preregistration_round131_20260622")


def run_daily_basic_non_price_public_carry_preregistration_cli(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    min_candidates: int = 8,
    min_families: int = 4,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    result = build_daily_basic_non_price_public_carry_preregistration(
        min_candidates=min_candidates,
        min_families=min_families,
    )
    write_daily_basic_non_price_public_carry_preregistration(output_dir, result)
    if not allow_not_ready and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Daily-basic non-price public-carry preregistration is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pre-register CN stock daily-basic-only public carry/value candidates after PV residual failure."
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-candidates", type=int, default=8)
    parser.add_argument("--min-families", type=int, default=4)
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    result = run_daily_basic_non_price_public_carry_preregistration_cli(
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
                "data_policy": result["data_policy"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
