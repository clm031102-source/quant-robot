from __future__ import annotations

import pandas as pd


def compute_ic(factors: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    merged = _merge_factors_labels(factors, labels)
    rows = []
    for (date, factor_name), group in merged.groupby(["date", "factor_name"], sort=True):
        valid = group[["factor_value", "forward_return"]].dropna()
        ic = _safe_corr(valid["factor_value"], valid["forward_return"])
        rank_ic = _safe_corr(valid["factor_value"].rank(), valid["forward_return"].rank())
        rows.append(
            {
                "date": date,
                "factor_name": factor_name,
                "ic": ic,
                "rank_ic": rank_ic,
                "count": len(valid),
            }
        )
    return pd.DataFrame(rows)


def _merge_factors_labels(factors: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    return factors.merge(labels, on=["date", "asset_id", "market"], how="inner")


def _safe_corr(left: pd.Series, right: pd.Series) -> float:
    valid = pd.concat([left, right], axis=1).dropna()
    if len(valid) < 2:
        return float("nan")
    left_values = valid.iloc[:, 0]
    right_values = valid.iloc[:, 1]
    if left_values.nunique() < 2 or right_values.nunique() < 2:
        return float("nan")
    return float(left_values.corr(right_values))
