from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.lpr_macro_regime_state_conditioned_walk_forward_validation import (  # noqa: E402
    run_lpr_macro_regime_state_conditioned_walk_forward_validation,
)


DEFAULT_PROCESSED_ROOT = Path("data/processed/round695_external_feeds_lpr_repaired_20260709")
DEFAULT_PREFLIGHT = Path(
    "data/reports/round736_lpr_macro_regime_state_conditioned_walk_forward_preflight_20260709/"
    "lpr_macro_regime_state_conditioned_walk_forward_preflight.json"
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
DEFAULT_OUTPUT_DIR = Path("data/reports/round737_lpr_macro_regime_state_conditioned_walk_forward_validation_20260709")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run LPR macro regime state-conditioned walk-forward validation.")
    parser.add_argument("--processed-root", default=str(DEFAULT_PROCESSED_ROOT))
    parser.add_argument("--preflight", default=str(DEFAULT_PREFLIGHT))
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
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--cost-bps", type=float, default=10.0)
    parser.add_argument("--portfolio-value", type=float, default=1_000_000.0)
    parser.add_argument("--max-participation-rate", type=float, default=0.01)
    parser.add_argument("--quantiles", type=int, default=5)
    parser.add_argument("--min-ic-observations", type=int, default=10)
    parser.add_argument("--min-ic-cross-section", type=int, default=30)
    parser.add_argument("--min-selected-assets", type=int, default=20)
    parser.add_argument("--min-test-positive-ic-rate", type=float, default=0.50)
    parser.add_argument("--min-test-long-short-positive-rate", type=float, default=0.50)
    parser.add_argument("--min-accepted-folds", type=int, default=2)
    parser.add_argument("--min-regime-allowed-dates", type=int, default=1)
    parser.add_argument("--min-regime-blocked-dates", type=int, default=1)
    parser.add_argument("--max-exposure-challenge-mean-abs-corr", type=float, default=0.45)
    parser.add_argument("--max-exposure-challenge-max-abs-corr", type=float, default=0.85)
    parser.add_argument("--allow-not-accepted", action="store_true")
    args = parser.parse_args(argv)
    result = run_lpr_macro_regime_state_conditioned_walk_forward_validation(
        processed_root=Path(args.processed_root),
        preflight_path=Path(args.preflight),
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
        execution_lag=args.execution_lag,
        cost_bps=args.cost_bps,
        portfolio_value=args.portfolio_value,
        max_participation_rate=args.max_participation_rate,
        quantiles=args.quantiles,
        min_ic_observations=args.min_ic_observations,
        min_ic_cross_section=args.min_ic_cross_section,
        min_selected_assets=args.min_selected_assets,
        min_test_positive_ic_rate=args.min_test_positive_ic_rate,
        min_test_long_short_positive_rate=args.min_test_long_short_positive_rate,
        min_accepted_folds=args.min_accepted_folds,
        min_regime_allowed_dates=args.min_regime_allowed_dates,
        min_regime_blocked_dates=args.min_regime_blocked_dates,
        max_exposure_challenge_mean_abs_corr=args.max_exposure_challenge_mean_abs_corr,
        max_exposure_challenge_max_abs_corr=args.max_exposure_challenge_max_abs_corr,
    )
    if not args.allow_not_accepted and result.get("status") != "accepted":
        blockers = ", ".join(result.get("decision", {}).get("blockers", []) or [])
        raise RuntimeError(f"LPR state-conditioned walk-forward validation is not accepted: {blockers}")
    print(
        json.dumps(
            {
                "status": result.get("status"),
                "summary": result.get("summary", {}),
                "decision": result.get("decision", {}),
                "promotion_policy": result.get("promotion_policy", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
