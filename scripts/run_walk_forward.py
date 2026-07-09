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
from quant_robot.experiments.runner import ExperimentGridConfig
from quant_robot.ops.cn_stock_data_manifest import validate_cn_stock_data_manifest_packet
from quant_robot.ops.factor_batch_readiness_gate import validate_factor_batch_readiness_gate_packet
from quant_robot.ops.factor_mining_startup import validate_cleared_startup_gate_packet
from quant_robot.storage.processed_bars import load_processed_bars
from quant_robot.validation.walk_forward import load_walk_forward_config, run_walk_forward_validation


def run_walk_forward(
    config_path: str | Path = "configs/walk_forward.json",
    source: str = "fixture",
    data_root: str | Path = "data/processed",
    output_dir: str | Path | None = None,
    startup_gate_packet: str | Path | None = Path("data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json"),
    data_manifest_packet: str | Path | None = Path("data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json"),
    factor_batch_readiness_gate_packet: str | Path | None = Path(
        "data/reports/factor_batch_readiness_gate/factor_batch_readiness_gate.json"
    ),
    allow_review_required_data_manifest: bool = False,
) -> dict[str, object]:
    config = load_walk_forward_config(config_path)
    if output_dir is not None:
        config = replace(config, output_dir=Path(output_dir))
    experiment_grid = _attach_processed_cn_etf_rotation_membership(config.experiment_grid, source, Path(data_root))
    if experiment_grid is not config.experiment_grid:
        config = replace(config, experiment_grid=experiment_grid)
    _enforce_cn_stock_walk_forward_inputs(
        source=source,
        markets=config.experiment_grid.markets,
        startup_gate_packet=startup_gate_packet,
        data_manifest_packet=data_manifest_packet,
        factor_batch_readiness_gate_packet=factor_batch_readiness_gate_packet,
        data_root=Path(data_root),
        allow_review_required_data_manifest=allow_review_required_data_manifest,
    )
    bars = _load_bars(source, Path(data_root), config.experiment_grid.markets)
    return run_walk_forward_validation(bars, config)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local walk-forward validation for experiment candidates.")
    parser.add_argument("--config", default="configs/walk_forward.json")
    parser.add_argument("--source", choices=["fixture", "processed-bars"], default="fixture")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--output-dir")
    parser.add_argument("--startup-gate-packet", default="data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json")
    parser.add_argument("--data-manifest-packet", default="data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json")
    parser.add_argument(
        "--factor-batch-readiness-gate-packet",
        default="data/reports/factor_batch_readiness_gate/factor_batch_readiness_gate.json",
    )
    parser.add_argument("--allow-review-required-data-manifest", action="store_true")
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
        startup_gate_packet=Path(args.startup_gate_packet) if args.startup_gate_packet else None,
        data_manifest_packet=Path(args.data_manifest_packet) if args.data_manifest_packet else None,
        factor_batch_readiness_gate_packet=Path(args.factor_batch_readiness_gate_packet)
        if args.factor_batch_readiness_gate_packet
        else None,
        allow_review_required_data_manifest=args.allow_review_required_data_manifest,
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
    frames = [load_processed_bars(data_root, market) for market in markets if market.upper() != "ALL"]
    if not frames:
        raise ValueError("processed-bars source requires at least one specific market")
    return pd.concat(frames, ignore_index=True)


def _enforce_cn_stock_walk_forward_inputs(
    *,
    source: str,
    markets: tuple[str, ...],
    startup_gate_packet: str | Path | None,
    data_manifest_packet: str | Path | None,
    factor_batch_readiness_gate_packet: str | Path | None,
    data_root: Path,
    allow_review_required_data_manifest: bool,
) -> None:
    if source != "processed-bars" or not any(market.upper() == "CN" for market in markets):
        return
    validate_cleared_startup_gate_packet(
        startup_gate_packet,
        context="CN walk-forward validation",
    )
    validate_cn_stock_data_manifest_packet(
        data_manifest_packet,
        expected_source_root=data_root,
        allow_review_required=allow_review_required_data_manifest,
        context="CN walk-forward validation",
    )
    validate_factor_batch_readiness_gate_packet(
        factor_batch_readiness_gate_packet,
        context="CN walk-forward validation",
    )


def _attach_processed_cn_etf_rotation_membership(
    config: ExperimentGridConfig,
    source: str,
    data_root: Path,
) -> ExperimentGridConfig:
    if source != "processed-bars":
        return config
    markets = {market.upper() for market in config.markets}
    if "CN_ETF" not in markets:
        return config
    return replace(
        config,
        rotation_membership_root=config.rotation_membership_root or data_root,
        rotation_membership_required=True,
    )


if __name__ == "__main__":
    main()
