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

from quant_robot.ops.financial_pit_post_announcement_gap_reversal_matrix_label_smoke import (  # noqa: E402
    build_financial_pit_post_announcement_gap_reversal_matrix_label_smoke,
    write_financial_pit_post_announcement_gap_reversal_matrix_label_smoke,
)


DEFAULT_FINANCIAL_ROOT = Path("data/processed/round202_financial_pit_signal_filtered_20260623")
DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_PREREGISTRATION_JSON = Path(
    "data/reports/financial_pit_post_announcement_gap_reversal_preregistration_round223_20260624/"
    "financial_pit_post_announcement_gap_reversal_preregistration.json"
)
DEFAULT_OUTPUT_DIR = Path("data/reports/financial_pit_post_announcement_gap_reversal_matrix_label_smoke_round223_20260624")


def run_financial_pit_post_announcement_gap_reversal_matrix_label_smoke_cli(
    *,
    financial_root: str | Path = DEFAULT_FINANCIAL_ROOT,
    bars_roots: list[str | Path] | tuple[str | Path, ...] = DEFAULT_BARS_ROOTS,
    preregistration_json: str | Path = DEFAULT_PREREGISTRATION_JSON,
    candidate_plan_gate_json: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    include_final_holdout: bool = False,
    horizons: list[int] | tuple[int, ...] = (5,),
    execution_lag: int = 1,
    min_label_coverage: float = 0.60,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    result = build_financial_pit_post_announcement_gap_reversal_matrix_label_smoke(
        financial_root=Path(financial_root),
        bars_roots=[Path(root) for root in bars_roots],
        preregistration_json=Path(preregistration_json),
        candidate_plan_gate_json=Path(candidate_plan_gate_json) if candidate_plan_gate_json else None,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        horizons=tuple(horizons),
        execution_lag=execution_lag,
        min_label_coverage=min_label_coverage,
    )
    write_financial_pit_post_announcement_gap_reversal_matrix_label_smoke(output_dir, result)
    if not allow_not_ready and not result["summary"].get("passes", False):
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Financial PIT post-announcement gap reversal matrix label smoke is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Round223 financial PIT post-announcement gap reversal factor-matrix and label-alignment smoke."
    )
    parser.add_argument("--financial-root", default=str(DEFAULT_FINANCIAL_ROOT))
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--preregistration-json", default=str(DEFAULT_PREREGISTRATION_JSON))
    parser.add_argument("--candidate-plan-gate-json")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default="2015-01-01")
    parser.add_argument("--analysis-end-date", default="2025-12-31")
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--horizon", action="append", type=int, default=[])
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--min-label-coverage", type=float, default=0.60)
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    result = run_financial_pit_post_announcement_gap_reversal_matrix_label_smoke_cli(
        financial_root=Path(args.financial_root),
        bars_roots=[Path(root) for root in (args.bars_root or DEFAULT_BARS_ROOTS)],
        preregistration_json=Path(args.preregistration_json),
        candidate_plan_gate_json=Path(args.candidate_plan_gate_json) if args.candidate_plan_gate_json else None,
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        horizons=args.horizon or [5],
        execution_lag=args.execution_lag,
        min_label_coverage=args.min_label_coverage,
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
