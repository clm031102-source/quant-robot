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

from quant_robot.ops.capacity_safe_price_volume_preregistration import (  # noqa: E402
    build_capacity_safe_price_volume_preregistration,
    write_capacity_safe_price_volume_preregistration,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/capacity_safe_price_volume_preregistration")


def run_capacity_safe_price_volume_preregistration_cli(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    min_candidates: int = 8,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    result = build_capacity_safe_price_volume_preregistration(min_candidates=min_candidates)
    write_capacity_safe_price_volume_preregistration(output_dir, result)
    if not allow_not_ready and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Capacity-safe price-volume preregistration is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pre-register capacity-safe public price-volume, low-volatility, and reversal CN stock factor candidates."
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--min-candidates", type=int, default=8)
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    result = run_capacity_safe_price_volume_preregistration_cli(
        output_dir=Path(args.output_dir),
        min_candidates=args.min_candidates,
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
