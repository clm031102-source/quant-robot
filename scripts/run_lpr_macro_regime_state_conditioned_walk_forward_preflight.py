from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.lpr_macro_regime_state_conditioned_walk_forward_preflight import (  # noqa: E402
    DEFAULT_CANDIDATE_HIGH_CORR_THRESHOLD,
    DEFAULT_MIN_CORR_CROSS_SECTION,
    DEFAULT_MIN_PAIR_OBSERVATIONS,
    DEFAULT_MIN_WALK_FORWARD_FOLDS,
    DEFAULT_STEP_STATE_DATES,
    DEFAULT_TEST_STATE_DATES,
    DEFAULT_TRAIN_STATE_DATES,
    run_lpr_macro_regime_state_conditioned_walk_forward_preflight,
)


DEFAULT_PROCESSED_ROOT = Path("data/processed/round695_external_feeds_lpr_repaired_20260709")
DEFAULT_REFERENCE_DEDUP = Path(
    "data/reports/round735_lpr_macro_regime_state_conditioned_reference_dedup_20260709/"
    "lpr_macro_regime_state_conditioned_reference_dedup.json"
)
DEFAULT_SMOKE = Path(
    "data/reports/round734_lpr_macro_regime_factor_value_reconstruction_smoke_20260709/"
    "lpr_macro_regime_factor_value_reconstruction_smoke.json"
)
DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_DAILY_BASIC_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260617_daily_basic_factor_inputs"),
)
DEFAULT_STOCK_BASIC = Path("data/processed/cn_stock_metadata")
DEFAULT_OUTPUT_DIR = Path("data/reports/round736_lpr_macro_regime_state_conditioned_walk_forward_preflight_20260709")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run LPR macro regime state-conditioned walk-forward preflight.")
    parser.add_argument("--processed-root", default=str(DEFAULT_PROCESSED_ROOT))
    parser.add_argument("--reference-dedup", default=str(DEFAULT_REFERENCE_DEDUP))
    parser.add_argument("--smoke", default=str(DEFAULT_SMOKE))
    parser.add_argument("--bars-root", action="append", default=None, dest="bars_roots")
    parser.add_argument("--daily-basic-root", action="append", default=None, dest="daily_basic_roots")
    parser.add_argument("--stock-basic", default=str(DEFAULT_STOCK_BASIC))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--market", default="CN")
    parser.add_argument("--analysis-start-date", default="2024-07-01")
    parser.add_argument("--analysis-end-date", default="2025-12-31")
    parser.add_argument("--lookback-days", type=int, default=60)
    parser.add_argument("--min-abs-gap-change", type=float, default=0.01)
    parser.add_argument("--min-signal-date-amount", type=float, default=10_000_000)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-industries", type=int, default=2)
    parser.add_argument("--min-assets-per-industry", type=int, default=2)
    parser.add_argument("--min-state-dates", type=int, default=20)
    parser.add_argument("--min-median-cross-section", type=int, default=100)
    parser.add_argument("--min-pair-observations", type=int, default=DEFAULT_MIN_PAIR_OBSERVATIONS)
    parser.add_argument("--min-corr-cross-section", type=int, default=DEFAULT_MIN_CORR_CROSS_SECTION)
    parser.add_argument("--candidate-high-corr-threshold", type=float, default=DEFAULT_CANDIDATE_HIGH_CORR_THRESHOLD)
    parser.add_argument("--train-state-dates", type=int, default=DEFAULT_TRAIN_STATE_DATES)
    parser.add_argument("--test-state-dates", type=int, default=DEFAULT_TEST_STATE_DATES)
    parser.add_argument("--step-state-dates", type=int, default=DEFAULT_STEP_STATE_DATES)
    parser.add_argument("--min-walk-forward-folds", type=int, default=DEFAULT_MIN_WALK_FORWARD_FOLDS)
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args(argv)
    result = run_lpr_macro_regime_state_conditioned_walk_forward_preflight(
        processed_root=Path(args.processed_root),
        reference_dedup_path=Path(args.reference_dedup),
        smoke_path=Path(args.smoke),
        bars_roots=[Path(path) for path in (args.bars_roots or DEFAULT_BARS_ROOTS)],
        daily_basic_roots=[Path(path) for path in (args.daily_basic_roots or DEFAULT_DAILY_BASIC_ROOTS)],
        stock_basic=Path(args.stock_basic) if args.stock_basic else None,
        output_dir=Path(args.output_dir),
        market=args.market,
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        lookback_days=args.lookback_days,
        min_abs_gap_change=args.min_abs_gap_change,
        min_signal_date_amount=args.min_signal_date_amount,
        min_cross_section=args.min_cross_section,
        min_industries=args.min_industries,
        min_assets_per_industry=args.min_assets_per_industry,
        min_state_dates=args.min_state_dates,
        min_median_cross_section=args.min_median_cross_section,
        min_pair_observations=args.min_pair_observations,
        min_corr_cross_section=args.min_corr_cross_section,
        candidate_high_corr_threshold=args.candidate_high_corr_threshold,
        train_state_dates=args.train_state_dates,
        test_state_dates=args.test_state_dates,
        step_state_dates=args.step_state_dates,
        min_walk_forward_folds=args.min_walk_forward_folds,
    )
    if not args.allow_not_ready and result.get("status") != "cleared":
        blockers = ", ".join(result.get("decision", {}).get("blockers", []) or [])
        raise RuntimeError(f"LPR state-conditioned walk-forward preflight is not ready: {blockers}")
    print(
        json.dumps(
            {
                "status": result.get("status"),
                "summary": result.get("summary", {}),
                "decision": result.get("decision", {}),
                "preflight_policy": result.get("preflight_policy", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
