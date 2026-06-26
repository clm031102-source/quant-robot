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

from quant_robot.ops.profitability_event_revision_matrix_label_smoke import (  # noqa: E402
    build_profitability_event_revision_matrix_label_smoke,
    write_profitability_event_revision_matrix_label_smoke,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/profitability_event_revision_matrix_label_smoke_round152_20260623")


def run_profitability_event_revision_matrix_label_smoke_cli(
    *,
    financial_root: str | Path,
    bars_roots: list[str | Path],
    preregistration_json: str | Path,
    candidate_plan_gate_json: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    horizons: list[int] | tuple[int, ...] = (5, 20),
    execution_lag: int = 1,
    min_label_coverage: float = 0.6,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    result = build_profitability_event_revision_matrix_label_smoke(
        financial_root=Path(financial_root),
        bars_roots=[Path(root) for root in bars_roots],
        preregistration_json=Path(preregistration_json),
        candidate_plan_gate_json=Path(candidate_plan_gate_json) if candidate_plan_gate_json else None,
        horizons=tuple(horizons),
        execution_lag=execution_lag,
        min_label_coverage=min_label_coverage,
    )
    write_profitability_event_revision_matrix_label_smoke(output_dir, result)
    if not allow_not_ready and not result["summary"]["passes"]:
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"PIT profitability event-revision matrix label smoke is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Round152 PIT profitability event/revision factor-matrix and label-alignment smoke."
    )
    parser.add_argument("--financial-root", required=True)
    parser.add_argument("--bars-root", action="append", required=True)
    parser.add_argument("--preregistration-json", required=True)
    parser.add_argument("--candidate-plan-gate-json")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--horizon", action="append", type=int, default=[])
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--min-label-coverage", type=float, default=0.6)
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    result = run_profitability_event_revision_matrix_label_smoke_cli(
        financial_root=Path(args.financial_root),
        bars_roots=[Path(root) for root in args.bars_root],
        preregistration_json=Path(args.preregistration_json),
        candidate_plan_gate_json=Path(args.candidate_plan_gate_json) if args.candidate_plan_gate_json else None,
        output_dir=Path(args.output_dir),
        horizons=args.horizon or [5, 20],
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
