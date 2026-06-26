from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.turnover_low_overlay_walk_forward import (  # noqa: E402
    DEFAULT_POLICIES,
    market_state_policy_grid_from_returns,
    run_overlay_walk_forward_from_period_returns,
)


DEFAULT_PERIOD_RETURNS = Path(
    "data/reports/round317_24h_profit_sprint_turnover_low_tradeability_exposure_20260627/turnover_low_period_returns.csv"
)
DEFAULT_OUTPUT_DIR = Path("data/reports/turnover_low_overlay_walk_forward")


def run_turnover_low_overlay_walk_forward(
    *,
    period_returns: str | Path = DEFAULT_PERIOD_RETURNS,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    return_column: str = "entry_cash_proxy_return",
    decision_date_column: str = "entry_date",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    train_years: int = 3,
    test_years: int = 1,
    step_years: int = 1,
    include_market_state_policies: bool = False,
    market_return_csv: str | Path | None = None,
    market_return_date_column: str = "date",
    market_return_column: str = "market_return",
    market_lookbacks: tuple[int, ...] = (60, 120, 180),
    market_momentum_thresholds: tuple[float, ...] = (0.0, -0.05),
    market_drawdown_threshold: float = -0.10,
    market_cap_exposures: tuple[float, ...] = (0.50, 0.25),
) -> dict:
    period_frame = pd.read_csv(Path(period_returns))
    policies = list(DEFAULT_POLICIES)
    market_exposure_caps = None
    if include_market_state_policies:
        if market_return_csv is None:
            raise ValueError("market_return_csv is required when include_market_state_policies is enabled")
        market_returns = _read_market_returns(
            Path(market_return_csv),
            date_column=market_return_date_column,
            return_column=market_return_column,
        )
        market_policies, market_exposure_caps = market_state_policy_grid_from_returns(
            market_returns,
            lookback_periods=market_lookbacks,
            momentum_thresholds=market_momentum_thresholds,
            drawdown_threshold=market_drawdown_threshold,
            cap_exposures=market_cap_exposures,
        )
        policies.extend(market_policies)
    return run_overlay_walk_forward_from_period_returns(
        period_frame,
        output_dir=Path(output_dir),
        return_column=return_column,
        decision_date_column=decision_date_column,
        market_exposure_caps=market_exposure_caps,
        periods_per_year=periods_per_year,
        holding_period=holding_period,
        train_years=train_years,
        test_years=test_years,
        step_years=step_years,
        policies=tuple(policies),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run calendar walk-forward validation for turnover-low overlay policies.")
    parser.add_argument("--period-returns", default=str(DEFAULT_PERIOD_RETURNS))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--return-column", default="entry_cash_proxy_return")
    parser.add_argument("--decision-date-column", default="entry_date")
    parser.add_argument("--periods-per-year", type=float, default=252.0 / 5.0)
    parser.add_argument("--holding-period", type=int, default=20)
    parser.add_argument("--train-years", type=int, default=3)
    parser.add_argument("--test-years", type=int, default=1)
    parser.add_argument("--step-years", type=int, default=1)
    parser.add_argument("--include-market-state-policies", action="store_true")
    parser.add_argument("--market-return-csv")
    parser.add_argument("--market-return-date-column", default="date")
    parser.add_argument("--market-return-column", default="market_return")
    parser.add_argument("--market-lookbacks", nargs="+", type=int, default=[60, 120, 180])
    parser.add_argument("--market-momentum-thresholds", nargs="+", type=float, default=[0.0, -0.05])
    parser.add_argument("--market-drawdown-threshold", type=float, default=-0.10)
    parser.add_argument("--market-cap-exposures", nargs="+", type=float, default=[0.50, 0.25])
    args = parser.parse_args()

    result = run_turnover_low_overlay_walk_forward(
        period_returns=Path(args.period_returns),
        output_dir=Path(args.output_dir),
        return_column=args.return_column,
        decision_date_column=args.decision_date_column,
        periods_per_year=args.periods_per_year,
        holding_period=args.holding_period,
        train_years=args.train_years,
        test_years=args.test_years,
        step_years=args.step_years,
        include_market_state_policies=args.include_market_state_policies,
        market_return_csv=Path(args.market_return_csv) if args.market_return_csv else None,
        market_return_date_column=args.market_return_date_column,
        market_return_column=args.market_return_column,
        market_lookbacks=tuple(args.market_lookbacks),
        market_momentum_thresholds=tuple(args.market_momentum_thresholds),
        market_drawdown_threshold=args.market_drawdown_threshold,
        market_cap_exposures=tuple(args.market_cap_exposures),
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "policy_summary": result["policy_summary"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_market_returns(path: Path, *, date_column: str, return_column: str) -> pd.Series:
    frame = pd.read_csv(path)
    missing = [column for column in (date_column, return_column) if column not in frame]
    if missing:
        raise ValueError(f"market return csv missing columns: {', '.join(missing)}")
    dates = pd.to_datetime(frame[date_column])
    returns = pd.to_numeric(frame[return_column], errors="coerce").fillna(0.0)
    return pd.Series(returns.to_numpy(dtype=float), index=pd.DatetimeIndex(dates)).sort_index()


if __name__ == "__main__":
    main()
