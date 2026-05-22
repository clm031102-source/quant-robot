from __future__ import annotations

import pandas as pd


def select_top_n(factors: pd.DataFrame, top_n: int, portfolio_scope: str = "market") -> pd.DataFrame:
    if top_n <= 0:
        raise ValueError("top_n must be positive")
    group_columns = _group_columns(portfolio_scope)
    sort_columns = _sort_columns(portfolio_scope)
    ascending = [True] * (len(sort_columns) - 1) + [False]
    selected = (
        factors.dropna(subset=["factor_value"])
        .sort_values(sort_columns, ascending=ascending)
        .groupby(group_columns, as_index=False, group_keys=False)
        .head(top_n)
        .copy()
    )
    if selected.empty:
        selected["target_weight"] = pd.Series(dtype=float)
        return selected
    selected["target_weight"] = selected.groupby(group_columns)["asset_id"].transform(lambda values: 1.0 / len(values))
    return selected.reset_index(drop=True)


def _group_columns(portfolio_scope: str) -> list[str]:
    if portfolio_scope == "market":
        return ["date", "market", "factor_name"]
    if portfolio_scope == "global":
        return ["date", "factor_name"]
    raise ValueError("portfolio_scope must be 'market' or 'global'")


def _sort_columns(portfolio_scope: str) -> list[str]:
    if portfolio_scope == "market":
        return ["date", "market", "factor_name", "factor_value"]
    if portfolio_scope == "global":
        return ["date", "factor_name", "factor_value"]
    raise ValueError("portfolio_scope must be 'market' or 'global'")
