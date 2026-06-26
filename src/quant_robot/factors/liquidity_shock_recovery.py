from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


LIQUIDITY_SHOCK_RECOVERY_FACTOR_NAMES = (
    "amihud_shock_reversal_recovery_20_5",
    "volume_shock_absorption_reversal_20_5",
    "range_shock_liquidity_recovery_20_10",
    "downside_liquidity_resilience_20",
    "liquidity_recovery_quality_composite_20",
)

_EPSILON = 1e-12


def compute_liquidity_shock_recovery_factors(
    bars: pd.DataFrame,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    _require_columns(
        bars,
        ["date", "asset_id", "market", "adj_close", "high", "low", "amount"],
    )
    requested = _resolve_requested_factor_names(factor_names)
    frame = _feature_frame(bars)
    mask = frame["liquidity_recovery_tradeable"].fillna(False)

    amihud_recovery = (
        _cs_z(frame, -frame["return_5"])
        + 0.75 * _cs_z(frame, frame["amihud_spike_5_20"])
        + 0.75 * _cs_z(frame, frame["impact_absorption_5_20"])
        - 0.35 * _cs_z(frame, frame["downside_vol_20"])
    ).where(mask)
    volume_absorption = (
        _cs_z(frame, -frame["return_5"])
        + 0.60 * _cs_z(frame, frame["amount_shock_5_20"])
        + 0.60 * _cs_z(frame, frame["impact_absorption_5_20"])
        - 0.40 * _cs_z(frame, frame["abs_return_1"])
    ).where(mask)
    range_recovery = (
        _cs_z(frame, -frame["return_10"])
        + 0.65 * _cs_z(frame, frame["range_shock_5_20"])
        + 0.45 * _cs_z(frame, frame["liquidity_stability_20"])
        - 0.45 * _cs_z(frame, frame["hl_range_20"])
    ).where(mask)
    downside_resilience = (
        _cs_z(frame, -frame["downside_vol_20"])
        + 0.55 * _cs_z(frame, frame["liquidity_stability_20"])
        + 0.35 * _cs_z(frame, frame["impact_absorption_5_20"])
        - 0.30 * _cs_z(frame, frame["abs_return_1"])
    ).where(mask)
    composite = pd.concat(
        [amihud_recovery, volume_absorption, range_recovery, downside_resilience],
        axis=1,
    ).mean(axis=1, skipna=True).where(mask)

    values_by_name = {
        "amihud_shock_reversal_recovery_20_5": amihud_recovery,
        "volume_shock_absorption_reversal_20_5": volume_absorption,
        "range_shock_liquidity_recovery_20_10": range_recovery,
        "downside_liquidity_resilience_20": downside_resilience,
        "liquidity_recovery_quality_composite_20": composite,
    }
    pieces = [_factor_frame(frame, name, values_by_name[name]) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return LIQUIDITY_SHOCK_RECOVERY_FACTOR_NAMES
    supported = set(LIQUIDITY_SHOCK_RECOVERY_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported liquidity shock recovery factor_names: {', '.join(unknown)}")
    return factor_names


def _feature_frame(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    pieces: list[pd.DataFrame] = []
    for _, group in frame.groupby("asset_id", sort=False):
        item = group.copy()
        price = pd.to_numeric(item["adj_close"], errors="coerce")
        high = pd.to_numeric(item["high"], errors="coerce")
        low = pd.to_numeric(item["low"], errors="coerce")
        amount = pd.to_numeric(item["amount"], errors="coerce")
        returns = price.pct_change()
        abs_returns = returns.abs()
        adv20 = amount.rolling(20, min_periods=5).mean()
        adv5 = amount.rolling(5, min_periods=3).mean()
        amihud_1 = abs_returns / amount.where(amount > 0.0)
        amihud_20 = amihud_1.rolling(20, min_periods=5).mean()
        amihud_5_max = amihud_1.rolling(5, min_periods=3).max()
        hl_range_1 = high / low.where(low > 0.0) - 1.0
        hl_range_20 = hl_range_1.rolling(20, min_periods=5).mean()

        item["return_1"] = returns
        item["abs_return_1"] = abs_returns
        item["return_5"] = price.pct_change(5)
        item["return_10"] = price.pct_change(10)
        item["adv20_amount"] = adv20
        item["amount_shock_5_20"] = _safe_div(adv5, adv20) - 1.0
        item["liquidity_stability_20"] = _safe_div(amount.rolling(20, min_periods=5).min(), adv20)
        item["amihud_spike_5_20"] = _safe_div(amihud_5_max, amihud_20) - 1.0
        item["current_amihud_pressure"] = _safe_div(amihud_1, amihud_20) - 1.0
        item["impact_absorption_5_20"] = item["amihud_spike_5_20"] - item["current_amihud_pressure"]
        item["hl_range_20"] = hl_range_20
        item["range_shock_5_20"] = _safe_div(
            hl_range_1.rolling(5, min_periods=3).max(),
            hl_range_20,
        ) - 1.0
        item["downside_vol_20"] = returns.clip(upper=0.0).rolling(20, min_periods=5).std(ddof=0)
        pieces.append(item)

    out = pd.concat(pieces, ignore_index=True).replace([np.inf, -np.inf], np.nan)
    out["adv20_rank"] = _cs_rank(out, out["adv20_amount"])
    out["downside_vol_rank"] = _cs_rank(out, out["downside_vol_20"])
    out["range_rank"] = _cs_rank(out, out["hl_range_20"])
    out["liquidity_recovery_tradeable"] = (
        (out["adv20_rank"] > 0.25)
        & (out["downside_vol_rank"] <= 0.90)
        & (out["range_rank"] <= 0.95)
        & (pd.to_numeric(out["abs_return_1"], errors="coerce") <= 0.50)
    )
    return out


def _factor_frame(frame: pd.DataFrame, name: str, values: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": frame["date"].to_numpy(),
            "asset_id": frame["asset_id"].to_numpy(),
            "market": frame["market"].to_numpy(),
            "factor_name": name,
            "factor_value": values.to_numpy(),
            "lookback_window": 20,
        }
    )


def _cs_rank(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.groupby([frame["date"], frame["market"]], sort=False).rank(pct=True)


def _cs_z(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    grouped = numeric.groupby([frame["date"], frame["market"]], sort=False)
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return ((numeric - mean) / std.where(std > _EPSILON)).replace([np.inf, -np.inf], np.nan)


def _safe_div(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    with np.errstate(divide="ignore", invalid="ignore"):
        value = numerator / denominator.replace(0.0, np.nan)
    return value.replace([np.inf, -np.inf], np.nan)


def _require_columns(frame: pd.DataFrame, required: list[str]) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Bars are missing columns for liquidity shock recovery factor calculation: {', '.join(missing)}")
