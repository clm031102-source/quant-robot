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

from quant_robot.ops.financial_pit_post_announcement_gap_reversal_walk_forward_validation import (  # noqa: E402
    build_financial_pit_post_announcement_gap_reversal_walk_forward_validation,
    write_financial_pit_post_announcement_gap_reversal_walk_forward_validation,
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
DEFAULT_PREFLIGHT_JSON = Path(
    "data/reports/financial_pit_post_announcement_gap_reversal_walk_forward_preflight_round224_20260624/"
    "financial_pit_post_announcement_gap_reversal_walk_forward_preflight.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "data/reports/financial_pit_post_announcement_gap_reversal_walk_forward_validation_round225_20260624"
)
SENTINEL_TOP_N_VALUES = (20,)
SENTINEL_HOLDING_PERIODS = (5,)
SENTINEL_REBALANCE_INTERVALS = (5,)
SENTINEL_COST_BPS_VALUES = (10.0,)
SENTINEL_PORTFOLIO_VALUES = (1_000_000.0,)


def run_financial_pit_post_announcement_gap_reversal_walk_forward_validation_cli(
    *,
    financial_root: str | Path = DEFAULT_FINANCIAL_ROOT,
    bars_roots: list[str | Path] | tuple[str | Path, ...] = DEFAULT_BARS_ROOTS,
    preregistration_json: str | Path = DEFAULT_PREREGISTRATION_JSON,
    preflight_json: str | Path = DEFAULT_PREFLIGHT_JSON,
    candidate_plan_gate_json: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    include_final_holdout: bool = False,
    top_n_values: list[int] | tuple[int, ...] | None = None,
    holding_periods: list[int] | tuple[int, ...] | None = None,
    rebalance_intervals: list[int] | tuple[int, ...] | None = None,
    cost_bps_values: list[float] | tuple[float, ...] | None = None,
    portfolio_values: list[float] | tuple[float, ...] | None = None,
    market_impact_bps: float | None = None,
    max_participation_rate: float | None = None,
    min_signal_amount: float | None = 10_000_000.0,
    min_test_overlap_adjusted_sharpe: float = 0.30,
    max_test_drawdown_limit: float = 0.45,
    min_accepted_folds: int = 2,
    min_positive_test_fold_rate: float = 0.50,
    min_test_trades: int = 5,
    min_regime_states: int = 2,
    full_grid: bool = False,
    allow_no_accepted: bool = False,
) -> dict[str, Any]:
    if not full_grid:
        top_n_values = tuple(top_n_values or SENTINEL_TOP_N_VALUES)
        holding_periods = tuple(holding_periods or SENTINEL_HOLDING_PERIODS)
        rebalance_intervals = tuple(rebalance_intervals or SENTINEL_REBALANCE_INTERVALS)
        cost_bps_values = tuple(cost_bps_values or SENTINEL_COST_BPS_VALUES)
        portfolio_values = tuple(portfolio_values or SENTINEL_PORTFOLIO_VALUES)
    result = build_financial_pit_post_announcement_gap_reversal_walk_forward_validation(
        financial_root=Path(financial_root),
        bars_roots=[Path(root) for root in bars_roots],
        preregistration_json=Path(preregistration_json),
        preflight_json=Path(preflight_json),
        candidate_plan_gate_json=Path(candidate_plan_gate_json) if candidate_plan_gate_json else None,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        top_n_values=top_n_values,
        holding_periods=holding_periods,
        rebalance_intervals=rebalance_intervals,
        cost_bps_values=cost_bps_values,
        portfolio_values=portfolio_values,
        market_impact_bps=market_impact_bps,
        max_participation_rate=max_participation_rate,
        min_signal_amount=min_signal_amount,
        min_test_overlap_adjusted_sharpe=min_test_overlap_adjusted_sharpe,
        max_test_drawdown_limit=max_test_drawdown_limit,
        min_accepted_folds=min_accepted_folds,
        min_positive_test_fold_rate=min_positive_test_fold_rate,
        min_test_trades=min_test_trades,
        min_regime_states=min_regime_states,
    )
    write_financial_pit_post_announcement_gap_reversal_walk_forward_validation(output_dir, result)
    if not allow_no_accepted and int(result.get("summary", {}).get("accepted", 0)) == 0:
        raise RuntimeError("Round225 gap reversal walk-forward validation found no accepted candidates")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Round225 financial PIT gap reversal walk-forward cost/capacity/regime validation."
    )
    parser.add_argument("--financial-root", default=str(DEFAULT_FINANCIAL_ROOT))
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--preregistration-json", default=str(DEFAULT_PREREGISTRATION_JSON))
    parser.add_argument("--preflight-json", default=str(DEFAULT_PREFLIGHT_JSON))
    parser.add_argument("--candidate-plan-gate-json")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default="2015-01-01")
    parser.add_argument("--analysis-end-date", default="2025-12-31")
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--top-n-values")
    parser.add_argument("--holding-periods")
    parser.add_argument("--rebalance-intervals")
    parser.add_argument("--cost-bps-values")
    parser.add_argument("--portfolio-values")
    parser.add_argument("--market-impact-bps", type=float)
    parser.add_argument("--max-participation-rate", type=float)
    parser.add_argument("--min-signal-amount", type=float, default=10_000_000.0)
    parser.add_argument("--min-test-overlap-adjusted-sharpe", type=float, default=0.30)
    parser.add_argument("--max-test-drawdown-limit", type=float, default=0.45)
    parser.add_argument("--min-accepted-folds", type=int, default=2)
    parser.add_argument("--min-positive-test-fold-rate", type=float, default=0.50)
    parser.add_argument("--min-test-trades", type=int, default=5)
    parser.add_argument("--min-regime-states", type=int, default=2)
    parser.add_argument("--full-grid", action="store_true", help="Use the full Round224 frozen cost/capacity grid instead of the sentinel grid.")
    parser.add_argument("--allow-no-accepted", action="store_true")
    args = parser.parse_args()
    result = run_financial_pit_post_announcement_gap_reversal_walk_forward_validation_cli(
        financial_root=Path(args.financial_root),
        bars_roots=[Path(root) for root in (args.bars_root or DEFAULT_BARS_ROOTS)],
        preregistration_json=Path(args.preregistration_json),
        preflight_json=Path(args.preflight_json),
        candidate_plan_gate_json=Path(args.candidate_plan_gate_json) if args.candidate_plan_gate_json else None,
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        top_n_values=_parse_int_list(args.top_n_values),
        holding_periods=_parse_int_list(args.holding_periods),
        rebalance_intervals=_parse_int_list(args.rebalance_intervals),
        cost_bps_values=_parse_float_list(args.cost_bps_values),
        portfolio_values=_parse_float_list(args.portfolio_values),
        market_impact_bps=args.market_impact_bps,
        max_participation_rate=args.max_participation_rate,
        min_signal_amount=args.min_signal_amount,
        min_test_overlap_adjusted_sharpe=args.min_test_overlap_adjusted_sharpe,
        max_test_drawdown_limit=args.max_test_drawdown_limit,
        min_accepted_folds=args.min_accepted_folds,
        min_positive_test_fold_rate=args.min_positive_test_fold_rate,
        min_test_trades=args.min_test_trades,
        min_regime_states=args.min_regime_states,
        full_grid=args.full_grid,
        allow_no_accepted=args.allow_no_accepted,
    )
    print(
        json.dumps(
            {
                "summary": result.get("summary", {}),
                "top": result.get("leaderboard", [])[:10],
                "promotion_policy": result.get("promotion_policy", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _parse_int_list(value: str | None) -> tuple[int, ...] | None:
    if not value:
        return None
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


def _parse_float_list(value: str | None) -> tuple[float, ...] | None:
    if not value:
        return None
    return tuple(float(item.strip()) for item in value.split(",") if item.strip())


if __name__ == "__main__":
    main()
