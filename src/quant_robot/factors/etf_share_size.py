from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


ETF_SHARE_SIZE_FACTOR_NAMES = (
    "share_change_1d",
    "share_change_1d_low",
    "size_change_1d",
    "size_change_1d_low",
    "nav_premium_discount",
    "nav_premium_discount_low",
    "total_share_log",
    "total_size_log",
)


def compute_etf_share_size_factors(inputs: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "total_share", "total_size", "nav", "close"]
    missing = [column for column in required if column not in inputs.columns]
    if missing:
        raise ValueError(f"ETF share-size inputs are missing columns: {', '.join(missing)}")
    frame = inputs.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    share_change = _existing_or_pct_change(frame, "share_change_1d", "total_share")
    size_change = _existing_or_pct_change(frame, "size_change_1d", "total_size")
    premium_discount = (
        pd.to_numeric(frame["nav_premium_discount"], errors="coerce")
        if "nav_premium_discount" in frame.columns
        else _ratio(pd.to_numeric(frame["close"], errors="coerce"), pd.to_numeric(frame["nav"], errors="coerce")) - 1.0
    )
    factor_values = {
        "share_change_1d": share_change,
        "share_change_1d_low": -share_change,
        "size_change_1d": size_change,
        "size_change_1d_low": -size_change,
        "nav_premium_discount": premium_discount,
        "nav_premium_discount_low": -premium_discount,
        "total_share_log": _safe_log(frame["total_share"]),
        "total_size_log": _safe_log(frame["total_size"]),
    }
    pieces = [_factor_frame(frame, name, values) for name, values in factor_values.items()]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _existing_or_pct_change(frame: pd.DataFrame, value_column: str, fallback_column: str) -> pd.Series:
    if value_column in frame.columns:
        return pd.to_numeric(frame[value_column], errors="coerce")
    values = pd.to_numeric(frame[fallback_column], errors="coerce")
    return values.groupby(frame["asset_id"], sort=False).pct_change(fill_method=None)


def _ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return (numerator / denominator.where(denominator > 0)).replace([np.inf, -np.inf], np.nan)


def _safe_log(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return np.log(numeric.where(numeric > 0)).replace([np.inf, -np.inf], np.nan)


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
