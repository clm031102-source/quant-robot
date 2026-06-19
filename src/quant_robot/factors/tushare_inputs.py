from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


DAILY_BASIC_FACTOR_NAMES = (
    "turnover_rate",
    "turnover_rate_f",
    "volume_ratio",
    "turnover_rate_low",
    "turnover_rate_f_low",
    "volume_ratio_low",
    "pe_ttm_inverse",
    "pb_inverse",
    "ps_ttm_inverse",
    "dv_ttm",
    "total_mv_log",
    "circ_mv_log",
    "turnover_rate_low_large_mv",
    "turnover_rate_f_low_large_mv",
    "dv_ttm_large_mv",
    "ps_ttm_inverse_large_mv",
    "turnover_rate_low_mv_bucket_rank",
    "turnover_rate_f_low_mv_bucket_rank",
    "dv_ttm_mv_bucket_rank",
    "ps_ttm_inverse_mv_bucket_rank",
)


def compute_daily_basic_factors(inputs: pd.DataFrame, factor_names: tuple[str, ...] | None = None) -> pd.DataFrame:
    required = [
        "date",
        "asset_id",
        "market",
        "turnover_rate",
        "turnover_rate_f",
        "volume_ratio",
        "pe_ttm",
        "pb",
        "ps_ttm",
        "dv_ttm",
        "total_mv",
        "circ_mv",
    ]
    missing = [column for column in required if column not in inputs.columns]
    if missing:
        raise ValueError(f"Daily-basic inputs are missing columns: {', '.join(missing)}")
    requested = _resolve_requested_factor_names(factor_names)
    frame = inputs.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame.sort_values(["asset_id", "date"])
    builders = {
        "turnover_rate": lambda: pd.to_numeric(frame["turnover_rate"], errors="coerce"),
        "turnover_rate_f": lambda: pd.to_numeric(frame["turnover_rate_f"], errors="coerce"),
        "volume_ratio": lambda: pd.to_numeric(frame["volume_ratio"], errors="coerce"),
        "turnover_rate_low": lambda: _negative(frame["turnover_rate"]),
        "turnover_rate_f_low": lambda: _negative(frame["turnover_rate_f"]),
        "volume_ratio_low": lambda: _negative(frame["volume_ratio"]),
        "pe_ttm_inverse": lambda: _safe_inverse(frame["pe_ttm"]),
        "pb_inverse": lambda: _safe_inverse(frame["pb"]),
        "ps_ttm_inverse": lambda: _safe_inverse(frame["ps_ttm"]),
        "dv_ttm": lambda: pd.to_numeric(frame["dv_ttm"], errors="coerce"),
        "total_mv_log": lambda: _safe_log(frame["total_mv"]),
        "circ_mv_log": lambda: _safe_log(frame["circ_mv"]),
        "turnover_rate_low_large_mv": lambda: _capacity_aware_blend(_negative(frame["turnover_rate"]), frame["circ_mv"], frame["date"]),
        "turnover_rate_f_low_large_mv": lambda: _capacity_aware_blend(_negative(frame["turnover_rate_f"]), frame["circ_mv"], frame["date"]),
        "dv_ttm_large_mv": lambda: _capacity_aware_blend(frame["dv_ttm"], frame["circ_mv"], frame["date"]),
        "ps_ttm_inverse_large_mv": lambda: _capacity_aware_blend(_safe_inverse(frame["ps_ttm"]), frame["circ_mv"], frame["date"]),
        "turnover_rate_low_mv_bucket_rank": lambda: _bucket_rank_by_date(_negative(frame["turnover_rate"]), frame["circ_mv"], frame["date"]),
        "turnover_rate_f_low_mv_bucket_rank": lambda: _bucket_rank_by_date(_negative(frame["turnover_rate_f"]), frame["circ_mv"], frame["date"]),
        "dv_ttm_mv_bucket_rank": lambda: _bucket_rank_by_date(frame["dv_ttm"], frame["circ_mv"], frame["date"]),
        "ps_ttm_inverse_mv_bucket_rank": lambda: _bucket_rank_by_date(_safe_inverse(frame["ps_ttm"]), frame["circ_mv"], frame["date"]),
    }
    pieces = [_factor_frame(frame, name, builders[name]()) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return DAILY_BASIC_FACTOR_NAMES
    supported = set(DAILY_BASIC_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported daily-basic factor_names: {', '.join(unknown)}")
    return factor_names


def _safe_inverse(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return (1.0 / numeric.where(numeric > 0)).replace([np.inf, -np.inf], np.nan)


def _negative(values: pd.Series) -> pd.Series:
    return -pd.to_numeric(values, errors="coerce")


def _safe_log(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return np.log(numeric.where(numeric > 0)).replace([np.inf, -np.inf], np.nan)


def _capacity_aware_blend(signal: pd.Series, circ_mv: pd.Series, dates: pd.Series) -> pd.Series:
    signal_z = _zscore_by_date(signal, dates)
    size_z = _zscore_by_date(_safe_log(circ_mv), dates)
    return signal_z + size_z


def _zscore_by_date(values: pd.Series, dates: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    grouped = numeric.groupby(dates)
    means = grouped.transform("mean")
    stds = grouped.transform(lambda series: series.std(ddof=0))
    return (numeric - means) / stds.where(stds > 0)


def _bucket_rank_by_date(signal: pd.Series, circ_mv: pd.Series, dates: pd.Series, bucket_count: int = 5) -> pd.Series:
    frame = pd.DataFrame(
        {
            "signal": pd.to_numeric(signal, errors="coerce"),
            "size": _safe_log(circ_mv),
            "date": dates,
        }
    )
    result = pd.Series(np.nan, index=frame.index, dtype=float)
    for _, group in frame.dropna(subset=["signal", "size"]).groupby("date", sort=False):
        bucket_total = min(bucket_count, len(group))
        if bucket_total < 1:
            continue
        size_order = group["size"].rank(method="first")
        buckets = pd.qcut(size_order, q=bucket_total, labels=False, duplicates="drop")
        ranked = group["signal"].groupby(buckets).rank(method="average", pct=True)
        result.loc[group.index] = ranked.to_numpy(dtype=float)
    return result


def _factor_frame(inputs: pd.DataFrame, name: str, values: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": inputs["date"].to_numpy(),
            "asset_id": inputs["asset_id"].to_numpy(),
            "market": inputs["market"].to_numpy(),
            "factor_name": name,
            "factor_value": values.to_numpy(),
            "lookback_window": 1,
        }
    )
