from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.capacity_safe_price_volume_prescreen import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.daily_basic_free_float_supply_quality_event_adjusted_clean_rerun import (  # noqa: E402
    DEFAULT_ROUND139_AUDIT_REPORT,
    SUPPORTED_EXCLUSION_SCOPES,
    build_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun,
    write_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun,
)
from quant_robot.ops.daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun import (  # noqa: E402
    DEFAULT_COST_BPS_VALUES,
    DEFAULT_EXECUTION_LAG,
    DEFAULT_GUARD_MODES,
    DEFAULT_HOLDING_PERIOD,
    DEFAULT_MARKET_IMPACT_BPS,
    DEFAULT_MAX_CALENDAR_HOLDING_DAYS,
    DEFAULT_MAX_DRAWDOWN_FLOOR,
    DEFAULT_MIN_OOS_OVERLAP_ADJUSTED_SHARPE,
    DEFAULT_PORTFOLIO_VALUES,
    DEFAULT_PRICE_BASIS,
    DEFAULT_REBALANCE_INTERVAL,
    DEFAULT_TEST_START_DATE,
    DEFAULT_TOP_N,
    DEFAULT_TRAIN_END_DATE,
)
from quant_robot.ops.turnover_continuous_capacity_repair_prescreen import (  # noqa: E402
    DEFAULT_MAX_PARTICIPATION,
)
from quant_robot.ops.turnover_repair_champion_portfolio_conversion import (  # noqa: E402
    DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE,
    DEFAULT_MIN_SIGNAL_AMOUNT,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_DAILY_BASIC_ROOTS = (
    Path("data/processed/office_desktop_20260617_daily_basic_factor_inputs"),
)
DEFAULT_OUTPUT_DIR = Path(
    "data/reports/daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_round140_20260622"
)


def run_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    daily_basic_roots: Iterable[str | Path] = DEFAULT_DAILY_BASIC_ROOTS,
    round139_audit_report: str | Path = DEFAULT_ROUND139_AUDIT_REPORT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    exclusion_scope: str = "all",
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    price_basis: str = DEFAULT_PRICE_BASIS,
    cost_bps_values: Sequence[float] = DEFAULT_COST_BPS_VALUES,
    portfolio_values: Sequence[float] = DEFAULT_PORTFOLIO_VALUES,
    guard_modes: Sequence[str] = DEFAULT_GUARD_MODES,
    top_n: int = DEFAULT_TOP_N,
    holding_period: int = DEFAULT_HOLDING_PERIOD,
    rebalance_interval: int = DEFAULT_REBALANCE_INTERVAL,
    execution_lag: int = DEFAULT_EXECUTION_LAG,
    min_cross_section: int = 30,
    min_signal_date_amount: float = DEFAULT_MIN_SIGNAL_AMOUNT,
    min_signal_amount: float = DEFAULT_MIN_SIGNAL_AMOUNT,
    min_field_coverage_ratio: float = 0.95,
    max_participation_rate: float = DEFAULT_MAX_PARTICIPATION,
    market_impact_bps: float = DEFAULT_MARKET_IMPACT_BPS,
    max_calendar_holding_days: int | None = DEFAULT_MAX_CALENDAR_HOLDING_DAYS,
    min_overlap_adjusted_sharpe: float = DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE,
    min_oos_overlap_adjusted_sharpe: float = DEFAULT_MIN_OOS_OVERLAP_ADJUSTED_SHARPE,
    max_drawdown_floor: float = DEFAULT_MAX_DRAWDOWN_FLOOR,
    train_end_date: str = DEFAULT_TRAIN_END_DATE,
    test_start_date: str = DEFAULT_TEST_START_DATE,
) -> dict[str, Any]:
    result = build_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun(
        bars_roots=bars_roots,
        daily_basic_roots=daily_basic_roots,
        round139_audit_report=round139_audit_report,
        exclusion_scope=exclusion_scope,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        price_basis=price_basis,
        cost_bps_values=cost_bps_values,
        portfolio_values=portfolio_values,
        guard_modes=guard_modes,
        top_n=top_n,
        holding_period=holding_period,
        rebalance_interval=rebalance_interval,
        execution_lag=execution_lag,
        min_cross_section=min_cross_section,
        min_signal_date_amount=min_signal_date_amount,
        min_signal_amount=min_signal_amount,
        min_field_coverage_ratio=min_field_coverage_ratio,
        max_participation_rate=max_participation_rate,
        market_impact_bps=market_impact_bps,
        max_calendar_holding_days=max_calendar_holding_days,
        min_overlap_adjusted_sharpe=min_overlap_adjusted_sharpe,
        min_oos_overlap_adjusted_sharpe=min_oos_overlap_adjusted_sharpe,
        max_drawdown_floor=max_drawdown_floor,
        train_end_date=train_end_date,
        test_start_date=test_start_date,
    )
    write_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run Round140 event-adjusted clean rerun for the daily-basic free-float supply quality candidate."
        )
    )
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--daily-basic-root", action="append", default=None)
    parser.add_argument("--round139-audit-report", default=str(DEFAULT_ROUND139_AUDIT_REPORT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--exclusion-scope", choices=SUPPORTED_EXCLUSION_SCOPES, default="all")
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--price-basis", default=DEFAULT_PRICE_BASIS)
    parser.add_argument("--cost-bps-values", default=",".join(str(value) for value in DEFAULT_COST_BPS_VALUES))
    parser.add_argument("--portfolio-values", default=",".join(str(value) for value in DEFAULT_PORTFOLIO_VALUES))
    parser.add_argument("--guard-modes", default=",".join(DEFAULT_GUARD_MODES))
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    parser.add_argument("--holding-period", type=int, default=DEFAULT_HOLDING_PERIOD)
    parser.add_argument("--rebalance-interval", type=int, default=DEFAULT_REBALANCE_INTERVAL)
    parser.add_argument("--execution-lag", type=int, default=DEFAULT_EXECUTION_LAG)
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-signal-date-amount", type=float, default=DEFAULT_MIN_SIGNAL_AMOUNT)
    parser.add_argument("--min-signal-amount", type=float, default=DEFAULT_MIN_SIGNAL_AMOUNT)
    parser.add_argument("--min-field-coverage-ratio", type=float, default=0.95)
    parser.add_argument("--max-participation-rate", type=float, default=DEFAULT_MAX_PARTICIPATION)
    parser.add_argument("--market-impact-bps", type=float, default=DEFAULT_MARKET_IMPACT_BPS)
    parser.add_argument("--max-calendar-holding-days", type=int, default=DEFAULT_MAX_CALENDAR_HOLDING_DAYS)
    parser.add_argument("--min-overlap-adjusted-sharpe", type=float, default=DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE)
    parser.add_argument("--min-oos-overlap-adjusted-sharpe", type=float, default=DEFAULT_MIN_OOS_OVERLAP_ADJUSTED_SHARPE)
    parser.add_argument("--max-drawdown-floor", type=float, default=DEFAULT_MAX_DRAWDOWN_FLOOR)
    parser.add_argument("--train-end-date", default=DEFAULT_TRAIN_END_DATE)
    parser.add_argument("--test-start-date", default=DEFAULT_TEST_START_DATE)
    args = parser.parse_args()
    result = run_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_cli(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        daily_basic_roots=tuple(Path(path) for path in (args.daily_basic_root or DEFAULT_DAILY_BASIC_ROOTS)),
        round139_audit_report=Path(args.round139_audit_report),
        output_dir=Path(args.output_dir),
        exclusion_scope=args.exclusion_scope,
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        price_basis=args.price_basis,
        cost_bps_values=_parse_float_list(args.cost_bps_values),
        portfolio_values=_parse_float_list(args.portfolio_values),
        guard_modes=_parse_str_list(args.guard_modes),
        top_n=args.top_n,
        holding_period=args.holding_period,
        rebalance_interval=args.rebalance_interval,
        execution_lag=args.execution_lag,
        min_cross_section=args.min_cross_section,
        min_signal_date_amount=args.min_signal_date_amount,
        min_signal_amount=args.min_signal_amount,
        min_field_coverage_ratio=args.min_field_coverage_ratio,
        max_participation_rate=args.max_participation_rate,
        market_impact_bps=args.market_impact_bps,
        max_calendar_holding_days=args.max_calendar_holding_days,
        min_overlap_adjusted_sharpe=args.min_overlap_adjusted_sharpe,
        min_oos_overlap_adjusted_sharpe=args.min_oos_overlap_adjusted_sharpe,
        max_drawdown_floor=args.max_drawdown_floor,
        train_end_date=args.train_end_date,
        test_start_date=args.test_start_date,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "event_exclusion_summary": result["event_exclusion_summary"],
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


def _parse_str_list(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


if __name__ == "__main__":
    main()
