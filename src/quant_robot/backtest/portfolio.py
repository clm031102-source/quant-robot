from __future__ import annotations

import pandas as pd


def select_top_n(factors: pd.DataFrame, top_n: int) -> pd.DataFrame:
    if top_n <= 0:
        raise ValueError("top_n must be positive")
    selected = (
        factors.dropna(subset=["factor_value"])
        .sort_values(["date", "factor_name", "factor_value"], ascending=[True, True, False])
        .groupby(["date", "factor_name"], as_index=False, group_keys=False)
        .head(top_n)
        .copy()
    )
    if selected.empty:
        selected["target_weight"] = pd.Series(dtype=float)
        return selected
    selected["target_weight"] = selected.groupby(["date", "factor_name"])["asset_id"].transform(lambda values: 1.0 / len(values))
    return selected.reset_index(drop=True)
