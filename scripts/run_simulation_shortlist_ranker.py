from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.simulation_shortlist_ranker import (  # noqa: E402
    build_simulation_shortlist_ranking,
    write_simulation_shortlist_ranking,
)


DEFAULT_CONFIG = Path("configs/cn_stock_profit_sprint_simulation_shortlist_20260627.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/simulation_shortlist_ranking")


def run_simulation_shortlist_ranker(
    config: str | Path = DEFAULT_CONFIG,
    repo_root: str | Path = ".",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    max_user_drawdown: float = -0.30,
    min_oos_strict_pass_rate: float = 0.75,
    duplicate_correlation: float = 0.98,
) -> dict:
    config_path = Path(config)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    ranking = build_simulation_shortlist_ranking(
        payload,
        repo_root=Path(repo_root),
        periods_per_year=periods_per_year,
        holding_period=holding_period,
        max_user_drawdown=max_user_drawdown,
        min_oos_strict_pass_rate=min_oos_strict_pass_rate,
        duplicate_correlation=duplicate_correlation,
    )
    write_simulation_shortlist_ranking(Path(output_dir), ranking)
    return ranking


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank simulation-shortlist candidates under aggressive paper limits.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--periods-per-year", type=float, default=252.0 / 5.0)
    parser.add_argument("--holding-period", type=int, default=20)
    parser.add_argument("--max-user-drawdown", type=float, default=-0.30)
    parser.add_argument("--min-oos-strict-pass-rate", type=float, default=0.75)
    parser.add_argument("--duplicate-correlation", type=float, default=0.98)
    args = parser.parse_args()
    ranking = run_simulation_shortlist_ranker(
        config=Path(args.config),
        repo_root=Path(args.repo_root),
        output_dir=Path(args.output_dir),
        periods_per_year=args.periods_per_year,
        holding_period=args.holding_period,
        max_user_drawdown=args.max_user_drawdown,
        min_oos_strict_pass_rate=args.min_oos_strict_pass_rate,
        duplicate_correlation=args.duplicate_correlation,
    )
    print(
        json.dumps(
            {
                "stage": ranking["stage"],
                "summary": ranking["summary"],
                "top": ranking["rows"][:10],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
