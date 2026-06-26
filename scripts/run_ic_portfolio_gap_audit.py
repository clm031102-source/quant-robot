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

from quant_robot.ops.ic_portfolio_gap_audit import (  # noqa: E402
    build_ic_portfolio_gap_audit,
    load_leaderboard_rows,
    write_ic_portfolio_gap_audit,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/ic_portfolio_gap_audit")


def run_ic_portfolio_gap_audit(
    *,
    leaderboard: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    leaderboard_path = Path(leaderboard)
    rows = load_leaderboard_rows(leaderboard_path)
    audit = build_ic_portfolio_gap_audit(rows, source_report=str(leaderboard_path))
    write_ic_portfolio_gap_audit(output_dir, audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit where strong IC signals fail to become long-only portfolio returns.")
    parser.add_argument("--leaderboard", required=True, help="Experiment leaderboard CSV/JSON path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    audit = run_ic_portfolio_gap_audit(
        leaderboard=Path(args.leaderboard),
        output_dir=Path(args.output_dir),
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
