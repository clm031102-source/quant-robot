from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.storage.processed_bars import load_processed_bars
from quant_robot.validation.walk_forward import load_walk_forward_config, run_walk_forward_validation


def run_walk_forward(
    config_path: str | Path = "configs/walk_forward.json",
    source: str = "fixture",
    data_root: str | Path = "data/processed",
    output_dir: str | Path | None = None,
) -> dict[str, object]:
    config = load_walk_forward_config(config_path)
    if output_dir is not None:
        config = replace(config, output_dir=Path(output_dir))
    bars = _load_bars(source, Path(data_root), config.experiment_grid.markets)
    return run_walk_forward_validation(bars, config)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local walk-forward validation for experiment candidates.")
    parser.add_argument("--config", default="configs/walk_forward.json")
    parser.add_argument("--source", choices=["fixture", "processed-bars"], default="fixture")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    result = run_walk_forward(
        config_path=Path(args.config),
        source=args.source,
        data_root=Path(args.data_root),
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    print(json.dumps({"summary": result["summary"], "top": result["leaderboard"][:10]}, indent=2, sort_keys=True))


def _load_bars(source: str, data_root: Path, markets: tuple[str, ...]) -> pd.DataFrame:
    if source == "fixture":
        return load_demo_market_bars()
    if source != "processed-bars":
        raise ValueError(f"Unsupported walk-forward source: {source}")
    frames = [load_processed_bars(data_root, market) for market in markets if market.upper() != "ALL"]
    if not frames:
        raise ValueError("processed-bars source requires at least one specific market")
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    main()
