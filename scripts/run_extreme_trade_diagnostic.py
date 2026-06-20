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
from quant_robot.experiments.runner import ExperimentGridConfig, load_experiment_grid_config
from quant_robot.ops.cn_stock_data_manifest import validate_cn_stock_data_manifest_packet
from quant_robot.ops.extreme_trade_diagnostic import (
    DEFAULT_EXTREME_TRADE_THRESHOLD,
    diagnose_extreme_trades,
    write_extreme_trade_diagnostic,
)
from quant_robot.ops.factor_mining_startup import validate_cleared_startup_gate_packet
from quant_robot.research.pipeline import ResearchPipelineConfig, run_research_pipeline
from quant_robot.storage.authority_bars import load_authority_processed_bars_from_config
from quant_robot.storage.processed_bars import load_processed_bars


def run_extreme_trade_diagnostic_from_config(
    *,
    config_path: str | Path,
    factor_name: str,
    source: str = "fixture",
    data_root: str | Path = "data/processed",
    output_dir: str | Path,
    market: str | None = None,
    top_n: int | None = None,
    cost_bps: float | None = None,
    rebalance_interval: int | None = None,
    threshold: float = DEFAULT_EXTREME_TRADE_THRESHOLD,
    diagnostic_top_n: int = 20,
    authority_bars_config: str | Path | None = Path("configs/cn_stock_authority_bars_2015_2025.json"),
    startup_gate_packet: str | Path | None = Path("data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json"),
    data_manifest_packet: str | Path | None = Path("data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json"),
    allow_review_required_data_manifest: bool = False,
) -> dict[str, Any]:
    grid = load_experiment_grid_config(config_path)
    resolved_market = market or _first_market(grid)
    _enforce_cn_stock_inputs(
        source=source,
        markets=(resolved_market,),
        startup_gate_packet=startup_gate_packet,
        data_manifest_packet=data_manifest_packet,
        data_root=Path(data_root),
        allow_review_required_data_manifest=allow_review_required_data_manifest,
    )
    bars = _load_bars(
        source=source,
        data_root=Path(data_root),
        markets=(resolved_market,),
        authority_bars_config=authority_bars_config,
    )
    pipeline_config = _pipeline_config(
        grid,
        factor_name=factor_name,
        market=resolved_market,
        top_n=top_n,
        cost_bps=cost_bps,
        rebalance_interval=rebalance_interval,
    )
    result = run_research_pipeline(bars, pipeline_config)
    diagnostic = diagnose_extreme_trades(
        pd.DataFrame(result["trades"]),
        bars,
        threshold=threshold,
        top_n=diagnostic_top_n,
    )
    diagnostic["request"] = {
        "config_path": str(config_path),
        "factor_name": factor_name,
        "factor_source": grid.factor_source,
        "market": resolved_market,
        "top_n": pipeline_config.top_n,
        "cost_bps": pipeline_config.cost_bps,
        "rebalance_interval": pipeline_config.rebalance_interval,
        "forward_horizon": pipeline_config.forward_horizon,
        "execution_lag": pipeline_config.execution_lag,
        "threshold": threshold,
    }
    write_extreme_trade_diagnostic(output_dir, diagnostic)
    return diagnostic


def _pipeline_config(
    grid: ExperimentGridConfig,
    *,
    factor_name: str,
    market: str,
    top_n: int | None,
    cost_bps: float | None,
    rebalance_interval: int | None,
) -> ResearchPipelineConfig:
    return ResearchPipelineConfig(
        factor_name=factor_name,
        factor_source=grid.factor_source,
        factor_windows=grid.factor_windows,
        factor_input_root=grid.factor_input_root,
        factor_input_required=grid.factor_input_required,
        moneyflow_input_root=grid.moneyflow_input_root,
        market=market,
        start_date=grid.start_date,
        end_date=grid.end_date,
        forward_horizon=grid.forward_horizon,
        execution_lag=grid.execution_lag,
        rebalance_interval=rebalance_interval if rebalance_interval is not None else _first(grid.rebalance_intervals),
        quantiles=grid.quantiles,
        top_n=top_n if top_n is not None else _first(grid.top_n_values),
        cost_bps=cost_bps if cost_bps is not None else _first(grid.cost_bps_values),
        portfolio_scope=grid.portfolio_scope,
        periods_per_year=grid.periods_per_year,
        benchmark_asset_id=grid.benchmark_asset_id,
        cash_annual_return=grid.cash_annual_return,
        regime_filter=grid.regime_filter,
        regime_lookback=_first(grid.regime_lookback_values) if grid.regime_lookback_values else grid.regime_lookback,
        target_gross_exposure=grid.target_gross_exposure,
        commission_bps=grid.commission_bps,
        slippage_bps=grid.slippage_bps,
        market_impact_bps=grid.market_impact_bps,
        max_participation_rate=grid.max_participation_rate,
        portfolio_value=grid.portfolio_value,
        min_relative_return=grid.min_relative_return,
        max_drawdown_limit=grid.max_drawdown_limit,
        signal_start_date=grid.signal_start_date,
        signal_end_date=grid.signal_end_date,
        output_dir=None,
    )


