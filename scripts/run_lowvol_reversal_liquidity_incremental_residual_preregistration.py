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

from quant_robot.ops.lowvol_reversal_liquidity_incremental_residual_preregistration import (  # noqa: E402
    build_lowvol_reversal_liquidity_incremental_residual_preregistration,
    write_lowvol_reversal_liquidity_incremental_residual_preregistration,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/lowvol_reversal_liquidity_incremental_residual_preregistration")


def run_lowvol_reversal_liquidity_incremental_residual_preregistration_cli(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    min_candidates: int = 8,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    result = build_lowvol_reversal_liquidity_incremental_residual_preregistration(min_candidates=min_candidates)
    write_lowvol_reversal_liquidity_incremental_residual_preregistration(output_dir, result)
    if not allow_not_ready and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Low-vol incremental residual preregistration is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pre-register low-vol/reversal/liquidity incremental residual CN stock candidates."
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-candidates", type=int, default=8)
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    result = run_lowvol_reversal_liquidity_incremental_residual_preregistration_cli(
        output_dir=Path(args.output_dir),
        min_candidates=args.min_candidates,
        allow_not_ready=args.allow_not_ready,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "incremental_residual_context": result.get("incremental_residual_context", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
