from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant_robot.factors.technical import compute_basic_factors
from quant_robot.factors.tushare_moneyflow import compute_moneyflow_factors
from quant_robot.schema.factors import FACTOR_COLUMNS


@dataclass(frozen=True)
class ComboFactorSpec:
    moneyflow_factor: str
    technical_factor: str | tuple[str, ...]
    operation: str
    lookback_window: int
    economic_meaning: str
    liquidity_gate_quantile: float | None = None
    liquidity_gate_factor: str | None = None
    amount_floor: float | None = None


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
    "large_resid_liquidity_20": ComboFactorSpec(
        "large_order_net_amount_ratio",
        "liquidity_20",
        "residual",
        20,
        "Large-order net inflow residualized against same-day Amihud-style illiquidity.",
    ),
    "large_resid_liquidity_gate_20": ComboFactorSpec(
        "large_order_net_amount_ratio",
        "liquidity_20",
        "residual",
        20,
        "Large-order net inflow residualized against same-day Amihud-style illiquidity, restricted to the more liquid half of the cross-section.",
        liquidity_gate_quantile=0.5,
        liquidity_gate_factor="liquidity_20",
    ),
    "large_resid_liq_vol_amt_20": ComboFactorSpec(
        "large_order_net_amount_ratio",
        ("liquidity_20", "volatility_20", "log_amount_20"),
        "residual",
        20,
        "Large-order net inflow residualized against same-day liquidity, volatility, and log traded amount.",
    ),
    "large_resid_liq_vol_amt_gate_20": ComboFactorSpec(
        "large_order_net_amount_ratio",
        ("liquidity_20", "volatility_20", "log_amount_20"),
        "residual",
        20,
        "Large-order net inflow residualized against same-day liquidity, volatility, and log traded amount, restricted to signal-day amount >= 100m.",
        amount_floor=100_000_000.0,
    ),
    "large_liquidity_gate_20": ComboFactorSpec(
        "large_order_net_amount_ratio",
        "liquidity_20",
        "gate",
        20,
        "Large-order net inflow restricted to the more liquid half of the cross-section.",
        liquidity_gate_quantile=0.5,
    ),
    "mf_low_minus_volatility_liquidity_gate_20": ComboFactorSpec(
        "net_mf_amount_ratio_low",
        "volatility_20",
        "-",
        20,
        "Low net moneyflow penalized by 20-day volatility and restricted to the more liquid half of the cross-section.",
        liquidity_gate_quantile=0.5,
        liquidity_gate_factor="liquidity_20",
    ),
    "large_plus_risk_momentum_liquidity_gate_10": ComboFactorSpec(
        "large_order_net_amount_ratio",
        "risk_adjusted_momentum_10",
        "+",
        10,
        "Large-order net inflow blended with risk-adjusted momentum and restricted to the more liquid half of the cross-section.",
        liquidity_gate_quantile=0.5,
        liquidity_gate_factor="liquidity_10",
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
    moneyflow = _with_cross_sectional_zscore(
        compute_moneyflow_factors(moneyflow_inputs, factor_names=_required_moneyflow_factor_names(specs.values()))
    )
    required_technical = _required_technical_factor_names(specs.values())
    technical_raw = (
        compute_basic_factors(bars, windows=windows, factor_names=required_technical)
        if required_technical
        else pd.DataFrame(columns=FACTOR_COLUMNS)
    )
    log_amount = _compute_log_amount_factors(bars, _required_log_amount_windows(specs.values()))
    technical = _with_cross_sectional_zscore(pd.concat([technical_raw, log_amount], ignore_index=True))
    pieces = [_combo_frame(name, spec, moneyflow, technical, bars) for name, spec in specs.items()]
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
    bars: pd.DataFrame,
) -> pd.DataFrame:
    keys = ["date", "asset_id", "market"]
    left = moneyflow.loc[moneyflow["factor_name"] == spec.moneyflow_factor, keys + ["z_factor_value"]]
    merged = left.rename(columns={"z_factor_value": "z_factor_value_moneyflow"})
    exposure_names = _exposure_factor_names(spec)
    for index, factor_name in enumerate(exposure_names):
        right = technical.loc[technical["factor_name"] == factor_name, keys + ["z_factor_value"]].rename(
            columns={"z_factor_value": f"z_factor_value_exposure_{index}"}
        )
        merged = merged.merge(right, on=keys, how="inner")
    if spec.liquidity_gate_factor is not None:
        if spec.liquidity_gate_factor in exposure_names:
            gate_index = exposure_names.index(spec.liquidity_gate_factor)
            merged["z_factor_value_gate"] = merged[f"z_factor_value_exposure_{gate_index}"]
        else:
            gate = technical.loc[
                technical["factor_name"] == spec.liquidity_gate_factor,
                keys + ["z_factor_value"],
            ].rename(columns={"z_factor_value": "z_factor_value_gate"})
            merged = merged.merge(gate, on=keys, how="inner")
    amount = bars.loc[:, keys + ["amount"]].drop_duplicates(subset=keys)
    merged = merged.merge(amount, on=keys, how="left")
    exposure_columns = [f"z_factor_value_exposure_{index}" for index, _ in enumerate(exposure_names)]
    values = _combo_values(merged, spec, exposure_columns)
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


