from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.portfolio.rebalance import build_rebalance_plan
from quant_robot.signals.pipeline import SignalPipelineConfig, generate_signal_snapshot, write_signal_snapshot
from quant_robot.storage.processed_bars import load_processed_bars

DEFAULT_MARKETS = ("CN", "CN_ETF", "HK", "US", "CRYPTO")


def run_signal_snapshot(
    source: str = "fixture",
    data_root: str | Path = "data/processed",
    market: str = "ALL",
    factor_name: str = "momentum_2",
    factor_windows: tuple[int, ...] = (2, 3),
    top_n: int = 2,
    as_of_date: str | None = None,
    portfolio_scope: str | None = None,
    max_asset_weight: float = 1.0,
    max_market_weight: float = 1.0,
    max_gross_exposure: float = 1.0,
    min_cash_weight: float = 0.0,
    portfolio_value: float = 100000.0,
    positions_csv: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    bars = _load_bars(source, Path(data_root), market)
    snapshot = generate_signal_snapshot(
        bars,
        SignalPipelineConfig(
            factor_name=factor_name,
            factor_windows=factor_windows,
            market=market,
            as_of_date=as_of_date,
            top_n=top_n,
            portfolio_scope=portfolio_scope,
            max_asset_weight=max_asset_weight,
            max_market_weight=max_market_weight,
            max_gross_exposure=max_gross_exposure,
            min_cash_weight=min_cash_weight,
        ),
    )
    targets = pd.DataFrame(snapshot["targets"])
    current_positions = _load_positions(positions_csv)
    latest_prices = targets[["asset_id", "latest_price"]] if not targets.empty else pd.DataFrame(columns=["asset_id", "latest_price"])
    rebalance_plan = build_rebalance_plan(targets, current_positions, latest_prices, portfolio_value=portfolio_value)
    result = _sanitize({**snapshot, "portfolio_value": portfolio_value, "rebalance_plan": _records(rebalance_plan)})
    if output_dir is not None:
        output_path = Path(output_dir)
        write_signal_snapshot(result, output_path)
        rebalance_plan.to_csv(output_path / "rebalance_plan.csv", index=False)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a research-only signal snapshot and advisory rebalance plan.")
    parser.add_argument("--source", choices=["fixture", "processed-bars"], default="fixture")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--market", default="ALL")
    parser.add_argument("--factor", default="momentum_2")
    parser.add_argument("--factor-windows", default="2,3")
    parser.add_argument("--top-n", default=2, type=int)
    parser.add_argument("--as-of-date")
    parser.add_argument("--portfolio-scope", choices=["market", "global"])
    parser.add_argument("--max-asset-weight", default=1.0, type=float)
    parser.add_argument("--max-market-weight", default=1.0, type=float)
    parser.add_argument("--max-gross-exposure", default=1.0, type=float)
    parser.add_argument("--min-cash-weight", default=0.0, type=float)
    parser.add_argument("--portfolio-value", default=100000.0, type=float)
    parser.add_argument("--positions-csv")
    parser.add_argument("--output-dir", default="data/reports/signal_snapshot")
    args = parser.parse_args()
    result = run_signal_snapshot(
        source=args.source,
        data_root=Path(args.data_root),
        market=args.market,
        factor_name=args.factor,
        factor_windows=_parse_windows(args.factor_windows),
        top_n=args.top_n,
        as_of_date=args.as_of_date,
        portfolio_scope=args.portfolio_scope,
        max_asset_weight=args.max_asset_weight,
        max_market_weight=args.max_market_weight,
        max_gross_exposure=args.max_gross_exposure,
        min_cash_weight=args.min_cash_weight,
        portfolio_value=args.portfolio_value,
        positions_csv=Path(args.positions_csv) if args.positions_csv else None,
        output_dir=Path(args.output_dir),
    )
    print(
        json.dumps(
            {
                "data_mode": result["data_mode"],
                "as_of_date": result["as_of_date"],
                "signal_date": result["signal_date"],
                "target_gross_exposure": result["target_gross_exposure"],
                "cash_weight": result["cash_weight"],
                "targets": result["targets"],
                "rebalance_plan": result["rebalance_plan"],
            },
            indent=2,
            sort_keys=True,
        )
    )


def _load_positions(path: str | Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame(columns=["asset_id", "quantity"])
    return pd.read_csv(path)


def _load_bars(source: str, data_root: Path, market: str) -> pd.DataFrame:
    if source == "fixture":
        return load_demo_market_bars()
    if source != "processed-bars":
        raise ValueError(f"Unsupported signal source: {source}")
    if market.upper() != "ALL":
        return load_processed_bars(data_root, market)
    frames = [load_processed_bars(data_root, item) for item in DEFAULT_MARKETS]
    return pd.concat(frames, ignore_index=True)


def _parse_windows(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return frame.to_dict(orient="records")


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value


if __name__ == "__main__":
    main()
