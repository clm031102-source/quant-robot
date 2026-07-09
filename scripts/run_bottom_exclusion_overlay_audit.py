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

from quant_robot.data.fixtures import load_demo_market_bars  # noqa: E402
from quant_robot.experiments.runner import (  # noqa: E402
    _filter_bars_for_asset_universe,
    _filter_bars_for_precompute,
    _precompute_factor_matrix,
    load_experiment_grid_config,
)
from quant_robot.ops.bottom_exclusion_overlay_audit import (  # noqa: E402
    build_bottom_exclusion_overlay_audit,
    write_bottom_exclusion_overlay_audit,
)
from quant_robot.ops.cn_stock_data_manifest import validate_cn_stock_data_manifest_packet  # noqa: E402
from quant_robot.ops.factor_batch_readiness_gate import validate_factor_batch_readiness_gate_packet  # noqa: E402
from quant_robot.ops.factor_mining_startup import validate_cleared_startup_gate_packet  # noqa: E402
from quant_robot.research.labels import make_forward_returns  # noqa: E402
from quant_robot.storage.authority_bars import load_authority_processed_bars_from_config  # noqa: E402
from quant_robot.storage.processed_bars import load_processed_bars  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("data/reports/bottom_exclusion_overlay_audit")


def run_bottom_exclusion_overlay_audit(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    factors: str | Path | None = None,
    labels: str | Path | None = None,
    grid_config: str | Path | None = None,
    source: str = "authority-processed-bars",
    data_root: str | Path = "data/processed",
    authority_bars_config: str | Path | None = "configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json",
    startup_gate_packet: str | Path | None = Path("data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json"),
    data_manifest_packet: str | Path | None = Path("data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json"),
    factor_batch_readiness_gate_packet: str | Path | None = Path(
        "data/reports/factor_batch_readiness_gate/factor_batch_readiness_gate.json"
    ),
    allow_review_required_data_manifest: bool = False,
    bottom_quantile: float = 0.2,
    rebalance_interval: int | None = None,
    min_dates: int = 5,
    min_overlay_t_stat: float = 2.0,
    min_positive_overlay_rate: float = 0.55,
    min_mean_overlay_excess_return: float = 0.0,
) -> dict[str, Any]:
    if grid_config is not None:
        factor_frame, label_frame, source_report, resolved_rebalance_interval = _build_frames_from_grid(
            Path(grid_config),
            source=source,
            data_root=Path(data_root),
            authority_bars_config=Path(authority_bars_config) if authority_bars_config else None,
            startup_gate_packet=Path(startup_gate_packet) if startup_gate_packet is not None else None,
            data_manifest_packet=Path(data_manifest_packet) if data_manifest_packet is not None else None,
            factor_batch_readiness_gate_packet=(
                Path(factor_batch_readiness_gate_packet) if factor_batch_readiness_gate_packet is not None else None
            ),
            allow_review_required_data_manifest=allow_review_required_data_manifest,
            rebalance_interval=rebalance_interval,
        )
    else:
        if factors is None or labels is None:
            raise ValueError("Either --grid-config or both --factors and --labels are required")
        factor_frame = _load_frame(Path(factors))
        label_frame = _load_frame(Path(labels))
        resolved_rebalance_interval = rebalance_interval or 1
        source_report = f"factors={Path(factors)} labels={Path(labels)} rebalance_interval={resolved_rebalance_interval}"

    audit = build_bottom_exclusion_overlay_audit(
        factor_frame,
        label_frame,
        source_report=source_report,
        bottom_quantile=bottom_quantile,
        rebalance_interval=resolved_rebalance_interval,
        min_dates=min_dates,
        min_overlay_t_stat=min_overlay_t_stat,
        min_positive_overlay_rate=min_positive_overlay_rate,
        min_mean_overlay_excess_return=min_mean_overlay_excess_return,
    )
    write_bottom_exclusion_overlay_audit(output_dir, audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit whether a factor is useful as a bottom-quantile exclusion overlay.")
    parser.add_argument("--grid-config", help="Experiment-grid config used to precompute factors and labels.")
    parser.add_argument("--factors", help="Factor matrix CSV/JSON/Parquet path. Requires --labels.")
    parser.add_argument("--labels", help="Forward-return labels CSV/JSON/Parquet path. Requires --factors.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--source", choices=["fixture", "processed-bars", "authority-processed-bars"], default="authority-processed-bars")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--authority-bars-config", default="configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json")
    parser.add_argument("--startup-gate-packet", default="data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json")
    parser.add_argument("--data-manifest-packet", default="data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json")
    parser.add_argument(
        "--factor-batch-readiness-gate-packet",
        default="data/reports/factor_batch_readiness_gate/factor_batch_readiness_gate.json",
    )
    parser.add_argument("--allow-review-required-data-manifest", action="store_true")
    parser.add_argument("--bottom-quantile", type=float, default=0.2)
    parser.add_argument("--rebalance-interval", type=int)
    parser.add_argument("--min-dates", type=int, default=5)
    parser.add_argument("--min-overlay-t-stat", type=float, default=2.0)
    parser.add_argument("--min-positive-overlay-rate", type=float, default=0.55)
    parser.add_argument("--min-mean-overlay-excess-return", type=float, default=0.0)
    args = parser.parse_args()

    try:
        audit = run_bottom_exclusion_overlay_audit(
            output_dir=Path(args.output_dir),
            factors=Path(args.factors) if args.factors else None,
            labels=Path(args.labels) if args.labels else None,
            grid_config=Path(args.grid_config) if args.grid_config else None,
            source=args.source,
            data_root=Path(args.data_root),
            authority_bars_config=Path(args.authority_bars_config) if args.authority_bars_config else None,
            startup_gate_packet=Path(args.startup_gate_packet) if args.startup_gate_packet else None,
            data_manifest_packet=Path(args.data_manifest_packet) if args.data_manifest_packet else None,
            factor_batch_readiness_gate_packet=(
                Path(args.factor_batch_readiness_gate_packet) if args.factor_batch_readiness_gate_packet else None
            ),
            allow_review_required_data_manifest=args.allow_review_required_data_manifest,
            bottom_quantile=args.bottom_quantile,
            rebalance_interval=args.rebalance_interval,
            min_dates=args.min_dates,
            min_overlay_t_stat=args.min_overlay_t_stat,
            min_positive_overlay_rate=args.min_positive_overlay_rate,
            min_mean_overlay_excess_return=args.min_mean_overlay_excess_return,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(
        json.dumps(
            {
                "summary": audit["summary"],
                "recommended_next_actions": audit["recommended_next_actions"],
                "top": audit["factor_summary"][:10],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _build_frames_from_grid(
    config_path: Path,
    *,
    source: str,
    data_root: Path,
    authority_bars_config: Path | None,
    startup_gate_packet: str | Path | None = Path("data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json"),
    data_manifest_packet: str | Path | None = Path("data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json"),
    factor_batch_readiness_gate_packet: str | Path | None = Path(
        "data/reports/factor_batch_readiness_gate/factor_batch_readiness_gate.json"
    ),
    allow_review_required_data_manifest: bool = False,
    rebalance_interval: int | None,
) -> tuple[pd.DataFrame, pd.DataFrame, str, int]:
    config = load_experiment_grid_config(config_path)
    _enforce_cn_stock_bottom_exclusion_overlay_inputs(
        source=source,
        markets=config.markets,
        startup_gate_packet=startup_gate_packet,
        data_manifest_packet=data_manifest_packet,
        factor_batch_readiness_gate_packet=factor_batch_readiness_gate_packet,
        data_root=data_root,
        allow_review_required_data_manifest=allow_review_required_data_manifest,
    )
    bars = _load_bars(
        source,
        data_root,
        config.markets,
        authority_bars_config=authority_bars_config,
    )
    bars = _filter_bars_for_asset_universe(bars, config)
    filtered = _filter_bars_for_precompute(bars, config)
    factors = _precompute_factor_matrix(filtered, config)
    if factors is None or factors.empty:
        raise ValueError(f"Grid config produced no factor matrix: {config_path}")
    labels = make_forward_returns(
        filtered,
        horizons=(config.forward_horizon,),
        execution_lag=config.execution_lag,
    )
    resolved_rebalance_interval = rebalance_interval or int(config.rebalance_intervals[0])
    source_report = f"grid_config={config_path} rebalance_interval={resolved_rebalance_interval}"
    return factors, labels, source_report, resolved_rebalance_interval


def _enforce_cn_stock_bottom_exclusion_overlay_inputs(
    *,
    source: str,
    markets: tuple[str, ...],
    startup_gate_packet: str | Path | None,
    data_manifest_packet: str | Path | None,
    factor_batch_readiness_gate_packet: str | Path | None,
    data_root: Path,
    allow_review_required_data_manifest: bool,
) -> None:
    if source not in {"processed-bars", "authority-processed-bars"} or not any(market.upper() == "CN" for market in markets):
        return
    validate_cleared_startup_gate_packet(
        startup_gate_packet,
        context="CN bottom-exclusion overlay audit",
    )
    validate_cn_stock_data_manifest_packet(
        data_manifest_packet,
        expected_source_root=data_root,
        allow_review_required=allow_review_required_data_manifest,
        context="CN bottom-exclusion overlay audit",
    )
    validate_factor_batch_readiness_gate_packet(
        factor_batch_readiness_gate_packet,
        context="CN bottom-exclusion overlay audit",
    )


def _load_bars(
    source: str,
    data_root: Path,
    markets: tuple[str, ...],
    *,
    authority_bars_config: Path | None,
) -> pd.DataFrame:
    if source == "fixture":
        return load_demo_market_bars()
    if source == "authority-processed-bars":
        if authority_bars_config is None:
            raise ValueError("authority_bars_config is required for authority-processed-bars source")
        return load_authority_processed_bars_from_config(authority_bars_config, markets=markets)
    if source != "processed-bars":
        raise ValueError(f"Unsupported source: {source}")
    frames = [load_processed_bars(data_root, market) for market in markets if market.upper() != "ALL"]
    if not frames:
        raise ValueError("processed-bars source requires at least one specific market")
    return pd.concat(frames, ignore_index=True)


def _load_frame(path: Path) -> pd.DataFrame:
    if path.is_dir():
        files = sorted([*path.rglob("*.parquet"), *path.rglob("*.csv"), *path.rglob("*.json"), *path.rglob("*.jsonl")])
        if not files:
            raise FileNotFoundError(f"No tabular files found under {path}")
        return pd.concat([_load_frame(file) for file in files], ignore_index=True)
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".jsonl", ".ndjson"}:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return pd.DataFrame(rows)
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return pd.DataFrame(data)
        if isinstance(data, dict):
            for key in ("rows", "factors", "labels", "data"):
                value = data.get(key)
                if isinstance(value, list):
                    return pd.DataFrame(value)
        raise ValueError(f"JSON file does not contain a supported row list: {path}")
    raise ValueError(f"Unsupported frame file type: {path}")


if __name__ == "__main__":
    main()
