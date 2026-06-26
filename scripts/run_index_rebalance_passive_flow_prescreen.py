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

from quant_robot.ops.index_rebalance_passive_flow_prescreen import (
    build_index_rebalance_passive_flow_prescreen,
    write_index_rebalance_passive_flow_prescreen,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/index_rebalance_passive_flow_prescreen")


def run_index_rebalance_passive_flow_prescreen_cli(
    *,
    index_events_path: str | Path,
    bars_path: str | Path,
    stock_basic_path: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    horizons: tuple[int, ...] = (5, 20),
    min_cross_section: int = 30,
    min_ic_observations: int = 8,
    min_neutral_rank_ic: float = 0.01,
    min_neutral_ic_t_stat: float = 2.0,
    min_neutral_retention: float = 0.50,
) -> dict[str, Any]:
    result = build_index_rebalance_passive_flow_prescreen(
        index_events=_read_frame(index_events_path),
        bars=_read_frame(bars_path),
        stock_basic=_read_frame(stock_basic_path),
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_neutral_rank_ic=min_neutral_rank_ic,
        min_neutral_ic_t_stat=min_neutral_ic_t_stat,
        min_neutral_retention=min_neutral_retention,
    )
    write_index_rebalance_passive_flow_prescreen(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CN stock index rebalance passive-flow prescreen.")
    parser.add_argument("--index-events", required=True)
    parser.add_argument("--bars", required=True)
    parser.add_argument("--stock-basic", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--horizons", default="5,20")
    parser.add_argument("--min-cross-section", type=int, default=30)
    parser.add_argument("--min-ic-observations", type=int, default=8)
    parser.add_argument("--min-neutral-rank-ic", type=float, default=0.01)
    parser.add_argument("--min-neutral-ic-t-stat", type=float, default=2.0)
    parser.add_argument("--min-neutral-retention", type=float, default=0.50)
    args = parser.parse_args()
    result = run_index_rebalance_passive_flow_prescreen_cli(
        index_events_path=args.index_events,
        bars_path=args.bars,
        stock_basic_path=args.stock_basic,
        output_dir=args.output_dir,
        horizons=_parse_horizons(args.horizons),
        min_cross_section=args.min_cross_section,
        min_ic_observations=args.min_ic_observations,
        min_neutral_rank_ic=args.min_neutral_rank_ic,
        min_neutral_ic_t_stat=args.min_neutral_ic_t_stat,
        min_neutral_retention=args.min_neutral_retention,
    )
    print(json.dumps(_sanitize(result), indent=2, sort_keys=True))


def _read_frame(path: str | Path) -> pd.DataFrame:
    input_path = Path(path)
    if input_path.suffix.lower() == ".parquet":
        return pd.read_parquet(input_path)
    return pd.read_csv(input_path)


def _parse_horizons(value: str) -> tuple[int, ...]:
    horizons = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    if not horizons:
        raise ValueError("--horizons must contain at least one integer")
    return horizons


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key not in {"markdown", "factor_rows"}}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


if __name__ == "__main__":
    main()
