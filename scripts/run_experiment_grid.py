from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.experiments.runner import ExperimentGridConfig, load_experiment_grid_config, run_experiment_grid
from quant_robot.storage.processed_bars import load_processed_bars


def run_grid(
    config_path: str | Path | None = None,
    source: str = "fixture",
    data_root: str | Path = "data/processed",
    output_dir: str | Path | None = None,
) -> dict[str, object]:
    config = load_experiment_grid_config(config_path) if config_path is not None else ExperimentGridConfig()
    if output_dir is not None:
        config = replace(config, output_dir=Path(output_dir))
    bars = _load_bars(source, Path(data_root), config.markets)
    return run_experiment_grid(bars, config)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local batch experiment grid and write a strategy leaderboard.")
    parser.add_argument("--config", default="configs/experiment_grid.json")
    parser.add_argument("--source", choices=["fixture", "processed-bars"], default="fixture")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    result = run_grid(
        config_path=Path(args.config),
        source=args.source,
        data_root=Path(args.data_root),
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    print(json.dumps({"summary": result["summary"], "top": result["leaderboard"][:10]}, indent=2, sort_keys=True))
    try:
        assert_grid_succeeded(result)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


def assert_grid_succeeded(result: dict[str, object]) -> None:
    summary = result.get("summary", {})
    if not isinstance(summary, dict):
        raise RuntimeError("experiment grid failed: missing summary")
    failed = int(summary.get("failed", 0))
    completed = int(summary.get("completed", 0))
    if failed:
        leaderboard = result.get("leaderboard", [])
        if not isinstance(leaderboard, list):
            leaderboard = []
        failures = [
            f"{row.get('case_id')}: {row.get('error')}"
            for row in leaderboard
            if isinstance(row, dict) and row.get("status") == "failed"
        ]
        detail = "; ".join(failures[:5])
        raise RuntimeError(f"experiment grid failed: {failed} failed case(s)" + (f" ({detail})" if detail else ""))
    if completed == 0:
        raise RuntimeError("experiment grid failed: no completed experiment cases")


def _load_bars(source: str, data_root: Path, markets: tuple[str, ...]) -> pd.DataFrame:
    if source == "fixture":
        return load_demo_market_bars()
    if source != "processed-bars":
        raise ValueError(f"Unsupported experiment source: {source}")
    frames = [load_processed_bars(data_root, market) for market in markets if market.upper() != "ALL"]
    if not frames:
        raise ValueError("processed-bars source requires at least one specific market")
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    main()
