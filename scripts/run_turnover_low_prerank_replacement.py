from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.turnover_low_prerank_replacement import (  # noqa: E402
    DEFAULT_VARIANTS,
    run_turnover_low_prerank_replacement,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_DAILY_BASIC_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260617_daily_basic_factor_inputs"),
)
DEFAULT_TRADEABILITY_MASK_ROOTS = (
    Path("data/processed/round199_tradeability_mask_cache_2015_2025_with_stock_basic_20260623/processed/tradeability_masks"),
)
DEFAULT_METADATA_ROOTS = (Path("data/processed/cn_stock_metadata/metadata/tushare_stock_basic"),)
DEFAULT_OUTPUT_DIR = Path("data/reports/turnover_low_prerank_replacement")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run low-turnover pre-rank replacement variants.")
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--daily-basic-root", action="append", default=None)
    parser.add_argument("--tradeability-mask-root", action="append", default=None)
    parser.add_argument("--metadata-root", action="append", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default="2015-01-01")
    parser.add_argument("--analysis-end-date", default="2025-12-31")
    parser.add_argument("--factor-name", default="turnover_rate_low")
    parser.add_argument("--factor-price-column", default="close")
    parser.add_argument("--backtest-price-column", default="close")
    parser.add_argument("--top-n", type=int, default=50)
    parser.add_argument("--cost-bps", type=float, default=5.0)
    parser.add_argument("--holding-period", type=int, default=20)
    parser.add_argument("--rebalance-interval", type=int, default=5)
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--min-signal-date-amount", type=float, default=10_000_000.0)
    parser.add_argument("--portfolio-value", type=float, default=1_000_000.0)
    parser.add_argument("--max-participation-rate", type=float, default=0.05)
    parser.add_argument("--market-impact-bps", type=float, default=0.0)
    parser.add_argument("--exclude-asset-prefix", action="append", default=None)
    parser.add_argument("--max-abs-daily-return-quarantine", type=float)
    args = parser.parse_args()

    result = run_turnover_low_prerank_replacement(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        daily_basic_roots=tuple(Path(path) for path in (args.daily_basic_root or DEFAULT_DAILY_BASIC_ROOTS)),
        tradeability_mask_roots=tuple(
            Path(path) for path in (args.tradeability_mask_root or DEFAULT_TRADEABILITY_MASK_ROOTS)
        ),
        metadata_roots=tuple(Path(path) for path in (args.metadata_root or DEFAULT_METADATA_ROOTS)),
        output_dir=Path(args.output_dir),
        variants=DEFAULT_VARIANTS,
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        factor_name=args.factor_name,
        factor_price_column=args.factor_price_column,
        backtest_price_column=args.backtest_price_column,
        top_n=args.top_n,
        cost_bps=args.cost_bps,
        holding_period=args.holding_period,
        rebalance_interval=args.rebalance_interval,
        execution_lag=args.execution_lag,
        min_signal_date_amount=args.min_signal_date_amount,
        portfolio_value=args.portfolio_value,
        max_participation_rate=args.max_participation_rate,
        market_impact_bps=args.market_impact_bps,
        exclude_asset_prefixes=tuple(args.exclude_asset_prefix or ()),
        max_abs_daily_return_quarantine=args.max_abs_daily_return_quarantine,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "rows": result["rows"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
