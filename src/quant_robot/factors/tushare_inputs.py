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
