from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.bar_factor_clean_portfolio_diagnostic import (  # noqa: E402
    DEFAULT_CANDIDATES,
    run_bar_factor_clean_portfolio_diagnostic,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_OUTPUT_DIR = Path("data/reports/bar_factor_clean_portfolio_diagnostic")


def parse_int_list(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def parse_float_list(value: str) -> tuple[float, ...]:
    return tuple(float(part.strip()) for part in value.split(",") if part.strip())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a clean-universe close-price portfolio diagnostic for bar-based public indicator factors."
    )
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default="2015-01-01")
    parser.add_argument("--analysis-end-date", default="2025-12-31")
    parser.add_argument("--candidate-factor-name", action="append", dest="candidate_factor_names")
    parser.add_argument("--factor-price-column", default="close")
    parser.add_argument("--backtest-price-column", default="close")
    parser.add_argument("--top-n-values", default="100")
    parser.add_argument("--cost-bps-values", default="10")
    parser.add_argument("--holding-period", type=int, default=20)
    parser.add_argument("--rebalance-intervals", default="5")
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--min-signal-date-amount", type=float, default=10_000_000.0)
    parser.add_argument("--portfolio-value", type=float, default=1_000_000.0)
    parser.add_argument("--max-participation-rate", type=float, default=0.05)
    parser.add_argument("--market-impact-bps", type=float, default=0.0)
    parser.add_argument("--exclude-asset-prefix", action="append", default=None)
    parser.add_argument("--max-abs-daily-return-quarantine", type=float)
    parser.add_argument("--min-overlap-adjusted-sharpe", type=float, default=0.50)
    parser.add_argument("--max-drawdown-floor", type=float, default=-0.35)
    parser.add_argument("--extreme-trade-abs-return", type=float, default=0.50)
    args = parser.parse_args()

    result = run_bar_factor_clean_portfolio_diagnostic(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        candidate_factor_names=tuple(args.candidate_factor_names or DEFAULT_CANDIDATES),
        factor_price_column=args.factor_price_column,
        backtest_price_column=args.backtest_price_column,
        top_n_values=parse_int_list(args.top_n_values),
        cost_bps_values=parse_float_list(args.cost_bps_values),
        holding_period=args.holding_period,
        rebalance_intervals=parse_int_list(args.rebalance_intervals),
        execution_lag=args.execution_lag,
        min_signal_date_amount=args.min_signal_date_amount,
        portfolio_value=args.portfolio_value,
        max_participation_rate=args.max_participation_rate,
        market_impact_bps=args.market_impact_bps,
        exclude_asset_prefixes=tuple(args.exclude_asset_prefix or ()),
        max_abs_daily_return_quarantine=args.max_abs_daily_return_quarantine,
        min_overlap_adjusted_sharpe=args.min_overlap_adjusted_sharpe,
        max_drawdown_floor=args.max_drawdown_floor,
        extreme_trade_abs_return=args.extreme_trade_abs_return,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "top": result["leaderboard"][:10],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
