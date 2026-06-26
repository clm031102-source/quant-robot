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

from quant_robot.ops.profitability_quality_controlled_ic_screen import (  # noqa: E402
    build_profitability_quality_controlled_ic_screen,
    write_profitability_quality_controlled_ic_screen,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/profitability_quality_controlled_ic_screen")


def run_profitability_quality_controlled_ic_screen_cli(
    *,
    financial_root: str | Path,
    bars_roots: list[str | Path],
    preregistration_json: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    horizons: list[int] | tuple[int, ...] = (5, 20),
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 8,
    alpha: float = 0.05,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    result = build_profitability_quality_controlled_ic_screen(
        financial_root=Path(financial_root),
        bars_roots=[Path(root) for root in bars_roots],
        preregistration_json=Path(preregistration_json),
        horizons=tuple(horizons),
        execution_lag=execution_lag,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        alpha=alpha,
    )
    write_profitability_quality_controlled_ic_screen(output_dir, result)
    if not allow_not_ready and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Profitability quality controlled IC screen is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a controlled IC screen for PIT profitability-quality factors.")
    parser.add_argument("--financial-root", required=True)
    parser.add_argument("--bars-root", action="append", required=True)
    parser.add_argument("--preregistration-json", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--horizon", action="append", type=int, default=[])
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=8)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    result = run_profitability_quality_controlled_ic_screen_cli(
        financial_root=Path(args.financial_root),
        bars_roots=[Path(root) for root in args.bars_root],
        preregistration_json=Path(args.preregistration_json),
        output_dir=Path(args.output_dir),
        horizons=args.horizon or [5, 20],
        execution_lag=args.execution_lag,
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        alpha=args.alpha,
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
