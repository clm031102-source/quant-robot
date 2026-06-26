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
from quant_robot.ops.etf_liquid_universe import (
    ETFLiquidUniversePolicy,
    build_etf_liquid_universe,
    write_etf_liquid_universe,
)
from quant_robot.storage.processed_bars import load_processed_bars


def run_etf_liquid_universe_filter(
    *,
    source: str = "processed-bars",
    data_root: str | Path = "data/processed",
    market: str = "CN_ETF",
    output_dir: str | Path = "data/reports/etf_liquid_universe",
    start_date: str | None = None,
    end_date: str | None = None,
    min_history_days: int = ETFLiquidUniversePolicy.min_history_days,
    recent_window_days: int = ETFLiquidUniversePolicy.recent_window_days,
    min_recent_observations: int = ETFLiquidUniversePolicy.min_recent_observations,
    min_recent_amount: float = ETFLiquidUniversePolicy.min_recent_amount,
    max_stale_price_rate: float = ETFLiquidUniversePolicy.max_stale_price_rate,
    max_extreme_return_rate: float = ETFLiquidUniversePolicy.max_extreme_return_rate,
    extreme_return_threshold: float = ETFLiquidUniversePolicy.extreme_return_threshold,
    min_selected_assets: int = ETFLiquidUniversePolicy.min_selected_assets,
    required_asset_ids: tuple[str, ...] = ETFLiquidUniversePolicy.required_asset_ids,
) -> dict[str, object]:
    bars = _load_bars(source=source, data_root=Path(data_root), market=market)
    packet = build_etf_liquid_universe(
        bars,
        market=market,
        start_date=start_date,
        end_date=end_date,
        policy=ETFLiquidUniversePolicy(
            min_history_days=min_history_days,
            recent_window_days=recent_window_days,
            min_recent_observations=min_recent_observations,
            min_recent_amount=min_recent_amount,
            max_stale_price_rate=max_stale_price_rate,
            max_extreme_return_rate=max_extreme_return_rate,
            extreme_return_threshold=extreme_return_threshold,
            min_selected_assets=min_selected_assets,
            required_asset_ids=tuple(required_asset_ids),
        ),
    )
    write_etf_liquid_universe(output_dir, packet)
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a liquid-continuous CN ETF universe before factor mining.")
    parser.add_argument("--source", choices=["fixture", "processed-bars"], default="processed-bars")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--market", default="CN_ETF")
    parser.add_argument("--output-dir", default="data/reports/etf_liquid_universe")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--min-history-days", type=int, default=ETFLiquidUniversePolicy.min_history_days)
    parser.add_argument("--recent-window-days", type=int, default=ETFLiquidUniversePolicy.recent_window_days)
    parser.add_argument("--min-recent-observations", type=int, default=ETFLiquidUniversePolicy.min_recent_observations)
    parser.add_argument("--min-recent-amount", type=float, default=ETFLiquidUniversePolicy.min_recent_amount)
    parser.add_argument("--max-stale-price-rate", type=float, default=ETFLiquidUniversePolicy.max_stale_price_rate)
    parser.add_argument("--max-extreme-return-rate", type=float, default=ETFLiquidUniversePolicy.max_extreme_return_rate)
    parser.add_argument("--extreme-return-threshold", type=float, default=ETFLiquidUniversePolicy.extreme_return_threshold)
    parser.add_argument("--min-selected-assets", type=int, default=ETFLiquidUniversePolicy.min_selected_assets)
    parser.add_argument("--required-asset-id", dest="required_asset_ids", action="append", default=[])
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="Exit successfully while still writing the blocked universe packet.",
    )
    args = parser.parse_args()
    packet = run_etf_liquid_universe_filter(
        source=args.source,
        data_root=Path(args.data_root),
        market=args.market,
        output_dir=Path(args.output_dir),
        start_date=args.start_date,
        end_date=args.end_date,
        min_history_days=args.min_history_days,
        recent_window_days=args.recent_window_days,
        min_recent_observations=args.min_recent_observations,
        min_recent_amount=args.min_recent_amount,
        max_stale_price_rate=args.max_stale_price_rate,
        max_extreme_return_rate=args.max_extreme_return_rate,
        extreme_return_threshold=args.extreme_return_threshold,
        min_selected_assets=args.min_selected_assets,
        required_asset_ids=tuple(args.required_asset_ids),
    )
    print(
        json.dumps(
            {"status": packet["status"], "summary": packet["summary"], "decision": packet["decision"]},
            indent=2,
            sort_keys=True,
        )
    )
    if packet["status"] != "cleared" and not args.allow_blocked:
        raise SystemExit("ETF liquid universe filter blocked this run")


def _load_bars(*, source: str, data_root: Path, market: str):
    if source == "fixture":
        return load_demo_market_bars()
    if source == "processed-bars":
        return load_processed_bars(data_root, market.upper())
    raise ValueError(f"Unsupported ETF universe source: {source}")


if __name__ == "__main__":
    main()
