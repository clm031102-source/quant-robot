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

from quant_robot.ops.financial_reporting_timeliness_source_audit import (  # noqa: E402
    build_financial_reporting_timeliness_source_audit,
    write_financial_reporting_timeliness_source_audit,
)


DEFAULT_FINANCIAL_ROOTS = (
    Path("data/processed/round202_financial_pit_signal_filtered_20260623"),
    Path("data/processed/round216_financial_pit_signal_filtered_stratified_shard1_full100_20260624"),
    Path("data/processed/round236_financial_statement_pilot_first2_fullcycle_20260625"),
)
DEFAULT_OUTPUT_DIR = Path("data/reports/round270_financial_reporting_timeliness_source_audit_20260626")


def run_financial_reporting_timeliness_source_audit_cli(
    *,
    financial_roots: Iterable[str | Path] = DEFAULT_FINANCIAL_ROOTS,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    min_unique_symbols: int = 1000,
    min_end_years: int = 8,
) -> dict[str, Any]:
    roots = _expand_financial_roots(tuple(Path(path) for path in financial_roots))
    result = build_financial_reporting_timeliness_source_audit(
        financial_roots=roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        min_unique_symbols=min_unique_symbols,
        min_end_years=min_end_years,
    )
    write_financial_reporting_timeliness_source_audit(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Round270 financial reporting timeliness source audit.")
    parser.add_argument("--financial-root", action="append", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default="2015-01-01")
    parser.add_argument("--analysis-end-date", default="2025-12-31")
    parser.add_argument("--min-unique-symbols", type=int, default=1000)
    parser.add_argument("--min-end-years", type=int, default=8)
    args = parser.parse_args()

    result = run_financial_reporting_timeliness_source_audit_cli(
        financial_roots=tuple(Path(path) for path in (args.financial_root or DEFAULT_FINANCIAL_ROOTS)),
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        min_unique_symbols=args.min_unique_symbols,
        min_end_years=args.min_end_years,
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "summary": result["summary"],
                "gate": result["gate"],
                "candidate_plan_allowed": result["candidate_plan_allowed"],
                "next_direction": result["next_direction"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _expand_financial_roots(financial_roots: Iterable[Path]) -> tuple[Path, ...]:
    expanded: list[Path] = []
    for root in financial_roots:
        if root.is_dir() and root.name == "processed":
            children = [
                child
                for child in sorted(root.iterdir())
                if child.is_dir() and ("financial_statement" in child.name or "financial_pit_signal" in child.name)
            ]
            if children:
                expanded.extend(children)
                continue
        expanded.append(root)
    return tuple(expanded)


if __name__ == "__main__":
    main()
