from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.capacity_safe_price_volume_prescreen import (  # noqa: E402
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
)
from quant_robot.ops.turnover_repair_champion_portfolio_conversion import (  # noqa: E402
    DEFAULT_CHAMPION_FACTOR_NAME,
    DEFAULT_COST_BPS_VALUES,
    DEFAULT_EXECUTION_LAG,
    DEFAULT_HOLDING_PERIOD,
    DEFAULT_MARKET_IMPACT_BPS,
    DEFAULT_MAX_CALENDAR_HOLDING_DAYS,
    DEFAULT_MAX_DRAWDOWN_FLOOR,
    DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE,
    DEFAULT_MIN_SIGNAL_AMOUNT,
    DEFAULT_PORTFOLIO_VALUES,
    DEFAULT_REBALANCE_INTERVAL,
    build_turnover_repair_champion_portfolio_conversion,
    write_turnover_repair_champion_portfolio_conversion,
)
from quant_robot.ops.turnover_continuous_capacity_repair_prescreen import (  # noqa: E402
    DEFAULT_MAX_PARTICIPATION,
    DEFAULT_TOP_N,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_FACTOR_INPUT_ROOT = Path("configs/cn_stock_authority_daily_basic_inputs_2015_2025.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/turnover_repair_champion_portfolio_conversion_round126_20260622")


def run_turnover_repair_champion_portfolio_conversion_cli(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    factor_input_root: str | Path = DEFAULT_FACTOR_INPUT_ROOT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    factor_name: str = DEFAULT_CHAMPION_FACTOR_NAME,
    cost_bps_values: Sequence[float] = DEFAULT_COST_BPS_VALUES,
    portfolio_values: Sequence[float] = DEFAULT_PORTFOLIO_VALUES,
    top_n: int = DEFAULT_TOP_N,
    holding_period: int = DEFAULT_HOLDING_PERIOD,
    rebalance_interval: int = DEFAULT_REBALANCE_INTERVAL,
    execution_lag: int = DEFAULT_EXECUTION_LAG,
    min_signal_date_amount: float = DEFAULT_MIN_SIGNAL_AMOUNT,
    min_signal_amount: float = DEFAULT_MIN_SIGNAL_AMOUNT,
    max_participation_rate: float = DEFAULT_MAX_PARTICIPATION,
    market_impact_bps: float = DEFAULT_MARKET_IMPACT_BPS,
    max_calendar_holding_days: int | None = DEFAULT_MAX_CALENDAR_HOLDING_DAYS,
    min_overlap_adjusted_sharpe: float = DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE,
    max_drawdown_floor: float = DEFAULT_MAX_DRAWDOWN_FLOOR,
    stock_basic_path: str | Path | None = None,
    stk_limit_path: str | Path | None = None,
    suspension_path: str | Path | None = None,
    namechange_path: str | Path | None = None,
    tradeability_mask_path: str | Path | None = None,
) -> dict[str, Any]:
    result = build_turnover_repair_champion_portfolio_conversion(
        bars_roots=bars_roots,
        factor_input_root=factor_input_root,
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
        stock_basic=_read_frame(stock_basic_path) if stock_basic_path is not None else None,
        stk_limit=_read_frame(stk_limit_path) if stk_limit_path is not None else None,
        suspension=_read_frame(suspension_path) if suspension_path is not None else None,
        namechange=_read_frame(namechange_path) if namechange_path is not None else None,
        tradeability_frame=_read_frame(tradeability_mask_path) if tradeability_mask_path is not None else None,
    )
    result["input_paths"] = {
        "bars_roots": [str(Path(path)) for path in bars_roots],
        "factor_input_root": str(Path(factor_input_root)),
        "stock_basic_path": _optional_path(stock_basic_path),
        "stk_limit_path": _optional_path(stk_limit_path),
        "suspension_path": _optional_path(suspension_path),
        "namechange_path": _optional_path(namechange_path),
        "tradeability_mask_path": _optional_path(tradeability_mask_path),
    }
    write_turnover_repair_champion_portfolio_conversion(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Round126 single frozen turnover-repair champion costed portfolio conversion."
    )
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--factor-input-root", default=str(DEFAULT_FACTOR_INPUT_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default=DEFAULT_ANALYSIS_START_DATE)
    parser.add_argument("--analysis-end-date", default=DEFAULT_ANALYSIS_END_DATE)
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--factor-name", default=DEFAULT_CHAMPION_FACTOR_NAME)
    parser.add_argument("--cost-bps-values", default=",".join(str(value) for value in DEFAULT_COST_BPS_VALUES))
    parser.add_argument("--portfolio-values", default=",".join(str(value) for value in DEFAULT_PORTFOLIO_VALUES))
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    parser.add_argument("--holding-period", type=int, default=DEFAULT_HOLDING_PERIOD)
    parser.add_argument("--rebalance-interval", type=int, default=DEFAULT_REBALANCE_INTERVAL)
    parser.add_argument("--execution-lag", type=int, default=DEFAULT_EXECUTION_LAG)
    parser.add_argument("--min-signal-date-amount", type=float, default=DEFAULT_MIN_SIGNAL_AMOUNT)
    parser.add_argument("--min-signal-amount", type=float, default=DEFAULT_MIN_SIGNAL_AMOUNT)
    parser.add_argument("--max-participation-rate", type=float, default=DEFAULT_MAX_PARTICIPATION)
    parser.add_argument("--market-impact-bps", type=float, default=DEFAULT_MARKET_IMPACT_BPS)
    parser.add_argument("--max-calendar-holding-days", type=int, default=DEFAULT_MAX_CALENDAR_HOLDING_DAYS)
    parser.add_argument("--min-overlap-adjusted-sharpe", type=float, default=DEFAULT_MIN_OVERLAP_ADJUSTED_SHARPE)
    parser.add_argument("--max-drawdown-floor", type=float, default=DEFAULT_MAX_DRAWDOWN_FLOOR)
    parser.add_argument("--stock-basic-path")
    parser.add_argument("--stk-limit-path")
    parser.add_argument("--suspension-path")
    parser.add_argument("--namechange-path")
    parser.add_argument("--tradeability-mask-path")
    args = parser.parse_args()
    bars_roots = tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS))
    result = run_turnover_repair_champion_portfolio_conversion_cli(
        bars_roots=bars_roots,
        factor_input_root=Path(args.factor_input_root),
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
        stock_basic_path=Path(args.stock_basic_path) if args.stock_basic_path else None,
        stk_limit_path=Path(args.stk_limit_path) if args.stk_limit_path else None,
        suspension_path=Path(args.suspension_path) if args.suspension_path else None,
        namechange_path=Path(args.namechange_path) if args.namechange_path else None,
        tradeability_mask_path=Path(args.tradeability_mask_path) if args.tradeability_mask_path else None,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "portfolio_conversion_policy": result["portfolio_conversion_policy"],
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


def _optional_path(path: str | Path | None) -> str | None:
    return str(Path(path)) if path is not None else None


def _read_frame(path: str | Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame()
    source = Path(path)
    if source.is_dir():
        files = sorted(source.rglob("*.parquet")) or sorted(source.rglob("*.csv"))
        if not files:
            raise ValueError(f"No parquet or csv files found under {source}")
        return pd.concat([_read_frame(file) for file in files], ignore_index=True)
    suffix = source.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(source)
    if suffix == ".parquet":
        return pd.read_parquet(source)
    raise ValueError(f"Unsupported input file type for {source}")


if __name__ == "__main__":
    main()
