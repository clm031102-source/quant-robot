from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.ops.daily_basic_non_price_public_carry_prescreen import (
    compute_daily_basic_non_price_public_carry_factors,
    default_daily_basic_non_price_public_carry_specs,
)
from quant_robot.schema.factors import FACTOR_COLUMNS


DAILY_BASIC_VALUE_YIELD_RISK_REPAIR_FACTOR_NAMES = (
    "daily_basic_value_yield_lowtail_guard_20",
    "daily_basic_value_yield_crash_penalty_60",
    "daily_basic_value_yield_liquid_defensive_20",
    "daily_basic_value_yield_balanced_repair_20",
)


def compute_daily_basic_value_yield_risk_repair_factors(
    bars: pd.DataFrame,
    daily_basic_inputs: pd.DataFrame,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    requested = _resolve_requested_factor_names(factor_names)
    _require_columns(bars, ["date", "asset_id", "market", "adj_close", "high", "low", "amount"], "bars")
    _require_columns(daily_basic_inputs, ["date", "asset_id", "market"], "daily-basic inputs")
    base = _base_value_yield_factor(daily_basic_inputs)
    risk = _risk_feature_frame(bars)
    frame = base.merge(risk, on=["date", "asset_id", "market"], how="inner", validate="one_to_one")
    values = _candidate_values(frame)
    pieces = [_factor_frame(frame, name, values[name]) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return DAILY_BASIC_VALUE_YIELD_RISK_REPAIR_FACTOR_NAMES
    supported = set(DAILY_BASIC_VALUE_YIELD_RISK_REPAIR_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported daily-basic value-yield risk-repair factor_names: {', '.join(unknown)}")
    return factor_names


def _base_value_yield_factor(daily_basic_inputs: pd.DataFrame) -> pd.DataFrame:
    specs = [
        spec
        for spec in default_daily_basic_non_price_public_carry_specs()
        if spec.factor_name == "daily_basic_value_yield_size_neutral_20"
    ]
    base = compute_daily_basic_non_price_public_carry_factors(daily_basic_inputs, candidate_specs=specs)
    base = base[base["factor_name"] == "daily_basic_value_yield_size_neutral_20"].copy()
    base["date"] = pd.to_datetime(base["date"])
    return base[["date", "asset_id", "market", "factor_value"]].rename(columns={"factor_value": "base_value_yield"})


def _risk_feature_frame(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str)
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    pieces: list[pd.DataFrame] = []
    for _, group in frame.groupby("asset_id", sort=False):
        item = group.copy()
        price = pd.to_numeric(item["adj_close"], errors="coerce")
        high = pd.to_numeric(item["high"], errors="coerce")
        low = pd.to_numeric(item["low"], errors="coerce")
        amount = pd.to_numeric(item["amount"], errors="coerce")
        returns = price.pct_change()
        adv20 = amount.rolling(20, min_periods=5).mean()
        item["return_1d"] = returns
        item["adv20_amount"] = adv20
        item["log_adv20"] = np.log(adv20.where(adv20 > 0.0))
        item["downside_vol_20"] = returns.clip(upper=0.0).rolling(20, min_periods=5).std(ddof=0)
        item["realized_vol_20"] = returns.rolling(20, min_periods=5).std(ddof=0)
        item["drawdown_resilience_60"] = price / price.rolling(60, min_periods=20).max() - 1.0
        item["max_abs_return_20"] = returns.abs().rolling(20, min_periods=5).max()
        item["range_20"] = ((high / low.where(low > 0.0)) - 1.0).rolling(20, min_periods=5).mean()
        item["amount_stability_20"] = amount.rolling(20, min_periods=5).min() / adv20.replace(0.0, np.nan)
        pieces.append(
            item[
                [
                    "date",
                    "asset_id",
                    "market",
                    "return_1d",
                    "adv20_amount",
                    "log_adv20",
                    "downside_vol_20",
                    "realized_vol_20",
                    "drawdown_resilience_60",
                    "max_abs_return_20",
                    "range_20",
                    "amount_stability_20",
                ]
            ]
        )
    out = pd.concat(pieces, ignore_index=True).replace([np.inf, -np.inf], np.nan)
    out["adv20_rank"] = _cs_rank(out, out["adv20_amount"])
    out["downside_vol_rank"] = _cs_rank(out, out["downside_vol_20"])
    out["drawdown_rank"] = _cs_rank(out, out["drawdown_resilience_60"])
    out["risk_repair_tradeable"] = (
        (out["adv20_rank"] >= 0.40)
        & (out["downside_vol_rank"] <= 0.70)
        & (out["drawdown_rank"] >= 0.25)
        & (pd.to_numeric(out["return_1d"], errors="coerce").abs() <= 0.20)
        & (pd.to_numeric(out["amount_stability_20"], errors="coerce") >= 0.20)
    )
    return out


def _candidate_values(frame: pd.DataFrame) -> dict[str, pd.Series]:
    base = _cs_z(frame, frame["base_value_yield"]).fillna(0.0)
    low_tail = _cs_z(frame, -frame["downside_vol_20"]).fillna(0.0)
    drawdown = _cs_z(frame, frame["drawdown_resilience_60"]).fillna(0.0)
    crash_penalty = _cs_z(frame, frame["max_abs_return_20"]).fillna(0.0)
    range_penalty = _cs_z(frame, frame["range_20"]).fillna(0.0)
    liquidity = _cs_z(frame, frame["log_adv20"]).fillna(0.0)
    amount_stability = _cs_z(frame, frame["amount_stability_20"]).fillna(0.0)
    realized_vol = _cs_z(frame, frame["realized_vol_20"]).fillna(0.0)
    lowtail_guard = base + 0.70 * low_tail + 0.40 * drawdown + 0.20 * amount_stability
    crash_penalty_signal = base + 0.55 * drawdown - 0.70 * crash_penalty - 0.35 * range_penalty
    liquid_defensive = base + 0.35 * liquidity + 0.35 * amount_stability - 0.55 * realized_vol
    balanced = pd.concat([lowtail_guard, crash_penalty_signal, liquid_defensive], axis=1).mean(axis=1, skipna=False)
    mask = frame["risk_repair_tradeable"].fillna(False)
    return {
        "daily_basic_value_yield_lowtail_guard_20": lowtail_guard.where(mask),
        "daily_basic_value_yield_crash_penalty_60": crash_penalty_signal.where(mask),
        "daily_basic_value_yield_liquid_defensive_20": liquid_defensive.where(mask),
        "daily_basic_value_yield_balanced_repair_20": balanced.where(mask),
    }


def _factor_frame(frame: pd.DataFrame, name: str, values: pd.Series) -> pd.DataFrame:
    lookback = 60 if name.endswith("_60") else 20
    return pd.DataFrame(
        {
            "date": frame["date"].to_numpy(),
            "asset_id": frame["asset_id"].to_numpy(),
            "market": frame["market"].to_numpy(),
            "factor_name": name,
            "factor_value": values.to_numpy(),
            "lookback_window": lookback,
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
    return ((numeric - mean) / std.where(std > 1e-12)).replace([np.inf, -np.inf], np.nan)


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} are missing columns: {', '.join(missing)}")
