from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.simulation_shortlist_blend_audit import (  # noqa: E402
    build_simulation_shortlist_blend_audit,
    write_simulation_shortlist_blend_audit,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/simulation_shortlist_blend_audit")


def parse_return_source(value: str) -> tuple[str, dict[str, str]]:
    name, sep, rest = str(value).partition("=")
    if not sep or not name or not rest:
        raise argparse.ArgumentTypeError("return source must be name=path or name=path:return_column")
    path, column_sep, column = rest.partition(":")
    spec = {"path": path}
    if column_sep and column:
        spec["return_column"] = column
    return name, spec


def run_simulation_shortlist_blend_audit(
    *,
    return_sources: list[str],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    return_column: str | None = None,
    date_column: str = "date",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    weight_step: float = 0.25,
    max_components: int = 3,
    max_drawdown_floor: float = -0.30,
    duplicate_correlation: float = 0.98,
) -> dict:
    sources = dict(parse_return_source(value) for value in return_sources)
    audit = build_simulation_shortlist_blend_audit(
        return_sources=sources,
        return_column=return_column,
        date_column=date_column,
        periods_per_year=periods_per_year,
        holding_period=holding_period,
        weight_step=weight_step,
        max_components=max_components,
        max_drawdown_floor=max_drawdown_floor,
        duplicate_correlation=duplicate_correlation,
    )
    write_simulation_shortlist_blend_audit(output_dir, audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a low-dimensional blend audit for simulation-shortlist returns.")
    parser.add_argument("--return-source", action="append", required=True, help="Candidate spec as name=path[:return_column].")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--return-column", default=None)
    parser.add_argument("--date-column", default="date")
    parser.add_argument("--periods-per-year", type=float, default=252.0 / 5.0)
    parser.add_argument("--holding-period", type=int, default=20)
    parser.add_argument("--weight-step", type=float, default=0.25)
    parser.add_argument("--max-components", type=int, default=3)
    parser.add_argument("--max-drawdown-floor", type=float, default=-0.30)
    parser.add_argument("--duplicate-correlation", type=float, default=0.98)
    args = parser.parse_args()
    audit = run_simulation_shortlist_blend_audit(
        return_sources=args.return_source,
        output_dir=Path(args.output_dir),
        return_column=args.return_column,
        date_column=args.date_column,
        periods_per_year=args.periods_per_year,
        holding_period=args.holding_period,
        weight_step=args.weight_step,
        max_components=args.max_components,
        max_drawdown_floor=args.max_drawdown_floor,
        duplicate_correlation=args.duplicate_correlation,
    )
    print(
        json.dumps(
            {
                "stage": audit["stage"],
                "summary": audit["summary"],
                "top": audit["rows"][:10],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
