from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.research.pipeline import ResearchPipelineConfig, run_research_pipeline
from quant_robot.storage.processed_bars import load_processed_bars

DEFAULT_MARKETS = ("CN", "CN_ETF", "HK", "US", "CRYPTO")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a configurable local research/backtest pipeline.")
    parser.add_argument("--source", choices=["fixture", "processed-bars"], default="fixture")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--market", default="ALL")
    parser.add_argument("--factor", default="momentum_2")
    parser.add_argument(
        "--factor-source",
        choices=["technical", "tushare_daily_basic", "tushare_moneyflow", "moneyflow_technical_combo", "combined"],
        default="technical",
    )
    parser.add_argument("--factor-windows", default="2,3")
    parser.add_argument("--factor-input-root")
    parser.add_argument("--factor-input-required", action="store_true")
    parser.add_argument("--moneyflow-input-root")
    parser.add_argument("--top-n", default=2, type=int)
    parser.add_argument("--cost-bps", default=5.0, type=float)
    parser.add_argument("--forward-horizon", default=1, type=int)
    parser.add_argument("--execution-lag", default=1, type=int)
    parser.add_argument("--rebalance-interval", default=1, type=int)
    parser.add_argument("--portfolio-scope", choices=["market", "global"])
    parser.add_argument("--periods-per-year", type=float)
    parser.add_argument("--benchmark-asset-id")
    parser.add_argument("--cash-annual-return", default=0.0, type=float)
    parser.add_argument("--regime-filter", action="store_true")
    parser.add_argument("--regime-lookback", default=20, type=int)
    parser.add_argument("--min-relative-return", type=float)
    parser.add_argument("--max-drawdown-limit", type=float)
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--signal-start-date")
    parser.add_argument("--signal-end-date")
    parser.add_argument("--output-dir", default="data/reports/research_pipeline")
    args = parser.parse_args()
    bars = load_research_bars(args.source, Path(args.data_root), args.market)
    config = build_research_config(args)
    result = run_research_pipeline(bars, config)
    print(
        json.dumps(
            {
                "request": result["request"],
                "metrics": result["metrics"],
                "benchmark_metrics": result["benchmark_metrics"],
                "decision": result["decision"],
                "artifact_rows": result["artifact_rows"],
            },
            indent=2,
            sort_keys=True,
        )
    )


def _parse_windows(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def build_research_config(args: argparse.Namespace) -> ResearchPipelineConfig:
    return ResearchPipelineConfig(
        factor_name=args.factor,
        factor_source=args.factor_source,
        factor_windows=_parse_windows(args.factor_windows),
        factor_input_root=Path(args.factor_input_root) if args.factor_input_root else None,
        factor_input_required=args.factor_input_required,
        moneyflow_input_root=Path(args.moneyflow_input_root) if args.moneyflow_input_root else None,
        market=args.market,
        start_date=args.start_date,
        end_date=args.end_date,
        forward_horizon=args.forward_horizon,
        execution_lag=args.execution_lag,
        rebalance_interval=args.rebalance_interval,
        top_n=args.top_n,
        cost_bps=args.cost_bps,
        portfolio_scope=args.portfolio_scope,
        periods_per_year=args.periods_per_year,
        benchmark_asset_id=args.benchmark_asset_id,
        cash_annual_return=args.cash_annual_return,
        regime_filter=args.regime_filter,
        regime_lookback=args.regime_lookback,
        min_relative_return=args.min_relative_return,
        max_drawdown_limit=args.max_drawdown_limit,
        signal_start_date=args.signal_start_date,
        signal_end_date=args.signal_end_date,
        output_dir=Path(args.output_dir),
    )


def load_research_bars(source: str, data_root: Path, market: str) -> object:
    if source == "fixture":
        return load_demo_market_bars()
    if source != "processed-bars":
        raise ValueError(f"Unsupported research source: {source}")
    market_upper = market.upper()
    if market_upper != "ALL":
        return load_processed_bars(data_root, market_upper)
    import pandas as pd

    frames = [load_processed_bars(data_root, item) for item in DEFAULT_MARKETS]
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    main()
