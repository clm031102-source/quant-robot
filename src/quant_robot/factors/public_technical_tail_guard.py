from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.factors.public_technical import _bollinger_reversal, _rsi
from quant_robot.schema.factors import FACTOR_COLUMNS


PUBLIC_TECHNICAL_TAIL_GUARD_FACTOR_NAMES = (
    "rsi_reversal_liquid_low_tail_14_20",
    "bollinger_reversal_liquid_low_tail_20",
)


def compute_public_technical_tail_guard_factors(
    bars: pd.DataFrame,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "high", "low", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing columns for public technical tail-guard factor calculation: {', '.join(missing)}")
    requested = _resolve_requested_factor_names(factor_names)

    frame = _feature_frame(bars)
    values_by_name = {
        "rsi_reversal_liquid_low_tail_14_20": _tail_guard_score(frame, "rsi_reversal_14"),
        "bollinger_reversal_liquid_low_tail_20": _tail_guard_score(frame, "bollinger_reversal_20"),
    }
    pieces = [_factor_frame(frame, name, values_by_name[name]) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return PUBLIC_TECHNICAL_TAIL_GUARD_FACTOR_NAMES
    supported = set(PUBLIC_TECHNICAL_TAIL_GUARD_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported public technical tail-guard factor_names: {', '.join(unknown)}")
    return factor_names


def _feature_frame(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    pieces = []
    for _, group in frame.groupby("asset_id", sort=False):
        item = group.copy()
        price = pd.to_numeric(item["adj_close"], errors="coerce")
        high = pd.to_numeric(item["high"], errors="coerce")
        low = pd.to_numeric(item["low"], errors="coerce")
        amount = pd.to_numeric(item["amount"], errors="coerce")
        returns = price.pct_change()
        rolling_high = high.rolling(20).max()
        rolling_low = low.rolling(20).min()
        item["return_1d"] = returns
        item["adv20_amount"] = amount.rolling(20).mean()
        item["rsi_reversal_14"] = 100.0 - _rsi(price, 14)
        item["bollinger_reversal_20"] = _bollinger_reversal(price, 20)
        item["downside_vol_20"] = returns.clip(upper=0.0).rolling(20).std(ddof=0)
        item["hl_range_20"] = ((high / low.replace(0.0, np.nan)) - 1.0).rolling(20).mean()
        item["range_position_20"] = (price - rolling_low) / (rolling_high - rolling_low).replace(0.0, np.nan)
        pieces.append(item)
    out = pd.concat(pieces, ignore_index=True)
    out["adv20_rank"] = _cs_rank(out, out["adv20_amount"])
    out["downside_vol_rank"] = _cs_rank(out, out["downside_vol_20"])
    out["hl_range_rank"] = _cs_rank(out, out["hl_range_20"])
    out["log_adv20"] = np.log(pd.to_numeric(out["adv20_amount"], errors="coerce").where(out["adv20_amount"] > 0.0))
    out["tail_guard_tradeable"] = (
        (out["adv20_rank"] >= 0.50)
        & (out["downside_vol_rank"] <= 0.75)
        & (out["hl_range_rank"] <= 0.75)
        & (pd.to_numeric(out["range_position_20"], errors="coerce") >= 0.15)
        & (pd.to_numeric(out["return_1d"], errors="coerce").abs() <= 0.50)
    )
    return out


def _tail_guard_score(
    frame: pd.DataFrame,
    signal_column: str,
    *,
    signal_weight: float = 0.70,
) -> pd.Series:
    signal = _cs_z(frame, frame[signal_column])
    liquidity = _cs_z(frame, frame["log_adv20"])
    downside_low = -_cs_z(frame, frame["downside_vol_20"])
    value = signal_weight * signal + 0.20 * liquidity + 0.10 * downside_low
    return value.where(frame["tail_guard_tradeable"].fillna(False))


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
