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
)


def compute_daily_basic_factors(inputs: pd.DataFrame) -> pd.DataFrame:
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
    frame = inputs.sort_values(["asset_id", "date"]).copy()
    factor_values = {
        "turnover_rate": pd.to_numeric(frame["turnover_rate"], errors="coerce"),
        "turnover_rate_f": pd.to_numeric(frame["turnover_rate_f"], errors="coerce"),
        "volume_ratio": pd.to_numeric(frame["volume_ratio"], errors="coerce"),
        "turnover_rate_low": _negative(frame["turnover_rate"]),
        "turnover_rate_f_low": _negative(frame["turnover_rate_f"]),
        "volume_ratio_low": _negative(frame["volume_ratio"]),
        "pe_ttm_inverse": _safe_inverse(frame["pe_ttm"]),
        "pb_inverse": _safe_inverse(frame["pb"]),
        "ps_ttm_inverse": _safe_inverse(frame["ps_ttm"]),
        "dv_ttm": pd.to_numeric(frame["dv_ttm"], errors="coerce"),
        "total_mv_log": _safe_log(frame["total_mv"]),
        "circ_mv_log": _safe_log(frame["circ_mv"]),
    }
    pieces = [_factor_frame(frame, name, values) for name, values in factor_values.items()]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _safe_inverse(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return (1.0 / numeric.where(numeric > 0)).replace([np.inf, -np.inf], np.nan)


def _negative(values: pd.Series) -> pd.Series:
    return -pd.to_numeric(values, errors="coerce")


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
