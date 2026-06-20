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
from quant_robot.experiments.runner import load_experiment_grid_config
from quant_robot.ops.cn_stock_data_manifest import validate_cn_stock_data_manifest_packet
from quant_robot.ops.factor_mining_startup import validate_cleared_startup_gate_packet
from quant_robot.ops.same_parameter_replay import run_same_parameter_full_sample_replay
from quant_robot.storage.authority_bars import load_authority_processed_bars_from_config
from quant_robot.storage.processed_bars import load_processed_bars
from quant_robot.validation.walk_forward import load_walk_forward_config


DEFAULT_START_DATE = "2015-01-01"
DEFAULT_END_DATE = "2025-12-31"


def run_same_parameter_full_sample_replay_from_files(
    *,
    candidates_csv: str | Path,
    base_config_path: str | Path,
    source: str,
    data_root: str | Path,
    output_dir: str | Path,
    start_date: str = DEFAULT_START_DATE,
    end_date: str = DEFAULT_END_DATE,
    authority_bars_config: str | Path | None = Path("configs/cn_stock_authority_bars_2015_2025.json"),
    startup_gate_packet: str | Path | None = Path("data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json"),
    data_manifest_packet: str | Path | None = Path("data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json"),
    allow_review_required_data_manifest: bool = False,
    max_candidates: int | None = None,
) -> dict[str, Any]:
    base_config = _load_replay_base_config(base_config_path)
    candidates = pd.read_csv(candidates_csv)
    _enforce_cn_stock_replay_inputs(
        source=source,
        markets=base_config.markets,
        startup_gate_packet=startup_gate_packet,
        data_manifest_packet=data_manifest_packet,
        data_root=Path(data_root),
        allow_review_required_data_manifest=allow_review_required_data_manifest,
    )
    bars = _load_bars(
        source=source,
        data_root=Path(data_root),
        markets=base_config.markets,
        authority_bars_config=authority_bars_config,
    )
    return run_same_parameter_full_sample_replay(
        candidates,
        bars,
        base_config,
        output_dir=output_dir,
        start_date=start_date,
        end_date=end_date,
        max_candidates=max_candidates,
    )


def _load_replay_base_config(path: str | Path):
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict) and isinstance(data.get("experiment_grid"), dict):
        return load_walk_forward_config(config_path).experiment_grid
    return load_experiment_grid_config(config_path)


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
        frames = [load_processed_bars(data_root, market) for market in markets if market.upper() != "ALL"]
        if not frames:
            raise ValueError("processed-bars source requires at least one specific market")
        return pd.concat(frames, ignore_index=True)
    raise ValueError(f"Unsupported replay source: {source}")


def _enforce_cn_stock_replay_inputs(
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
        context="CN same-parameter full-sample replay",
    )
    validate_cn_stock_data_manifest_packet(
        data_manifest_packet,
        expected_source_root=data_root,
        allow_review_required=allow_review_required_data_manifest,
        context="CN same-parameter full-sample replay",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run same-parameter full-sample replay for candidate rows.")
    parser.add_argument("--candidates-csv", required=True)
    parser.add_argument("--base-config", required=True)
    parser.add_argument("--source", choices=["fixture", "processed-bars", "authority-processed-bars"], default="fixture")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    parser.add_argument("--authority-bars-config", default="configs/cn_stock_authority_bars_2015_2025.json")
    parser.add_argument("--startup-gate-packet", default="data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json")
    parser.add_argument("--data-manifest-packet", default="data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json")
    parser.add_argument("--allow-review-required-data-manifest", action="store_true")
    parser.add_argument("--max-candidates", type=int)
    args = parser.parse_args()

    pack = run_same_parameter_full_sample_replay_from_files(
        candidates_csv=Path(args.candidates_csv),
        base_config_path=Path(args.base_config),
        source=args.source,
        data_root=Path(args.data_root),
        output_dir=Path(args.output_dir),
        start_date=args.start_date,
        end_date=args.end_date,
        authority_bars_config=Path(args.authority_bars_config) if args.authority_bars_config else None,
        startup_gate_packet=Path(args.startup_gate_packet) if args.startup_gate_packet else None,
        data_manifest_packet=Path(args.data_manifest_packet) if args.data_manifest_packet else None,
        allow_review_required_data_manifest=args.allow_review_required_data_manifest,
        max_candidates=args.max_candidates,
    )
    print(json.dumps({"stage": pack["stage"], "summary": pack["summary"], "output_dir": str(Path(args.output_dir))}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
