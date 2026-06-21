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

from quant_robot.ops.profitability_quality_preregistration import (  # noqa: E402
    build_profitability_quality_preregistration,
    write_profitability_quality_preregistration,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/profitability_quality_preregistration")


def run_profitability_quality_preregistration_cli(
    *,
    input_root: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    min_assets: int = 50,
    min_passed_candidates: int = 8,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    result = build_profitability_quality_preregistration(
        input_root=Path(input_root),
        min_assets=min_assets,
        min_passed_candidates=min_passed_candidates,
    )
    write_profitability_quality_preregistration(output_dir, result)
    if not allow_not_ready and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Profitability quality preregistration is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pre-register profitability-quality factors and audit field coverage from PIT fina_indicator inputs."
    )
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-assets", type=int, default=50)
    parser.add_argument("--min-passed-candidates", type=int, default=8)
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    result = run_profitability_quality_preregistration_cli(
        input_root=Path(args.input_root),
        output_dir=Path(args.output_dir),
        min_assets=args.min_assets,
        min_passed_candidates=args.min_passed_candidates,
        allow_not_ready=args.allow_not_ready,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
