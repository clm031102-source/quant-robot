from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.storage.authority_bars import load_authority_processed_bars_from_config
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
    parser.add_argument(
        "--allow-no-accepted",
        action="store_true",
        help="Exit successfully when validation completes but every candidate is rejected.",
    )
    args = parser.parse_args()
    result = run_walk_forward(
        config_path=Path(args.config),
        source=args.source,
        data_root=Path(args.data_root),
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    print(json.dumps({"summary": result["summary"], "top": result["leaderboard"][:10]}, indent=2, sort_keys=True))
    try:
        assert_walk_forward_succeeded(result, allow_no_accepted=args.allow_no_accepted)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


def assert_walk_forward_succeeded(result: dict[str, object], *, allow_no_accepted: bool = False) -> None:
    summary = result.get("summary", {})
    if not isinstance(summary, dict):
        raise RuntimeError("walk-forward validation failed: missing summary")
    leaderboard = result.get("leaderboard", [])
    if not isinstance(leaderboard, list):
        leaderboard = []
    failed_rows = [
        row
        for row in leaderboard
        if isinstance(row, dict) and _has_failed_grid_status(row)
    ]
    if failed_rows:
        cases = ", ".join(str(row.get("case_id")) for row in failed_rows[:5])
        raise RuntimeError(f"walk-forward grid failures: {cases}")
    if int(summary.get("accepted", 0)) == 0 and not allow_no_accepted:
        raise RuntimeError("walk-forward validation failed: no accepted walk-forward cases")


def _has_failed_grid_status(row: dict[str, object]) -> bool:
    statuses = {row.get("train_status"), row.get("test_status")}
    return "failed" in statuses or "missing" in statuses


def _load_bars(source: str, data_root: Path, markets: tuple[str, ...]) -> pd.DataFrame:
    if source == "fixture":
        return load_demo_market_bars()
    if source != "processed-bars":
        raise ValueError(f"Unsupported walk-forward source: {source}")
    if data_root.is_file():
        return load_authority_processed_bars_from_config(data_root, markets)
    frames = [load_processed_bars(data_root, market) for market in markets if market.upper() != "ALL"]
    if not frames:
        raise ValueError("processed-bars source requires at least one specific market")
    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    main()