def _combo_values(merged: pd.DataFrame, spec: ComboFactorSpec, exposure_columns: list[str]) -> pd.Series:
    moneyflow = merged["z_factor_value_moneyflow"]
    exposures = merged.loc[:, exposure_columns]
    primary_exposure = exposures.iloc[:, 0]
    if spec.operation == "+":
        _require_single_exposure(spec)
        values = moneyflow + primary_exposure
    elif spec.operation == "-":
        _require_single_exposure(spec)
        values = moneyflow - primary_exposure
    elif spec.operation == "gate":
        _require_single_exposure(spec)
        values = moneyflow.copy()
    elif spec.operation == "residual":
        values = _cross_sectional_residuals(merged, moneyflow, exposures)
    else:
        raise ValueError(f"Unsupported combo operation: {spec.operation}")
    if spec.liquidity_gate_quantile is not None:
        gate = merged["z_factor_value_gate"] if "z_factor_value_gate" in merged else primary_exposure
        values = values.where(_liquidity_gate_mask(merged, gate, spec.liquidity_gate_quantile))
    if spec.amount_floor is not None:
        values = values.where(_amount_gate_mask(merged, spec.amount_floor))
    return values


def _cross_sectional_residuals(merged: pd.DataFrame, target: pd.Series, exposures: pd.DataFrame) -> pd.Series:
    values = pd.Series(np.nan, index=merged.index, dtype=float)
    for _, group in merged.groupby(["date", "market"], sort=False):
        x = exposures.loc[group.index].apply(pd.to_numeric, errors="coerce")
        y = pd.to_numeric(target.loc[group.index], errors="coerce")
        finite = x.notna().all(axis=1) & y.notna()
        if int(finite.sum()) <= x.shape[1]:
            continue
        x_clean = x.loc[finite]
        y_clean = y.loc[finite]
        design = np.column_stack([np.ones(len(x_clean)), x_clean.to_numpy(dtype=float)])
        if int(np.linalg.matrix_rank(design)) <= x.shape[1]:
            continue
        beta, *_ = np.linalg.lstsq(design, y_clean.to_numpy(dtype=float), rcond=None)
        values.loc[x_clean.index] = y_clean.to_numpy(dtype=float) - design @ beta
    return values


def _liquidity_gate_mask(merged: pd.DataFrame, liquidity: pd.Series, quantile: float) -> pd.Series:
    if not 0.0 < quantile <= 1.0:
        raise ValueError("liquidity_gate_quantile must be greater than 0 and at most 1")
    numeric = pd.to_numeric(liquidity, errors="coerce")
    thresholds = numeric.groupby([merged["date"], merged["market"]], sort=False).transform(
        lambda values: values.quantile(quantile)
    )
    return numeric.notna() & (numeric <= thresholds)


def _amount_gate_mask(merged: pd.DataFrame, amount_floor: float) -> pd.Series:
    if amount_floor <= 0:
        raise ValueError("amount_floor must be greater than 0")
    numeric = pd.to_numeric(merged["amount"], errors="coerce")
    return numeric.notna() & (numeric >= amount_floor)


def _exposure_factor_names(spec: ComboFactorSpec) -> tuple[str, ...]:
    if isinstance(spec.technical_factor, str):
        return (spec.technical_factor,)
    return spec.technical_factor


def _require_single_exposure(spec: ComboFactorSpec) -> None:
    if len(_exposure_factor_names(spec)) != 1:
        raise ValueError(f"Combo operation {spec.operation} requires exactly one technical exposure")


def _required_log_amount_windows(specs: Iterable[ComboFactorSpec]) -> tuple[int, ...]:
    windows: set[int] = set()
    for spec in specs:
        for factor_name in _exposure_factor_names(spec):
            if factor_name.startswith("log_amount_"):
                windows.add(int(factor_name.rsplit("_", 1)[1]))
    return tuple(sorted(windows))


def _required_moneyflow_factor_names(specs: Iterable[ComboFactorSpec]) -> tuple[str, ...]:
    return _unique_preserving_order(spec.moneyflow_factor for spec in specs)


def _required_technical_factor_names(specs: Iterable[ComboFactorSpec]) -> tuple[str, ...]:
    names = []
    for spec in specs:
        names.extend(name for name in _exposure_factor_names(spec) if not name.startswith("log_amount_"))
        if spec.liquidity_gate_factor is not None and not spec.liquidity_gate_factor.startswith("log_amount_"):
            names.append(spec.liquidity_gate_factor)
    return _unique_preserving_order(names)


def _unique_preserving_order(names: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    unique = []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        unique.append(name)
    return tuple(unique)


def _compute_log_amount_factors(bars: pd.DataFrame, windows: tuple[int, ...]) -> pd.DataFrame:
    if not windows:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    keys = ["date", "asset_id", "market"]
    amount = bars.loc[:, keys + ["amount"]].copy()
    amount["factor_value"] = np.log1p(pd.to_numeric(amount["amount"], errors="coerce"))
    amount.loc[pd.to_numeric(amount["amount"], errors="coerce") <= 0, "factor_value"] = np.nan
    frames = []
    for window in windows:
        frame = amount.loc[:, keys + ["factor_value"]].copy()
        frame["factor_name"] = f"log_amount_{window}"
        frame["lookback_window"] = window
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)[FACTOR_COLUMNS]
