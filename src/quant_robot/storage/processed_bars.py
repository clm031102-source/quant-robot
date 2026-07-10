from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore


def load_processed_bars(root: str | Path, market: str, *, recursive: bool = False) -> pd.DataFrame:
    root_path = Path(root)
    if market.upper() == "ALL":
        raise ValueError("market must be specific when loading processed bars")
    market = market.upper()
    frames = []
    store_roots = discover_processed_store_roots(root_path, market, recursive=recursive)
    if len(store_roots) > 1:
        roots = ", ".join(str(path) for path in store_roots)
        raise ValueError(f"ambiguous processed bars for {market}: {roots}")
    for store_root in store_roots:
        store = DatasetStore(store_root)
        base = store.partition_path("processed/bars", {"frequency": "1d", "market": market})
        for year_path in sorted(base.glob("year=*")):
            year = year_path.name.split("=", 1)[1]
            frames.append(store.read_frame("processed/bars", {"frequency": "1d", "market": market, "year": year}))
    if not frames:
        raise FileNotFoundError(f"No processed bars found under {root_path}")
    result = pd.concat(frames, ignore_index=True)
    duplicate_keys = [column for column in ("asset_id", "timestamp", "frequency") if column in result.columns]
    if len(duplicate_keys) == 3 and result.duplicated(duplicate_keys).any():
        raise ValueError("processed bars contain duplicate authority keys")
    sort_columns = [column for column in ("asset_id", "timestamp", "date") if column in result.columns]
    return result.sort_values(sort_columns).reset_index(drop=True) if sort_columns else result


def discover_processed_store_roots(root: str | Path, market: str, *, recursive: bool = False) -> list[Path]:
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
    if recursive and root_path.exists():
        for base in sorted(root_path.rglob(f"processed/bars/frequency=1d/{market_part}")):
            store_roots.append(base.parents[3])
    unique_roots = []
    resolved_roots: set[Path] = set()
    for store_root in store_roots:
        resolved = store_root.resolve()
        if resolved not in resolved_roots:
            unique_roots.append(store_root)
            resolved_roots.add(resolved)
    return unique_roots
