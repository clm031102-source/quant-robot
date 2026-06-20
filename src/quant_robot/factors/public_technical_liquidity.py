from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.factors.public_technical import _bollinger_reversal, _rsi
from quant_robot.schema.factors import FACTOR_COLUMNS


PUBLIC_TECHNICAL_LIQUIDITY_FACTOR_NAMES = (
    "rsi_reversal_liquid_14_20",
    "bollinger_reversal_liquid_20",
)


def compute_public_technical_liquidity_factors(
    bars: pd.DataFrame,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "high", "low", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing columns for public technical liquidity factor calculation: {', '.join(missing)}")
    requested = _resolve_requested_factor_names(factor_names)

    frame = _feature_frame(bars)
    values_by_name = {
        "rsi_reversal_liquid_14_20": _liquid_mean_reversion_score(frame, "rsi_reversal_14"),
        "bollinger_reversal_liquid_20": _liquid_mean_reversion_score(frame, "bollinger_reversal_20"),
    }
    pieces = [_factor_frame(frame, name, values_by_name[name]) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return PUBLIC_TECHNICAL_LIQUIDITY_FACTOR_NAMES
    supported = set(PUBLIC_TECHNICAL_LIQUIDITY_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported public technical liquidity factor_names: {', '.join(unknown)}")
    return factor_names


def _feature_frame(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    pieces = []
    for _, group in frame.groupby("asset_id", sort=False):
        item = group.copy()
        price = pd.to_numeric(item["adj_close"], errors="coerce")
        amount = pd.to_numeric(item["amount"], errors="coerce")
        item["return_1d"] = price.pct_change()
        item["adv20_amount"] = amount.rolling(20).mean()
        item["rsi_reversal_14"] = 100.0 - _rsi(price, 14)
        item["bollinger_reversal_20"] = _bollinger_reversal(price, 20)
        pieces.append(item)
    out = pd.concat(pieces, ignore_index=True)
    out["adv20_rank"] = _cs_rank(out, out["adv20_amount"])
    out["log_adv20"] = np.log(pd.to_numeric(out["adv20_amount"], errors="coerce").where(out["adv20_amount"] > 0.0))
    out["tradeable_public_technical"] = (
        (out["adv20_rank"] >= 0.60)
        & (pd.to_numeric(out["return_1d"], errors="coerce").abs() <= 0.50)
    )
    return out


def _liquid_mean_reversion_score(
    frame: pd.DataFrame,
    signal_column: str,
    *,
    signal_weight: float = 0.75,
) -> pd.Series:
    liquidity_weight = 1.0 - signal_weight
    signal = _cs_z(frame, frame[signal_column])
    liquidity = _cs_z(frame, frame["log_adv20"])
    value = signal_weight * signal + liquidity_weight * liquidity
    return value.where(frame["tradeable_public_technical"].fillna(False))


def _cs_rank(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.groupby([frame["date"], frame["market"]], sort=False).rank(pct=True)


def _cs_z(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    grouped = numeric.groupby([frame["date"], frame["market"]], sort=False)
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return ((numeric - mean) / std.where(std > 1e-12)).replace([np.inf, -np.inf], np.nan)


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
