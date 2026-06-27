from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.simulation_shortlist_replay import (  # noqa: E402
    build_simulation_shortlist_replay,
    write_simulation_shortlist_replay,
)


DEFAULT_CONFIG = Path("configs/cn_stock_profit_sprint_simulation_shortlist_20260627.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/simulation_shortlist_replay")


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay simulation shortlist event streams and compare config evidence.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--periods-per-year", type=float, default=252.0 / 5.0)
    parser.add_argument("--holding-period", type=int, default=20)
    parser.add_argument("--metric-tolerance", type=float, default=0.005)
    args = parser.parse_args()

    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    replay = build_simulation_shortlist_replay(
        config,
        repo_root=Path(args.repo_root),
        periods_per_year=args.periods_per_year,
        holding_period=args.holding_period,
        metric_tolerance=args.metric_tolerance,
    )
    write_simulation_shortlist_replay(Path(args.output_dir), replay)
    print(
        json.dumps(
            {
                "status": replay["status"],
                "blockers": replay["blockers"],
                "summary": replay["summary"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
