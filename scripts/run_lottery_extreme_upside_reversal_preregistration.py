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

from quant_robot.ops.lottery_extreme_upside_reversal_preregistration import (  # noqa: E402
    build_lottery_extreme_upside_reversal_preregistration,
    write_lottery_extreme_upside_reversal_preregistration,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/lottery_extreme_upside_reversal_preregistration_round149_20260622")


def run_lottery_extreme_upside_reversal_preregistration_cli(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    min_candidates: int = 6,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    result = build_lottery_extreme_upside_reversal_preregistration(min_candidates=min_candidates)
    write_lottery_extreme_upside_reversal_preregistration(output_dir, result)
    if not allow_not_ready and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Lottery extreme-upside preregistration is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pre-register Round149 CN stock lottery/MAX-effect extreme-upside reversal candidates."
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-candidates", type=int, default=6)
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    result = run_lottery_extreme_upside_reversal_preregistration_cli(
        output_dir=Path(args.output_dir),
        min_candidates=args.min_candidates,
        allow_not_ready=args.allow_not_ready,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "source_context": result.get("source_context", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
