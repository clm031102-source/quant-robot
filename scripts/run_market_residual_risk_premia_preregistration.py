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

from quant_robot.ops.market_residual_risk_premia_preregistration import (  # noqa: E402
    build_market_residual_risk_premia_preregistration,
    write_market_residual_risk_premia_preregistration,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/market_residual_risk_premia_preregistration")


def run_market_residual_risk_premia_preregistration_cli(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    min_candidates: int = 8,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    result = build_market_residual_risk_premia_preregistration(min_candidates=min_candidates)
    write_market_residual_risk_premia_preregistration(output_dir, result)
    if not allow_not_ready and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Market residual risk premia preregistration is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pre-register CN stock market-residual risk premia factor candidates."
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-candidates", type=int, default=8)
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    result = run_market_residual_risk_premia_preregistration_cli(
        output_dir=Path(args.output_dir),
        min_candidates=args.min_candidates,
        allow_not_ready=args.allow_not_ready,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "factor_model_context": result.get("factor_model_context", {}),
                "family_rotation_context": result.get("family_rotation_context", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
