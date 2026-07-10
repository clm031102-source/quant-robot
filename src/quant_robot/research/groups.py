from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.research.ic import _evaluation_group_columns, _merge_factors_labels


def quantile_group_returns(factors: pd.DataFrame, labels: pd.DataFrame, quantiles: int = 5) -> pd.DataFrame:
    merged = _merge_factors_labels(factors, labels).dropna(subset=["factor_value", "forward_return"])
    group_columns = _evaluation_group_columns(merged)
    if merged.empty:
        return pd.DataFrame(
            columns=["date", "market", "factor_name", "horizon", "execution_lag", "quantile", "mean_forward_return", "count"]
        )
    merged = merged.copy()
    merged["quantile"] = merged.groupby(group_columns, group_keys=False)["factor_value"].transform(
        lambda values: _rank_quantiles(values, quantiles)
    )
    return (
        merged.groupby([*group_columns, "quantile"], as_index=False)
        .agg(mean_forward_return=("forward_return", "mean"), count=("forward_return", "size"))
        .sort_values([*group_columns, "quantile"])
        .reset_index(drop=True)
    )


def _rank_quantiles(values: pd.Series, quantiles: int) -> pd.Series:
    ranks = values.rank(method="first", pct=True)
    buckets = np.ceil(ranks * quantiles).astype(int)
    return pd.Series(np.clip(buckets, 1, quantiles), index=values.index)
