from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant_robot.factors.technical import compute_basic_factors
from quant_robot.factors.tushare_moneyflow import compute_moneyflow_factors
from quant_robot.schema.factors import FACTOR_COLUMNS


@dataclass(frozen=True)
class ComboFactorSpec:
    moneyflow_factor: str
    technical_factor: str
    operation: str
    lookback_window: int
    economic_meaning: str


MONEYFLOW_TECHNICAL_COMBO_SPECS: dict[str, ComboFactorSpec] = {
    "mf_low_plus_momentum_5": ComboFactorSpec(
        "net_mf_amount_ratio_low",
        "momentum_5",
        "+",
        5,
        "Low net moneyflow blended with short-term momentum.",
    ),
    "mf_low_plus_reversal_5": ComboFactorSpec(
        "net_mf_amount_ratio_low",
        "reversal_5",
        "+",
        5,
        "Low net moneyflow blended with short-term reversal.",
    ),
    "mf_low_minus_volatility_20": ComboFactorSpec(
        "net_mf_amount_ratio_low",
        "volatility_20",
        "-",
        20,
        "Low net moneyflow penalized by 20-day volatility.",
    ),
    "large_plus_momentum_5": ComboFactorSpec(
        "large_order_net_amount_ratio",
        "momentum_5",
        "+",
        5,
        "Large-order net inflow blended with short-term momentum.",
    ),
    "large_plus_risk_momentum_10": ComboFactorSpec(
        "large_order_net_amount_ratio",
        "risk_adjusted_momentum_10",
        "+",
        10,
        "Large-order net inflow blended with risk-adjusted momentum.",
    ),
    "large_minus_liquidity_20": ComboFactorSpec(
        "large_order_net_amount_ratio",
        "liquidity_20",
        "-",
        20,
        "Large-order net inflow penalized by Amihud-style illiquidity.",
    ),
    "extra_plus_momentum_10": ComboFactorSpec(
        "extra_large_order_net_amount_ratio",
        "momentum_10",
        "+",
        10,
        "Extra-large-order net inflow blended with medium-term momentum.",
    ),
    "extra_low_plus_reversal_5": ComboFactorSpec(
        "extra_large_order_net_amount_ratio_low",
        "reversal_5",
        "+",
        5,
        "Low extra-large-order flow blended with short-term reversal.",
    ),
    "small_sell_plus_reversal_5": ComboFactorSpec(
        "small_order_sell_pressure",
        "reversal_5",
        "+",
        5,
        "Small-order sell pressure blended with short-term reversal.",
    ),
    "small_sell_low_plus_momentum_5": ComboFactorSpec(
        "small_order_sell_pressure_low",
        "momentum_5",
        "+",
        5,
        "Low small-order sell pressure blended with short-term momentum.",
    ),
}

MONEYFLOW_TECHNICAL_COMBO_FACTOR_NAMES = tuple(MONEYFLOW_TECHNICAL_COMBO_SPECS)


def compute_moneyflow_technical_combo_factors(
    bars: pd.DataFrame,
    moneyflow_inputs: pd.DataFrame,
    factor_names: tuple[str, ...] = MONEYFLOW_TECHNICAL_COMBO_FACTOR_NAMES,
) -> pd.DataFrame:
    unknown = [name for name in factor_names if name not in MONEYFLOW_TECHNICAL_COMBO_SPECS]
    if unknown:
        raise ValueError(f"Unsupported moneyflow technical combo factors: {', '.join(unknown)}")
    specs = {name: MONEYFLOW_TECHNICAL_COMBO_SPECS[name] for name in factor_names}
    windows = tuple(sorted({spec.lookback_window for spec in specs.values()}))
    moneyflow = _with_cross_sectional_zscore(compute_moneyflow_factors(moneyflow_inputs))
    technical = _with_cross_sectional_zscore(compute_basic_factors(bars, windows=windows))
    pieces = [_combo_frame(name, spec, moneyflow, technical) for name, spec in specs.items()]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _with_cross_sectional_zscore(factors: pd.DataFrame) -> pd.DataFrame:
    frame = factors.copy()
    if frame.empty:
        frame["z_factor_value"] = pd.Series(dtype=float)
        return frame
    frame["z_factor_value"] = frame.groupby(["date", "market", "factor_name"], group_keys=False)[
        "factor_value"
    ].transform(_zscore)
    return frame


def _zscore(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    std = float(numeric.std(ddof=0))
    if not np.isfinite(std) or std <= 1e-12:
        return pd.Series(np.nan, index=values.index)
    return (numeric - float(numeric.mean())) / std


def _combo_frame(
    name: str,
    spec: ComboFactorSpec,
    moneyflow: pd.DataFrame,
    technical: pd.DataFrame,
) -> pd.DataFrame:
    keys = ["date", "asset_id", "market"]
    left = moneyflow.loc[moneyflow["factor_name"] == spec.moneyflow_factor, keys + ["z_factor_value"]]
    right = technical.loc[technical["factor_name"] == spec.technical_factor, keys + ["z_factor_value"]]
    merged = left.merge(right, on=keys, how="inner", suffixes=("_moneyflow", "_technical"))
    sign = 1.0 if spec.operation == "+" else -1.0
    values = merged["z_factor_value_moneyflow"] + sign * merged["z_factor_value_technical"]
    return pd.DataFrame(
        {
            "date": merged["date"].to_numpy(),
            "asset_id": merged["asset_id"].to_numpy(),
            "market": merged["market"].to_numpy(),
            "factor_name": name,
            "factor_value": values.to_numpy(),
            "lookback_window": spec.lookback_window,
        }
    )
