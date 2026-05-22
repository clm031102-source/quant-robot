from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore


def load_processed_bars(root: str | Path, market: str) -> pd.DataFrame:
    root_path = Path(root)
    if market.upper() == "ALL":
        raise ValueError("market must be specific when loading processed bars")
    market = market.upper()
    frames = []
    for store_root in discover_processed_store_roots(root_path, market):
        store = DatasetStore(store_root)
        base = store.partition_path("processed/bars", {"frequency": "1d", "market": market})
        for year_path in sorted(base.glob("year=*")):
            year = year_path.name.split("=", 1)[1]
            frames.append(store.read_frame("processed/bars", {"frequency": "1d", "market": market, "year": year}))
    if not frames:
        raise FileNotFoundError(f"No processed bars found under {root_path}")
    return pd.concat(frames, ignore_index=True)


def discover_processed_store_roots(root: str | Path, market: str) -> list[Path]:
    root_path = Path(root)
    market_part = f"market={market.upper()}"
    candidate_bases = [
        root_path / "processed" / "bars" / "frequency=1d" / market_part,
        root_path / "bars" / "frequency=1d" / market_part,
        root_path / "frequency=1d" / market_part,
    ]
    store_roots = []
    for base in candidate_bases:
        if not base.exists() or base.parts[-4:] != ("processed", "bars", "frequency=1d", market_part):
            continue
        store_roots.append(base.parents[3])
    if root_path.exists():
        for base in sorted(root_path.rglob(f"processed/bars/frequency=1d/{market_part}")):
            store_roots.append(base.parents[3])
    unique_roots = []
    for store_root in store_roots:
        resolved = store_root.resolve()
        if resolved not in [item.resolve() for item in unique_roots]:
            unique_roots.append(store_root)
    return unique_roots
