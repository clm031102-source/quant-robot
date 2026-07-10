from __future__ import annotations

import pandas as pd

from quant_robot.research.groups import quantile_group_returns


def long_short_returns(factors: pd.DataFrame, labels: pd.DataFrame, quantiles: int = 5) -> pd.DataFrame:
    grouped = quantile_group_returns(factors, labels, quantiles=quantiles)
    if grouped.empty:
        return pd.DataFrame(
            columns=["date", "market", "factor_name", "horizon", "execution_lag", "long_short_return"]
        )
    identity_columns = [
        column
        for column in ("date", "market", "factor_name", "horizon", "execution_lag")
        if column in grouped.columns
    ]
    bottom = grouped[grouped["quantile"] == 1][[*identity_columns, "mean_forward_return"]]
    top = grouped[grouped["quantile"] == quantiles][[*identity_columns, "mean_forward_return"]]
    merged = top.merge(bottom, on=identity_columns, suffixes=("_top", "_bottom"))
    merged["long_short_return"] = merged["mean_forward_return_top"] - merged["mean_forward_return_bottom"]
    return merged[[*identity_columns, "long_short_return"]].sort_values(identity_columns).reset_index(drop=True)