def _load_bars(
    *,
    source: str,
    data_root: Path,
    markets: tuple[str, ...],
    authority_bars_config: str | Path | None,
) -> pd.DataFrame:
    if source == "fixture":
        return load_demo_market_bars()
    if source == "authority-processed-bars":
        if authority_bars_config is None:
            raise ValueError("authority_bars_config is required for authority-processed-bars source")
        return load_authority_processed_bars_from_config(authority_bars_config, markets=markets)
    if source == "processed-bars":
        if data_root.is_file():
            return load_authority_processed_bars_from_config(data_root, markets=markets)
        frames = [load_processed_bars(data_root, market) for market in markets if market.upper() != "ALL"]
        if not frames:
            raise ValueError("processed-bars source requires at least one specific market")
        return pd.concat(frames, ignore_index=True)
    raise ValueError(f"Unsupported source: {source}")


def _enforce_cn_stock_inputs(
    *,
    source: str,
    markets: tuple[str, ...],
    startup_gate_packet: str | Path | None,
    data_manifest_packet: str | Path | None,
    data_root: Path,
    allow_review_required_data_manifest: bool,
) -> None:
    if source not in {"processed-bars", "authority-processed-bars"} or not any(market.upper() == "CN" for market in markets):
        return
    validate_cleared_startup_gate_packet(
        startup_gate_packet,
        context="CN extreme trade diagnostic",
    )
    validate_cn_stock_data_manifest_packet(
        data_manifest_packet,
        expected_source_root=data_root,
        allow_review_required=allow_review_required_data_manifest,
        context="CN extreme trade diagnostic",
    )


def _first_market(grid: ExperimentGridConfig) -> str:
    for market in grid.markets:
        if market.upper() != "ALL":
            return market.upper()
    raise ValueError("diagnostic requires a specific market")


def _first(values):
    return next(iter(values))


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose extreme trade returns for one experiment-grid candidate.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--factor-name", required=True)
    parser.add_argument("--source", choices=["fixture", "processed-bars", "authority-processed-bars"], default="fixture")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--market")
    parser.add_argument("--top-n", type=int)
    parser.add_argument("--cost-bps", type=float)
    parser.add_argument("--rebalance-interval", type=int)
    parser.add_argument("--threshold", type=float, default=DEFAULT_EXTREME_TRADE_THRESHOLD)
    parser.add_argument("--diagnostic-top-n", type=int, default=20)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--authority-bars-config", default="configs/cn_stock_authority_bars_2015_2025.json")
    parser.add_argument("--startup-gate-packet", default="data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json")
    parser.add_argument("--data-manifest-packet", default="data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json")
    parser.add_argument("--allow-review-required-data-manifest", action="store_true")
    args = parser.parse_args()
    diagnostic = run_extreme_trade_diagnostic_from_config(
        config_path=Path(args.config),
        factor_name=args.factor_name,
        source=args.source,
        data_root=Path(args.data_root),
        output_dir=Path(args.output_dir),
        market=args.market,
        top_n=args.top_n,
        cost_bps=args.cost_bps,
        rebalance_interval=args.rebalance_interval,
        threshold=args.threshold,
        diagnostic_top_n=args.diagnostic_top_n,
        authority_bars_config=Path(args.authority_bars_config) if args.authority_bars_config else None,
        startup_gate_packet=Path(args.startup_gate_packet) if args.startup_gate_packet else None,
        data_manifest_packet=Path(args.data_manifest_packet) if args.data_manifest_packet else None,
        allow_review_required_data_manifest=args.allow_review_required_data_manifest,
    )
    print(json.dumps({"summary": diagnostic["summary"], "output_dir": str(Path(args.output_dir))}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
