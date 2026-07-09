from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.lpr_macro_regime_pairwise_residual_ic_prescreen import (
    run_lpr_macro_regime_pairwise_residual_ic_prescreen,
)


DEFAULT_PROCESSED_ROOT = Path("data/processed/round695_external_feeds_lpr_repaired_20260709")
DEFAULT_STATE_PRESCREEN = Path(
    "data/reports/round731_lpr_macro_regime_state_prescreen_20260709/lpr_macro_regime_state_prescreen.json"
)
DEFAULT_OUTPUT_DIR = Path("data/reports/round732_lpr_macro_regime_pairwise_residual_ic_prescreen_20260709")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run LPR macro regime pairwise residual IC prescreen.")
    parser.add_argument("--processed-root", default=str(DEFAULT_PROCESSED_ROOT))
    parser.add_argument("--state-prescreen", default=str(DEFAULT_STATE_PRESCREEN))
    parser.add_argument("--residual-ic", action="append", required=True, dest="residual_ic_paths")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--market", default="CN")
    parser.add_argument("--analysis-start-date", default="2024-07-01")
    parser.add_argument("--analysis-end-date", default="2025-12-31")
    parser.add_argument("--lookback-days", type=int, default=60)
    parser.add_argument("--min-abs-gap-change", type=float, default=0.01)
    parser.add_argument("--min-state-ic-observations", type=int, default=20)
    parser.add_argument("--min-mean-ic", type=float, default=0.02)
    parser.add_argument("--min-icir", type=float, default=0.20)
    parser.add_argument("--min-positive-ic-rate", type=float, default=0.55)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--include-final-holdout", action="store_true")
    args = parser.parse_args(argv)
    result = run_lpr_macro_regime_pairwise_residual_ic_prescreen(
        processed_root=Path(args.processed_root),
        state_prescreen_path=Path(args.state_prescreen),
        residual_ic_paths=[Path(path) for path in args.residual_ic_paths],
        output_dir=Path(args.output_dir),
        market=args.market,
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        lookback_days=args.lookback_days,
        min_abs_gap_change=args.min_abs_gap_change,
        min_state_ic_observations=args.min_state_ic_observations,
        min_mean_ic=args.min_mean_ic,
        min_icir=args.min_icir,
        min_positive_ic_rate=args.min_positive_ic_rate,
        alpha=args.alpha,
        include_final_holdout=args.include_final_holdout,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "decision": result.get("decision", {}),
                "pairing_audit": result.get("pairing_audit", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
