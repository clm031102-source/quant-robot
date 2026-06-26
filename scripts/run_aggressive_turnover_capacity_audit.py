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

from quant_robot.ops.aggressive_turnover_capacity_audit import (  # noqa: E402
    build_aggressive_turnover_capacity_audit,
    write_aggressive_turnover_capacity_audit,
)
from quant_robot.ops.ic_portfolio_gap_audit import load_leaderboard_rows  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("data/reports/aggressive_turnover_capacity_audit")


def run_aggressive_turnover_capacity_audit(
    *,
    leaderboard: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    target_factors: list[str] | None = None,
    user_max_drawdown_tolerance: float = 0.30,
) -> dict[str, Any]:
    leaderboard_path = Path(leaderboard)
    rows = load_leaderboard_rows(leaderboard_path)
    audit = build_aggressive_turnover_capacity_audit(
        rows,
        source_report=str(leaderboard_path),
        target_factors=target_factors,
        user_max_drawdown_tolerance=user_max_drawdown_tolerance,
    )
    write_aggressive_turnover_capacity_audit(output_dir, audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit high-return turnover factors under aggressive drawdown tolerance but strict capacity gates."
    )
    parser.add_argument("--leaderboard", required=True, help="Experiment leaderboard CSV/JSON path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--target-factor",
        action="append",
        default=None,
        help="Raw factor to pair with '<factor>_large_mv'. Repeat for multiple factors.",
    )
    parser.add_argument("--user-max-drawdown-tolerance", type=float, default=0.30)
    args = parser.parse_args()
    audit = run_aggressive_turnover_capacity_audit(
        leaderboard=Path(args.leaderboard),
        output_dir=Path(args.output_dir),
        target_factors=args.target_factor,
        user_max_drawdown_tolerance=args.user_max_drawdown_tolerance,
    )
    print(
        json.dumps(
            {
                "summary": audit["summary"],
                "recommended_next_actions": audit["recommended_next_actions"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
