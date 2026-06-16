from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


MONEYFLOW_FACTOR_NAMES = (
    "net_mf_amount_ratio",
    "net_mf_amount_ratio_low",
    "large_order_net_amount_ratio",
    "large_order_net_amount_ratio_low",
    "extra_large_order_net_amount_ratio",
    "extra_large_order_net_amount_ratio_low",
    "small_order_sell_pressure",
    "small_order_sell_pressure_low",
)


def compute_moneyflow_factors(inputs: pd.DataFrame) -> pd.DataFrame:
    required = [
        "date",
        "asset_id",
        "market",
        "buy_sm_amount",
        "sell_sm_amount",
        "buy_md_amount",
        "sell_md_amount",
        "buy_lg_amount",
        "sell_lg_amount",
        "buy_elg_amount",
        "sell_elg_amount",
        "net_mf_amount",
    ]
    missing = [column for column in required if column not in inputs.columns]
    if missing:
        raise ValueError(f"Moneyflow inputs are missing columns: {', '.join(missing)}")
    frame = inputs.sort_values(["asset_id", "date"]).copy()
    denominator = _total_flow_amount(frame)
    net_mf = _ratio(frame["net_mf_amount"], denominator)
    large_order_net = _ratio(
        _number(frame["buy_lg_amount"])
        + _number(frame["buy_elg_amount"])
        - _number(frame["sell_lg_amount"])
        - _number(frame["sell_elg_amount"]),
        denominator,
    )
    extra_large_net = _ratio(_number(frame["buy_elg_amount"]) - _number(frame["sell_elg_amount"]), denominator)
    small_sell_pressure = _ratio(_number(frame["sell_sm_amount"]) - _number(frame["buy_sm_amount"]), denominator)
    factor_values = {
        "net_mf_amount_ratio": net_mf,
        "net_mf_amount_ratio_low": -net_mf,
        "large_order_net_amount_ratio": large_order_net,
        "large_order_net_amount_ratio_low": -large_order_net,
        "extra_large_order_net_amount_ratio": extra_large_net,
        "extra_large_order_net_amount_ratio_low": -extra_large_net,
        "small_order_sell_pressure": small_sell_pressure,
        "small_order_sell_pressure_low": -small_sell_pressure,
    }
    pieces = [_factor_frame(frame, name, values) for name, values in factor_values.items()]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _total_flow_amount(frame: pd.DataFrame) -> pd.Series:
    amount_columns = [
        "buy_sm_amount",
        "sell_sm_amount",
        "buy_md_amount",
        "sell_md_amount",
        "buy_lg_amount",
        "sell_lg_amount",
        "buy_elg_amount",
        "sell_elg_amount",
    ]
    total = sum(_number(frame[column]).abs() for column in amount_columns)
    return total.where(total > 0)


def _ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return (_number(numerator) / denominator).replace([np.inf, -np.inf], np.nan)


def _number(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce")


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
