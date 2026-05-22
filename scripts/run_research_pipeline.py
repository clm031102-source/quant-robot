from __future__ import annotations

import argparse
import json
from pathlib import Path

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.research.pipeline import ResearchPipelineConfig, run_research_pipeline
from quant_robot.storage.processed_bars import load_processed_bars


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a configurable local research/backtest pipeline.")
    parser.add_argument("--source", choices=["fixture", "processed-bars"], default="fixture")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--market", default="ALL")
    parser.add_argument("--factor", default="momentum_2")
    parser.add_argument("--factor-windows", default="2,3")
    parser.add_argument("--top-n", default=2, type=int)
    parser.add_argument("--cost-bps", default=5.0, type=float)
    parser.add_argument("--forward-horizon", default=1, type=int)
    parser.add_argument("--execution-lag", default=1, type=int)
    parser.add_argument("--portfolio-scope", choices=["market", "global"])
    parser.add_argument("--periods-per-year", type=int)
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--signal-start-date")
    parser.add_argument("--signal-end-date")
    parser.add_argument("--output-dir", default="data/reports/research_pipeline")
    args = parser.parse_args()
    bars = load_demo_market_bars() if args.source == "fixture" else load_processed_bars(Path(args.data_root), args.market)
    config = ResearchPipelineConfig(
        factor_name=args.factor,
        factor_windows=_parse_windows(args.factor_windows),
        market=args.market,
        start_date=args.start_date,
        end_date=args.end_date,
        forward_horizon=args.forward_horizon,
        execution_lag=args.execution_lag,
        top_n=args.top_n,
        cost_bps=args.cost_bps,
        portfolio_scope=args.portfolio_scope,
        periods_per_year=args.periods_per_year,
        signal_start_date=args.signal_start_date,
        signal_end_date=args.signal_end_date,
        output_dir=Path(args.output_dir),
    )
    result = run_research_pipeline(bars, config)
    print(json.dumps({"request": result["request"], "metrics": result["metrics"], "artifact_rows": result["artifact_rows"]}, indent=2, sort_keys=True))


def _parse_windows(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


if __name__ == "__main__":
    main()
