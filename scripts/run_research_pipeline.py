from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.research.pipeline import ResearchPipelineConfig, run_research_pipeline
from quant_robot.storage.dataset_store import DatasetStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a configurable local research/backtest pipeline.")
    parser.add_argument("--source", choices=["fixture", "processed-bars"], default="fixture")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--market", default="ALL")
    parser.add_argument("--factor", default="momentum_2")
    parser.add_argument("--factor-windows", default="2,3")
    parser.add_argument("--top-n", default=2, type=int)
    parser.add_argument("--cost-bps", default=5.0, type=float)
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--output-dir", default="data/reports/research_pipeline")
    args = parser.parse_args()
    bars = load_demo_market_bars() if args.source == "fixture" else _load_processed_bars(Path(args.data_root), args.market)
    config = ResearchPipelineConfig(
        factor_name=args.factor,
        factor_windows=_parse_windows(args.factor_windows),
        market=args.market,
        start_date=args.start_date,
        end_date=args.end_date,
        top_n=args.top_n,
        cost_bps=args.cost_bps,
        output_dir=Path(args.output_dir),
    )
    result = run_research_pipeline(bars, config)
    print(json.dumps({"request": result["request"], "metrics": result["metrics"], "artifact_rows": result["artifact_rows"]}, indent=2, sort_keys=True))


def _parse_windows(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def _load_processed_bars(root: Path, market: str) -> pd.DataFrame:
    if market.upper() == "ALL":
        raise ValueError("--market must be specific when loading processed-bars")
    market = market.upper()
    frames = []
    for store_root in _discover_processed_store_roots(root, market):
        store = DatasetStore(store_root)
        base = store.partition_path("processed/bars", {"frequency": "1d", "market": market})
        for year_path in sorted(base.glob("year=*")):
            year = year_path.name.split("=", 1)[1]
            frames.append(store.read_frame("processed/bars", {"frequency": "1d", "market": market, "year": year}))
    if not frames:
        raise FileNotFoundError(f"No processed bars found under {root}")
    return pd.concat(frames, ignore_index=True)


def _discover_processed_store_roots(root: Path, market: str) -> list[Path]:
    market_part = f"market={market}"
    candidate_bases = [
        root / "processed" / "bars" / "frequency=1d" / market_part,
        root / "bars" / "frequency=1d" / market_part,
        root / "frequency=1d" / market_part,
    ]
    store_roots = []
    for base in candidate_bases:
        if not base.exists() or base.parts[-4:] != ("processed", "bars", "frequency=1d", market_part):
            continue
        store_roots.append(base.parents[3])
    if root.exists():
        for base in sorted(root.rglob(f"processed/bars/frequency=1d/{market_part}")):
            store_roots.append(base.parents[3])
    unique_roots = []
    for store_root in store_roots:
        resolved = store_root.resolve()
        if resolved not in [item.resolve() for item in unique_roots]:
            unique_roots.append(store_root)
    return unique_roots


if __name__ == "__main__":
    main()
