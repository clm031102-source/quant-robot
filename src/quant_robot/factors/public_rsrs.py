from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


PUBLIC_RSRS_FACTOR_NAMES = (
    "rsrs_slope_18",
    "rsrs_zscore_18_60",
    "rsrs_right_skew_18_60",
    "rsrs_reversal_18_60",
)


def compute_public_rsrs_factors(
    bars: pd.DataFrame,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "high", "low"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing columns for public RSRS factor calculation: {', '.join(missing)}")
    requested = _resolve_requested_factor_names(factor_names)
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    pieces = []
    for _, group in frame.groupby("asset_id", sort=False):
        enriched = _rsrs_features(group)
        if "rsrs_slope_18" in requested:
            pieces.append(_factor_frame(enriched, "rsrs_slope_18", enriched["rsrs_slope_18"], 18))
        if "rsrs_zscore_18_60" in requested:
            pieces.append(_factor_frame(enriched, "rsrs_zscore_18_60", enriched["rsrs_zscore_18_60"], 60))
        if "rsrs_right_skew_18_60" in requested:
            pieces.append(_factor_frame(enriched, "rsrs_right_skew_18_60", enriched["rsrs_right_skew_18_60"], 60))
        if "rsrs_reversal_18_60" in requested:
            pieces.append(_factor_frame(enriched, "rsrs_reversal_18_60", -enriched["rsrs_right_skew_18_60"], 60))
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return PUBLIC_RSRS_FACTOR_NAMES
    supported = set(PUBLIC_RSRS_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported public RSRS factor_names: {', '.join(unknown)}")
    return factor_names


def _rsrs_features(group: pd.DataFrame) -> pd.DataFrame:
    frame = group.copy()
    high = pd.to_numeric(frame["high"], errors="coerce")
    low = pd.to_numeric(frame["low"], errors="coerce")
    slope = _rolling_slope(low, high, 18)
    r_squared = high.rolling(18, min_periods=18).corr(low).pow(2.0)
    slope_mean = slope.rolling(60, min_periods=20).mean()
    slope_std = slope.rolling(60, min_periods=20).std(ddof=0).replace(0.0, np.nan)
    zscore = ((slope - slope_mean) / slope_std).replace([np.inf, -np.inf], np.nan)
    frame["rsrs_slope_18"] = slope
    frame["rsrs_zscore_18_60"] = zscore
    frame["rsrs_right_skew_18_60"] = zscore * r_squared
    return frame


def _rolling_slope(x: pd.Series, y: pd.Series, window: int) -> pd.Series:
    mean_x = x.rolling(window, min_periods=window).mean()
    mean_y = y.rolling(window, min_periods=window).mean()
    mean_xy = (x * y).rolling(window, min_periods=window).mean()
    mean_x2 = (x * x).rolling(window, min_periods=window).mean()
    covariance = mean_xy - mean_x * mean_y
    variance = (mean_x2 - mean_x * mean_x).where(lambda values: values.abs() > 1e-12)
    with np.errstate(divide="ignore", invalid="ignore"):
        slope = covariance / variance
    return slope.replace([np.inf, -np.inf], np.nan)


def _factor_frame(group: pd.DataFrame, name: str, values: pd.Series, window: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": group["date"].to_numpy(),
            "asset_id": group["asset_id"].to_numpy(),
            "market": group["market"].to_numpy(),
            "factor_name": name,
            "factor_value": values.to_numpy(),
            "lookback_window": window,
        }
    )
