from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.lpr_macro_regime_state_prescreen import run_lpr_macro_regime_state_prescreen


DEFAULT_PROCESSED_ROOT = Path("data/processed/round695_external_feeds_lpr_repaired_20260709")
DEFAULT_READINESS_GATE = Path(
    "data/reports/round730_lpr_macro_regime_factor_batch_readiness_after_state_check_20260709/"
    "factor_batch_readiness_gate.json"
)
DEFAULT_CANDIDATE_PLAN = Path("configs/factor_mining_candidate_plan_round730_lpr_macro_regime_control_20260709.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/round731_lpr_macro_regime_state_prescreen_20260709")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run LPR macro regime state prescreen.")
    parser.add_argument("--processed-root", default=str(DEFAULT_PROCESSED_ROOT))
    parser.add_argument("--readiness-gate", default=str(DEFAULT_READINESS_GATE))
    parser.add_argument("--candidate-plan", default=str(DEFAULT_CANDIDATE_PLAN))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--market", default="CN")
    parser.add_argument("--analysis-start-date", default="2024-07-01")
    parser.add_argument("--analysis-end-date", default="2025-12-31")
    parser.add_argument("--lookback-days", type=int, default=60)
    parser.add_argument("--min-abs-gap-change", type=float, default=0.01)
    parser.add_argument("--min-state-dates", type=int, default=5)
    parser.add_argument("--min-nonzero-gap-changes", type=int, default=20)
    parser.add_argument("--include-final-holdout", action="store_true")
    args = parser.parse_args(argv)
    result = run_lpr_macro_regime_state_prescreen(
        processed_root=Path(args.processed_root),
        readiness_gate_path=Path(args.readiness_gate),
        candidate_plan_path=Path(args.candidate_plan),
        output_dir=Path(args.output_dir),
        market=args.market,
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        lookback_days=args.lookback_days,
        min_abs_gap_change=args.min_abs_gap_change,
        min_state_dates=args.min_state_dates,
        min_nonzero_gap_changes=args.min_nonzero_gap_changes,
        include_final_holdout=args.include_final_holdout,
    )
    print(
        json.dumps(
                {
                    "summary": result["summary"],
                    "data_window": result.get("data_window", {}),
                    "decision": result.get("decision", {}),
                    "output_dir": str(Path(args.output_dir)),
                },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
