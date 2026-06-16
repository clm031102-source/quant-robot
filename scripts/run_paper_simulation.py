from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.paper.simulator import PaperSimulationConfig, run_paper_simulation, write_paper_simulation_artifacts
from quant_robot.storage.processed_bars import load_processed_bars

DEFAULT_MARKETS = ("CN", "CN_ETF", "HK", "US", "CRYPTO")


def run_simulation(
    source: str = "fixture",
    data_root: str | Path = "data/processed",
    market: str = "ALL",
    factor_source: str = "technical",
    factor_name: str = "momentum_2",
    factor_windows: tuple[int, ...] = (2, 3),
    factor_input_root: str | Path | None = None,
    moneyflow_input_root: str | Path | None = None,
    top_n: int = 2,
    rebalance_interval: int = 1,
    start_date: str | None = None,
    end_date: str | None = None,
    initial_cash: float = 100000.0,
    commission_bps: float = 5.0,
    slippage_bps: float = 5.0,
    market_impact_bps: float = 0.0,
    max_participation_rate: float | None = None,
    min_trade_value: float = 1.0,
    max_asset_weight: float = 1.0,
    max_market_weight: float = 1.0,
    max_gross_exposure: float = 1.0,
    min_cash_weight: float = 0.0,
    periods_per_year: float | None = None,
    max_drawdown_guard: float | None = None,
    guard_cooldown_periods: int = 0,
    positions_csv: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    bars = _load_bars(source, Path(data_root), market)
    positions = pd.read_csv(positions_csv) if positions_csv is not None else None
    config = PaperSimulationConfig(
        market=market,
        factor_source=factor_source,
        factor_name=factor_name,
        factor_windows=factor_windows,
        factor_input_root=Path(factor_input_root) if factor_input_root is not None else None,
        moneyflow_input_root=Path(moneyflow_input_root) if moneyflow_input_root is not None else None,
        top_n=top_n,
        rebalance_interval=rebalance_interval,
        start_date=start_date,
        end_date=end_date,
        initial_cash=initial_cash,
        commission_bps=commission_bps,
        slippage_bps=slippage_bps,
        market_impact_bps=market_impact_bps,
        max_participation_rate=max_participation_rate,
        min_trade_value=min_trade_value,
        max_asset_weight=max_asset_weight,
        max_market_weight=max_market_weight,
        max_gross_exposure=max_gross_exposure,
        min_cash_weight=min_cash_weight,
        periods_per_year=periods_per_year,
        max_drawdown_guard=max_drawdown_guard,
        guard_cooldown_periods=guard_cooldown_periods,
        output_dir=None,
    )
    result = run_paper_simulation(bars, config, initial_positions=positions)
    if output_dir is not None:
        write_paper_simulation_artifacts(result, Path(output_dir))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local paper trading simulation. Research-only; no broker integration.")
    parser.add_argument("--source", choices=["fixture", "processed-bars"], default="fixture")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--market", default="ALL")
    parser.add_argument("--factor-source", choices=["technical", "tushare_daily_basic", "tushare_moneyflow"], default="technical")
    parser.add_argument("--factor", default="momentum_2")
    parser.add_argument("--factor-windows", default="2,3")
    parser.add_argument("--factor-input-root")
    parser.add_argument("--moneyflow-input-root")
    parser.add_argument("--top-n", default=2, type=int)
    parser.add_argument("--rebalance-interval", default=1, type=int)
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--initial-cash", default=100000.0, type=float)
    parser.add_argument("--commission-bps", default=5.0, type=float)
    parser.add_argument("--slippage-bps", default=5.0, type=float)
    parser.add_argument("--market-impact-bps", default=0.0, type=float)
    parser.add_argument("--max-participation-rate", type=float)
    parser.add_argument("--min-trade-value", default=1.0, type=float)
    parser.add_argument("--max-asset-weight", default=1.0, type=float)
    parser.add_argument("--max-market-weight", default=1.0, type=float)
    parser.add_argument("--max-gross-exposure", default=1.0, type=float)
    parser.add_argument("--min-cash-weight", default=0.0, type=float)
    parser.add_argument("--periods-per-year", type=float)
    parser.add_argument("--max-drawdown-guard", type=float)
    parser.add_argument("--guard-cooldown-periods", default=0, type=int)
    parser.add_argument("--positions-csv")
    parser.add_argument("--output-dir", default="data/reports/paper_simulation")
    args = parser.parse_args()
    result = run_simulation(
        source=args.source,
        data_root=Path(args.data_root),
        market=args.market,
        factor_source=args.factor_source,
        factor_name=args.factor,
        factor_windows=_parse_windows(args.factor_windows),
        factor_input_root=Path(args.factor_input_root) if args.factor_input_root else None,
        moneyflow_input_root=Path(args.moneyflow_input_root) if args.moneyflow_input_root else None,
        top_n=args.top_n,
        rebalance_interval=args.rebalance_interval,
        start_date=args.start_date,
        end_date=args.end_date,
        initial_cash=args.initial_cash,
        commission_bps=args.commission_bps,
        slippage_bps=args.slippage_bps,
        market_impact_bps=args.market_impact_bps,
        max_participation_rate=args.max_participation_rate,
        min_trade_value=args.min_trade_value,
        max_asset_weight=args.max_asset_weight,
        max_market_weight=args.max_market_weight,
        max_gross_exposure=args.max_gross_exposure,
        min_cash_weight=args.min_cash_weight,
        periods_per_year=args.periods_per_year,
        max_drawdown_guard=args.max_drawdown_guard,
        guard_cooldown_periods=args.guard_cooldown_periods,
        positions_csv=Path(args.positions_csv) if args.positions_csv else None,
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "data_mode": result["data_mode"],
                "metrics": result["metrics"],
                "intents": len(result["intents"]),
                "fills": len(result["fills"]),
                "positions": len(result["positions"]),
                "equity_points": len(result["equity_curve"]),
                "guard_events": len(result["guard_events"]),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_bars(source: str, data_root: Path, market: str) -> pd.DataFrame:
    if source == "fixture":
        return load_demo_market_bars()
    if source != "processed-bars":
        raise ValueError(f"Unsupported simulation source: {source}")
    if market.upper() != "ALL":
        return load_processed_bars(data_root, market)
    frames = [load_processed_bars(data_root, item) for item in DEFAULT_MARKETS]
    return pd.concat(frames, ignore_index=True)


def _parse_windows(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


if __name__ == "__main__":
    main()
