from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore


def load_etf_moneyflow_baskets(root: str | Path, market: str) -> pd.DataFrame:
    root_path = Path(root)
    if market.upper() == "ALL":
        raise ValueError("market must be specific when loading ETF moneyflow baskets")
    market = market.upper()
    frames = []
    for store_root in discover_etf_moneyflow_basket_store_roots(root_path, market):
        store = DatasetStore(store_root)
        frames.append(store.read_frame("metadata/etf_moneyflow_baskets", {"market": market}))
    if not frames:
        raise FileNotFoundError(f"No ETF moneyflow baskets found under {root_path}")
    return pd.concat(frames, ignore_index=True)


def discover_etf_moneyflow_basket_store_roots(root: str | Path, market: str) -> list[Path]:
    root_path = Path(root)
    market_part = f"market={market.upper()}"
    candidate_bases = [
        root_path / "metadata" / "etf_moneyflow_baskets" / market_part,
        root_path / "etf_moneyflow_baskets" / market_part,
    ]
    store_roots = []
    for base in candidate_bases:
        if not base.exists() or base.parts[-3:] != ("metadata", "etf_moneyflow_baskets", market_part):
            continue
        store_roots.append(base.parents[2])
    if root_path.exists():
        for base in sorted(root_path.rglob(f"metadata/etf_moneyflow_baskets/{market_part}")):
            store_roots.append(base.parents[2])
    unique_roots = []
    for store_root in store_roots:
        resolved = store_root.resolve()
        if resolved not in [item.resolve() for item in unique_roots]:
            unique_roots.append(store_root)
    return unique_roots
