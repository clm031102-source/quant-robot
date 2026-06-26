from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.etf_validation_preflight import (
    ETFValidationPreflightPolicy,
    build_etf_validation_preflight,
    write_etf_validation_preflight,
)
from quant_robot.validation.walk_forward import load_walk_forward_config
from scripts.run_walk_forward import _load_bars


def run_etf_validation_preflight(
    *,
    config_path: str | Path,
    source: str = "fixture",
    data_root: str | Path = "data/processed",
    output_dir: str | Path = "data/reports/etf_validation_preflight",
    min_assets: int = ETFValidationPreflightPolicy.min_assets,
    min_rebalance_opportunities_per_fold: int = ETFValidationPreflightPolicy.min_rebalance_opportunities_per_fold,
    min_median_allowed_rebalance_dates: int = ETFValidationPreflightPolicy.min_median_allowed_rebalance_dates,
    max_zero_allowed_fold_rate: float = ETFValidationPreflightPolicy.max_zero_allowed_fold_rate,
) -> dict[str, object]:
    config = load_walk_forward_config(config_path)
    bars = _load_bars(source, Path(data_root), config.experiment_grid.markets)
    packet = build_etf_validation_preflight(
        bars,
        config,
        policy=ETFValidationPreflightPolicy(
            min_assets=min_assets,
            min_rebalance_opportunities_per_fold=min_rebalance_opportunities_per_fold,
            min_median_allowed_rebalance_dates=min_median_allowed_rebalance_dates,
            max_zero_allowed_fold_rate=max_zero_allowed_fold_rate,
        ),
    )
    write_etf_validation_preflight(output_dir, packet)
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CN ETF validation preflight before expensive walk-forward jobs.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--source", choices=["fixture", "processed-bars"], default="fixture")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--output-dir", default="data/reports/etf_validation_preflight")
    parser.add_argument("--min-assets", type=int, default=ETFValidationPreflightPolicy.min_assets)
    parser.add_argument(
        "--min-rebalance-opportunities-per-fold",
        type=int,
        default=ETFValidationPreflightPolicy.min_rebalance_opportunities_per_fold,
    )
    parser.add_argument(
        "--min-median-allowed-rebalance-dates",
        type=int,
        default=ETFValidationPreflightPolicy.min_median_allowed_rebalance_dates,
    )
    parser.add_argument(
        "--max-zero-allowed-fold-rate",
        type=float,
        default=ETFValidationPreflightPolicy.max_zero_allowed_fold_rate,
    )
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="Exit successfully while still writing the blocked preflight packet.",
    )
    args = parser.parse_args()
    packet = run_etf_validation_preflight(
        config_path=Path(args.config),
        source=args.source,
        data_root=Path(args.data_root),
        output_dir=Path(args.output_dir),
        min_assets=args.min_assets,
        min_rebalance_opportunities_per_fold=args.min_rebalance_opportunities_per_fold,
        min_median_allowed_rebalance_dates=args.min_median_allowed_rebalance_dates,
        max_zero_allowed_fold_rate=args.max_zero_allowed_fold_rate,
    )
    print(json.dumps({"status": packet["status"], "summary": packet["summary"], "decision": packet["decision"]}, indent=2, sort_keys=True))
    if packet["status"] != "cleared" and not args.allow_blocked:
        raise SystemExit("ETF validation preflight blocked this run")


if __name__ == "__main__":
    main()
