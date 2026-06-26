from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.turnover_repair_dedup_sensitivity import (  # noqa: E402
    DEFAULT_CAPITAL_GRID,
    load_turnover_repair_prescreen_results,
    summarize_turnover_repair_dedup_sensitivity,
    write_turnover_repair_dedup_sensitivity,
)


DEFAULT_ROUND124_RESULTS = Path(
    "data/reports/turnover_continuous_capacity_repair_prescreen_round124_20260622/"
    "turnover_continuous_capacity_repair_prescreen_results.csv"
)
DEFAULT_OUTPUT_DIR = Path("data/reports/turnover_repair_dedup_sensitivity_round125_20260622")


def run_turnover_repair_dedup_sensitivity_cli(
    *,
    round124_results: str | Path = DEFAULT_ROUND124_RESULTS,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    capital_grid: Iterable[int | float] = DEFAULT_CAPITAL_GRID,
) -> dict[str, Any]:
    frame = load_turnover_repair_prescreen_results(round124_results)
    result = summarize_turnover_repair_dedup_sensitivity(frame, capital_grid=capital_grid)
    write_turnover_repair_dedup_sensitivity(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Round125 turnover-repair dedup and small-capital sensitivity audit."
    )
    parser.add_argument("--round124-results", default=str(DEFAULT_ROUND124_RESULTS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--capital-grid", default=",".join(str(item) for item in DEFAULT_CAPITAL_GRID))
    args = parser.parse_args()
    result = run_turnover_repair_dedup_sensitivity_cli(
        round124_results=Path(args.round124_results),
        output_dir=Path(args.output_dir),
        capital_grid=_parse_capital_grid(args.capital_grid),
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "champion": result.get("champion", {}),
                "portfolio_conversion_policy": result.get("portfolio_conversion_policy", {}),
                "promotion_policy": result.get("promotion_policy", {}),
                "next_direction": result.get("next_direction"),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _parse_capital_grid(value: str) -> tuple[int, ...]:
    capitals = []
    for item in value.split(","):
        text = item.strip()
        if text:
            capitals.append(int(float(text)))
    return tuple(capitals)


if __name__ == "__main__":
    main()
