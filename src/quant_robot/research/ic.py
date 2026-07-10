from __future__ import annotations

import math

import pandas as pd


LABEL_DIMENSIONS = ("horizon", "execution_lag")


def compute_ic(factors: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    merged = _merge_factors_labels(factors, labels)
    rows = []
    group_columns = _evaluation_group_columns(merged)
    for group_key, group in merged.groupby(group_columns, sort=True):
        values = group_key if isinstance(group_key, tuple) else (group_key,)
        identity = dict(zip(group_columns, values, strict=True))
        valid = group[["factor_value", "forward_return"]].dropna()
        ic = _corr_stats(valid["factor_value"], valid["forward_return"])
        rank_ic = _corr_stats(valid["factor_value"].rank(), valid["forward_return"].rank())
        rows.append(
            {
                **identity,
                "ic": ic["correlation"],
                "rank_ic": rank_ic["correlation"],
                "ic_t_stat": ic["t_stat"],
                "ic_p_value": ic["p_value"],
                "rank_ic_t_stat": rank_ic["t_stat"],
                "rank_ic_p_value": rank_ic["p_value"],
                "count": len(valid),
            }
        )
    return pd.DataFrame(rows)


def _merge_factors_labels(factors: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    keys = ["date", "asset_id", "market"]
    keys.extend(column for column in LABEL_DIMENSIONS if column in factors.columns and column in labels.columns)
    return factors.merge(labels, on=keys, how="inner")


def _evaluation_group_columns(frame: pd.DataFrame) -> list[str]:
    columns = ["date", "market", "factor_name"]
    columns.extend(column for column in LABEL_DIMENSIONS if column in frame.columns)
    return columns


def _safe_corr(left: pd.Series, right: pd.Series) -> float:
    return _corr_stats(left, right)["correlation"]


def _corr_stats(left: pd.Series, right: pd.Series) -> dict[str, float]:
    valid = pd.concat([left, right], axis=1).dropna()
    if len(valid) < 2:
        return _empty_stats()
    left_values = valid.iloc[:, 0]
    right_values = valid.iloc[:, 1]
    if left_values.nunique() < 2 or right_values.nunique() < 2:
        return _empty_stats()
    correlation = float(left_values.corr(right_values))
    t_stat, p_value = _corr_t_test(correlation, len(valid))
    return {"correlation": correlation, "t_stat": t_stat, "p_value": p_value}


def _empty_stats() -> dict[str, float]:
    return {"correlation": float("nan"), "t_stat": float("nan"), "p_value": float("nan")}


def _corr_t_test(correlation: float, observations: int) -> tuple[float, float]:
    if observations < 3 or not math.isfinite(correlation):
        return float("nan"), float("nan")
    bounded = max(min(correlation, 1.0), -1.0)
    if abs(bounded) >= 1.0:
        return math.copysign(1e12, bounded), 0.0
    denominator = max(1.0 - bounded * bounded, 0.0)
    if denominator == 0.0:
        return math.copysign(1e12, bounded), 0.0
    t_stat = bounded * math.sqrt((observations - 2) / denominator)
    p_value = math.erfc(abs(t_stat) / math.sqrt(2.0))
    return t_stat, max(min(p_value, 1.0), 0.0)
