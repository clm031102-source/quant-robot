from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.cn_calendar_pre_holiday_cost_capacity_preflight import (  # noqa: E402
    DEFAULT_COST_BPS_VALUES,
    DEFAULT_EXECUTION_LAG,
    DEFAULT_FACTOR_NAME,
    DEFAULT_HOLDING_PERIOD,
    DEFAULT_MARKET_IMPACT_BPS,
    DEFAULT_MAX_CALENDAR_HOLDING_DAYS,
    DEFAULT_MAX_DRAWDOWN_FLOOR,
    DEFAULT_MAX_PARTICIPATION_RATE,
    DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE,
    DEFAULT_MIN_SIGNAL_AMOUNT,
    DEFAULT_PERIODS_PER_YEAR,
    DEFAULT_PORTFOLIO_VALUES,
    DEFAULT_REBALANCE_INTERVAL,
    DEFAULT_TOP_N,
    build_cn_calendar_pre_holiday_cost_capacity_preflight,
    write_cn_calendar_pre_holiday_cost_capacity_preflight,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_STOCK_BASIC = Path("data/processed/cn_stock_metadata")
DEFAULT_OUTPUT_DIR = Path("data/reports/cn_calendar_pre_holiday_cost_capacity_preflight_round165_20260623")


def run_cn_calendar_pre_holiday_cost_capacity_preflight_cli(
    *,
    bars_roots: Sequence[str | Path] = DEFAULT_BARS_ROOTS,
    stock_basic: str | Path = DEFAULT_STOCK_BASIC,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    include_final_holdout: bool = False,
    factor_name: str = DEFAULT_FACTOR_NAME,
    cost_bps_values: Sequence[float] = DEFAULT_COST_BPS_VALUES,
    portfolio_values: Sequence[float] = DEFAULT_PORTFOLIO_VALUES,
    top_n: int = DEFAULT_TOP_N,
    holding_period: int = DEFAULT_HOLDING_PERIOD,
    rebalance_interval: int = DEFAULT_REBALANCE_INTERVAL,
    execution_lag: int = DEFAULT_EXECUTION_LAG,
    min_signal_date_amount: float = DEFAULT_MIN_SIGNAL_AMOUNT,
    min_signal_amount: float = DEFAULT_MIN_SIGNAL_AMOUNT,
    max_participation_rate: float = DEFAULT_MAX_PARTICIPATION_RATE,
    market_impact_bps: float = DEFAULT_MARKET_IMPACT_BPS,
    max_calendar_holding_days: int | None = DEFAULT_MAX_CALENDAR_HOLDING_DAYS,
    min_overlap_adjusted_sharpe: float = DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE,
    max_drawdown_floor: float = DEFAULT_MAX_DRAWDOWN_FLOOR,
    periods_per_year: float = DEFAULT_PERIODS_PER_YEAR,
    min_cross_section: int = 30,
    min_industries: int = 2,
    min_assets_per_industry: int = 2,
) -> dict[str, Any]:
    result = build_cn_calendar_pre_holiday_cost_capacity_preflight(
        bars_roots=bars_roots,
        stock_basic=stock_basic,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        factor_name=factor_name,
        cost_bps_values=cost_bps_values,
        portfolio_values=portfolio_values,
        top_n=top_n,
        holding_period=holding_period,
        rebalance_interval=rebalance_interval,
        execution_lag=execution_lag,
        min_signal_date_amount=min_signal_date_amount,
        min_signal_amount=min_signal_amount,
        max_participation_rate=max_participation_rate,
        market_impact_bps=market_impact_bps,
        max_calendar_holding_days=max_calendar_holding_days,
        min_overlap_adjusted_sharpe=min_overlap_adjusted_sharpe,
        max_drawdown_floor=max_drawdown_floor,
        periods_per_year=periods_per_year,
        min_cross_section=min_cross_section,
        min_industries=min_industries,
        min_assets_per_industry=min_assets_per_industry,
    )
    write_cn_calendar_pre_holiday_cost_capacity_preflight(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Round165 CN calendar pre-holiday cost/capacity preflight.")
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--stock-basic", default=str(DEFAULT_STOCK_BASIC))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default="2015-01-01")
    parser.add_argument("--analysis-end-date", default="2025-12-31")
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--factor-name", default=DEFAULT_FACTOR_NAME)
    parser.add_argument("--cost-bps-values", default=",".join(str(value) for value in DEFAULT_COST_BPS_VALUES))
    parser.add_argument("--portfolio-values", default=",".join(str(value) for value in DEFAULT_PORTFOLIO_VALUES))
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    parser.add_argument("--holding-period", type=int, default=DEFAULT_HOLDING_PERIOD)
    parser.add_argument("--rebalance-interval", type=int, default=DEFAULT_REBALANCE_INTERVAL)
    parser.add_argument("--execution-lag", type=int, default=DEFAULT_EXECUTION_LAG)
    parser.add_argument("--min-signal-date-amount", type=float, default=DEFAULT_MIN_SIGNAL_AMOUNT)
    parser.add_argument("--min-signal-amount", type=float, default=DEFAULT_MIN_SIGNAL_AMOUNT)
    parser.add_argument("--max-participation-rate", type=float, default=DEFAULT_MAX_PARTICIPATION_RATE)
    parser.add_argument("--market-impact-bps", type=float, default=DEFAULT_MARKET_IMPACT_BPS)
    parser.add_argument("--max-calendar-holding-days", type=int, default=DEFAULT_MAX_CALENDAR_HOLDING_DAYS)
    parser.add_argument("--min-overlap-adjusted-sharpe", type=float, default=DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE)
    parser.add_argument("--max-drawdown-floor", type=float, default=DEFAULT_MAX_DRAWDOWN_FLOOR)
    parser.add_argument("--periods-per-year", type=float, default=DEFAULT_PERIODS_PER_YEAR)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-industries", type=int, default=2)
    parser.add_argument("--min-assets-per-industry", type=int, default=2)
    args = parser.parse_args()
    result = run_cn_calendar_pre_holiday_cost_capacity_preflight_cli(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        stock_basic=Path(args.stock_basic),
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        factor_name=args.factor_name,
        cost_bps_values=_parse_float_list(args.cost_bps_values),
        portfolio_values=_parse_float_list(args.portfolio_values),
        top_n=args.top_n,
        holding_period=args.holding_period,
        rebalance_interval=args.rebalance_interval,
        execution_lag=args.execution_lag,
        min_signal_date_amount=args.min_signal_date_amount,
        min_signal_amount=args.min_signal_amount,
        max_participation_rate=args.max_participation_rate,
        market_impact_bps=args.market_impact_bps,
        max_calendar_holding_days=args.max_calendar_holding_days,
        min_overlap_adjusted_sharpe=args.min_overlap_adjusted_sharpe,
        max_drawdown_floor=args.max_drawdown_floor,
        periods_per_year=args.periods_per_year,
        min_cross_section=args.min_cross_section,
        min_industries=args.min_industries,
        min_assets_per_industry=args.min_assets_per_industry,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "portfolio_preflight_policy": result["portfolio_preflight_policy"],
                "promotion_policy": result["promotion_policy"],
                "next_direction": result["next_direction"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _parse_float_list(value: str) -> tuple[float, ...]:
    return tuple(float(item.strip()) for item in value.split(",") if item.strip())


if __name__ == "__main__":
    main()
