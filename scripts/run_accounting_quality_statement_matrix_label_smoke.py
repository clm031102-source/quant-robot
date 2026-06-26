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

from quant_robot.ops.accounting_quality_statement_matrix_label_smoke import (  # noqa: E402
    build_accounting_quality_statement_matrix_label_smoke,
    write_accounting_quality_statement_matrix_label_smoke,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/accounting_quality_statement_matrix_label_smoke")


def run_accounting_quality_statement_matrix_label_smoke_cli(
    *,
    statement_roots: list[str | Path] | tuple[str | Path, ...],
    bars_roots: list[str | Path] | tuple[str | Path, ...],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    include_final_holdout: bool = False,
    horizons: list[int] | tuple[int, ...] = (5, 20),
    execution_lag: int = 1,
    min_label_coverage: float = 0.60,
    deduplicate: bool = True,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    result = build_accounting_quality_statement_matrix_label_smoke(
        statement_roots=[Path(root) for root in statement_roots],
        bars_roots=[Path(root) for root in bars_roots],
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        horizons=tuple(horizons),
        execution_lag=int(execution_lag),
        min_label_coverage=float(min_label_coverage),
        deduplicate=deduplicate,
    )
    write_accounting_quality_statement_matrix_label_smoke(output_dir, result)
    if not allow_not_ready and not result["summary"].get("passes", False):
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"accounting quality statement matrix label smoke is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run accounting-quality statement factor-matrix and label-alignment smoke.")
    parser.add_argument("--statement-root", action="append", required=True, help="Processed statement root. Can be repeated.")
    parser.add_argument("--bars-root", action="append", required=True, help="Processed CN stock bars root. Can be repeated.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default="2015-01-01")
    parser.add_argument("--analysis-end-date", default="2025-12-31")
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--horizon", action="append", type=int, default=[])
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--min-label-coverage", type=float, default=0.60)
    parser.add_argument("--no-deduplicate", action="store_true")
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    result = run_accounting_quality_statement_matrix_label_smoke_cli(
        statement_roots=[Path(root) for root in args.statement_root],
        bars_roots=[Path(root) for root in args.bars_root],
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        horizons=args.horizon or [5, 20],
        execution_lag=args.execution_lag,
        min_label_coverage=args.min_label_coverage,
        deduplicate=not args.no_deduplicate,
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
