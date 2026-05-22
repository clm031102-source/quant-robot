from __future__ import annotations

import pandas as pd

from quant_robot.research.groups import quantile_group_returns


def long_short_returns(factors: pd.DataFrame, labels: pd.DataFrame, quantiles: int = 5) -> pd.DataFrame:
    grouped = quantile_group_returns(factors, labels, quantiles=quantiles)
    if grouped.empty:
        return pd.DataFrame(columns=["date", "market", "factor_name", "long_short_return"])
    bottom = grouped[grouped["quantile"] == 1][["date", "market", "factor_name", "mean_forward_return"]]
    top = grouped[grouped["quantile"] == quantiles][["date", "market", "factor_name", "mean_forward_return"]]
    merged = top.merge(bottom, on=["date", "market", "factor_name"], suffixes=("_top", "_bottom"))
    merged["long_short_return"] = merged["mean_forward_return_top"] - merged["mean_forward_return_bottom"]
    return merged[["date", "market", "factor_name", "long_short_return"]].sort_values(
        ["date", "market", "factor_name"]
    ).reset_index(drop=True)
