from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.experiments.runner import ExperimentGridConfig, load_experiment_grid_config, run_experiment_grid
from quant_robot.ops.cn_stock_data_manifest import validate_cn_stock_data_manifest_packet
from quant_robot.ops.factor_mining_candidate_plan_gate import validate_candidate_plan_gate_packet
from quant_robot.ops.factor_mining_startup import validate_cleared_startup_gate_packet
from quant_robot.storage.authority_bars import load_authority_processed_bars_from_config
from quant_robot.storage.processed_bars import load_processed_bars


def run_grid(
    config_path: str | Path | None = None,
    source: str = "fixture",
    data_root: str | Path = "data/processed",
    output_dir: str | Path | None = None,
    startup_gate_packet: str | Path | None = Path("data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json"),
    data_manifest_packet: str | Path | None = Path("data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json"),
    candidate_plan_gate_packet: str | Path | None = Path("data/reports/factor_mining_candidate_plan_gate/factor_mining_candidate_plan_gate.json"),
    authority_bars_config: str | Path | None = Path("configs/cn_stock_authority_bars_2015_2025.json"),
    allow_missing_startup_gate: bool = False,
    allow_review_required_data_manifest: bool = False,
    progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, object]:
    config = load_experiment_grid_config(config_path) if config_path is not None else ExperimentGridConfig()
    if output_dir is not None:
        config = replace(config, output_dir=Path(output_dir))
    _enforce_cn_stock_startup_gate(
        source=source,
        markets=config.markets,
        startup_gate_packet=startup_gate_packet,
        data_manifest_packet=data_manifest_packet,
        candidate_plan_gate_packet=candidate_plan_gate_packet,
        allow_missing_startup_gate=allow_missing_startup_gate,
        allow_review_required_data_manifest=allow_review_required_data_manifest,
        data_root=Path(data_root),
    )
    _emit_progress(
        progress,
        "load_bars_start",
        source=source,
        data_root=str(data_root),
        markets=list(config.markets),
    )
    bars = _load_bars(source, Path(data_root), config.markets, authority_bars_config=authority_bars_config)
    _emit_progress(
        progress,
        "load_bars_done",
        source=source,
        data_root=str(data_root),
        markets=list(config.markets),
        bar_rows=len(bars),
    )
    _enforce_authority_bar_year_coverage(source=source, bars=bars, config=config)
    return run_experiment_grid(bars, config, progress=progress)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local batch experiment grid and write a strategy leaderboard.")
    parser.add_argument("--config", default="configs/experiment_grid.json")
    parser.add_argument("--source", choices=["fixture", "processed-bars", "authority-processed-bars"], default="fixture")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--output-dir")
    parser.add_argument(
        "--authority-bars-config",
        default="configs/cn_stock_authority_bars_2015_2025.json",
        help="Authority processed-bars segment config used by authority-processed-bars source.",
    )
    parser.add_argument(
        "--startup-gate-packet",
        default="data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json",
        help="Cleared CN stock factor-mining startup gate packet required for processed CN grids.",
    )
    parser.add_argument(
        "--allow-missing-startup-gate",
        action="store_true",
        help="Deprecated. CN processed-bars grids cannot bypass the startup gate.",
    )
    parser.add_argument(
        "--data-manifest-packet",
        default="data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json",
        help="CN stock data manifest packet required for processed CN grids.",
    )
    parser.add_argument(
        "--candidate-plan-gate-packet",
        default="data/reports/factor_mining_candidate_plan_gate/factor_mining_candidate_plan_gate.json",
        help="Cleared CN stock candidate plan gate packet required before processed CN experiment grids.",
    )
    parser.add_argument(
        "--allow-review-required-data-manifest",
        action="store_true",
        help="Allow a reviewed CN stock data manifest that has warnings but no blockers.",
    )
    args = parser.parse_args()
    result = run_grid(
        config_path=Path(args.config),
        source=args.source,
        data_root=Path(args.data_root),
        output_dir=Path(args.output_dir) if args.output_dir else None,
        startup_gate_packet=Path(args.startup_gate_packet) if args.startup_gate_packet else None,
        data_manifest_packet=Path(args.data_manifest_packet) if args.data_manifest_packet else None,
        candidate_plan_gate_packet=Path(args.candidate_plan_gate_packet) if args.candidate_plan_gate_packet else None,
        authority_bars_config=Path(args.authority_bars_config) if args.authority_bars_config else None,
        allow_missing_startup_gate=args.allow_missing_startup_gate,
        allow_review_required_data_manifest=args.allow_review_required_data_manifest,
        progress=_stderr_progress,
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


def _stderr_progress(event: dict[str, Any]) -> None:
    print(json.dumps(event, sort_keys=True), file=sys.stderr, flush=True)


def _emit_progress(
    progress: Callable[[dict[str, Any]], None] | None,
    event: str,
    **fields: Any,
) -> None:
    if progress is None:
        return
    progress({"event": event, **fields})


def _load_bars(
    source: str,
    data_root: Path,
    markets: tuple[str, ...],
    *,
    authority_bars_config: str | Path | None,
) -> pd.DataFrame:
    if source == "fixture":
        return load_demo_market_bars()
    if source == "authority-processed-bars":
        if authority_bars_config is None:
            raise ValueError("authority_bars_config is required for authority-processed-bars source")
        return load_authority_processed_bars_from_config(authority_bars_config, markets=markets)
    if source != "processed-bars":
        raise ValueError(f"Unsupported experiment source: {source}")
    frames = [load_processed_bars(data_root, market) for market in markets if market.upper() != "ALL"]
    if not frames:
        raise ValueError("processed-bars source requires at least one specific market")
    return pd.concat(frames, ignore_index=True)


def _enforce_authority_bar_year_coverage(
    *,
    source: str,
    bars: pd.DataFrame,
    config: ExperimentGridConfig,
) -> None:
    if source != "authority-processed-bars" or not config.start_date or not config.end_date:
        return
    if "date" not in bars.columns:
        raise ValueError("authority-processed-bars missing date column for year coverage check")
    required_years = set(range(pd.to_datetime(config.start_date).year, pd.to_datetime(config.end_date).year + 1))
    actual_years = set(pd.to_datetime(bars["date"], errors="coerce").dropna().dt.year.astype(int).unique())
    missing = sorted(required_years - actual_years)
    if missing:
        raise ValueError(
            "authority-processed-bars missing required years: "
            + ", ".join(str(year) for year in missing)
        )


def _enforce_cn_stock_startup_gate(
    *,
    source: str,
    markets: tuple[str, ...],
    startup_gate_packet: str | Path | None,
    data_manifest_packet: str | Path | None,
    candidate_plan_gate_packet: str | Path | None,
    allow_missing_startup_gate: bool,
    allow_review_required_data_manifest: bool,
    data_root: Path,
) -> None:
    if source not in {"processed-bars", "authority-processed-bars"} or not any(market.upper() == "CN" for market in markets):
        return
    if allow_missing_startup_gate:
        raise ValueError("CN processed-bars experiment grid startup gate cannot be bypassed")
    validate_cleared_startup_gate_packet(
        startup_gate_packet,
        context="CN processed-bars experiment grid",
    )
    validate_cn_stock_data_manifest_packet(
        data_manifest_packet,
        expected_source_root=data_root,
        allow_review_required=allow_review_required_data_manifest,
        context="CN processed-bars experiment grid",
    )
    validate_candidate_plan_gate_packet(
        candidate_plan_gate_packet,
        context="CN processed-bars experiment grid",
    )


if __name__ == "__main__":
    main()
