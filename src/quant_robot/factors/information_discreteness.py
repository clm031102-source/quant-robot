from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


INFORMATION_DISCRETENESS_FACTOR_NAMES = (
    "fip_smooth_momentum_quality_60_20",
    "fip_smooth_momentum_skip5_60",
    "fip_continuous_accumulation_low_jump_20_60",
    "fip_discrete_jump_reversal_20_5",
    "fip_smooth_pullback_resilience_60_20",
    "fip_volume_confirmed_smooth_trend_20_60",
)


def compute_information_discreteness_factors(
    bars: pd.DataFrame,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(
            "Bars are missing columns for information-discreteness factor calculation: "
            + ", ".join(missing)
        )
    requested = _resolve_requested_factor_names(factor_names)

    frame = _feature_frame(bars)
    mask = frame["state_tradeable"].fillna(False)
    smooth_momentum = (
        _cs_z(frame, frame["return_60"])
        + 0.70 * _cs_z(frame, frame["information_continuity_60"])
        - 0.40 * _cs_z(frame, frame["jump_share_20"])
        - 0.25 * _cs_z(frame, frame["realized_vol_20"])
    ).where(mask)
    skip_momentum = (
        _cs_z(frame, frame["skip5_return_60"])
        + 0.70 * _cs_z(frame, frame["skip5_information_continuity_60"])
        - 0.25 * _cs_z(frame, frame["realized_vol_20"])
    ).where(mask)
    accumulation_low_jump = (
        _cs_z(frame, frame["return_20"])
        + 0.50 * _cs_z(frame, frame["return_60"])
        + 0.70 * _cs_z(frame, frame["information_continuity_60"])
        - 0.80 * _cs_z(frame, frame["jump_share_20"])
    ).where(mask)
    discrete_jump_reversal = (
        -_cs_z(frame, frame["return_20"])
        + 0.80 * _cs_z(frame, frame["jump_share_20"])
        - 0.25 * _cs_z(frame, frame["realized_vol_20"])
    ).where(mask)
    smooth_pullback = (
        _cs_z(frame, frame["return_60"])
        + 0.60 * _cs_z(frame, -frame["return_20"])
        + 0.50 * _cs_z(frame, frame["information_continuity_60"])
        - 0.30 * _cs_z(frame, frame["jump_share_20"])
    ).where(mask)
    volume_confirmed = (
        _cs_z(frame, frame["return_60"])
        + 0.60 * _cs_z(frame, frame["path_smoothness_60"])
        + 0.50 * _cs_z(frame, frame["amount_trend_20_60"])
        - 0.40 * _cs_z(frame, frame["jump_share_20"])
    ).where(mask)

    values_by_name = {
        "fip_smooth_momentum_quality_60_20": smooth_momentum,
        "fip_smooth_momentum_skip5_60": skip_momentum,
        "fip_continuous_accumulation_low_jump_20_60": accumulation_low_jump,
        "fip_discrete_jump_reversal_20_5": discrete_jump_reversal,
        "fip_smooth_pullback_resilience_60_20": smooth_pullback,
        "fip_volume_confirmed_smooth_trend_20_60": volume_confirmed,
    }
    pieces = [_factor_frame(frame, name, values_by_name[name]) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return INFORMATION_DISCRETENESS_FACTOR_NAMES
    supported = set(INFORMATION_DISCRETENESS_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported information-discreteness factor_names: {', '.join(unknown)}")
    return factor_names


def _feature_frame(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    pieces: list[pd.DataFrame] = []
    for _, group in frame.groupby("asset_id", sort=False):
        item = group.copy()
        price = pd.to_numeric(item["adj_close"], errors="coerce")
        amount = pd.to_numeric(item["amount"], errors="coerce")
        returns = price.pct_change()
        shifted_returns = returns.shift(5)

        item["return_1d"] = returns
        item["return_5"] = price.pct_change(5)
        item["return_20"] = price.pct_change(20)
        item["return_60"] = price.pct_change(60)
        item["skip5_return_60"] = price.shift(5) / price.shift(65) - 1.0
        item["amount_20"] = amount.rolling(20, min_periods=5).mean()
        item["amount_trend_20_60"] = item["amount_20"] / _nonzero(amount.rolling(60, min_periods=20).mean()) - 1.0
        item["realized_vol_20"] = returns.rolling(20, min_periods=5).std(ddof=0)
        item["path_smoothness_20"] = _path_smoothness(returns, price.pct_change(20), 20)
        item["path_smoothness_60"] = _path_smoothness(returns, item["return_60"], 60)
        item["sign_consistency_20"] = _sign_consistency(returns, 20)
        item["sign_consistency_60"] = _sign_consistency(returns, 60)
        item["jump_share_20"] = _jump_share(returns, 20)
        item["jump_share_60"] = _jump_share(returns, 60)
        item["information_continuity_60"] = (
            0.50 * item["path_smoothness_60"]
            + 0.50 * item["sign_consistency_60"]
            - item["jump_share_60"]
        )
        item["skip5_path_smoothness_60"] = _path_smoothness(shifted_returns, item["skip5_return_60"], 60)
        item["skip5_sign_consistency_60"] = _sign_consistency(shifted_returns, 60)
        item["skip5_jump_share_60"] = _jump_share(shifted_returns, 60)
        item["skip5_information_continuity_60"] = (
            0.50 * item["skip5_path_smoothness_60"]
            + 0.50 * item["skip5_sign_consistency_60"]
            - item["skip5_jump_share_60"]
        )
        pieces.append(item)

    out = pd.concat(pieces, ignore_index=True).replace([np.inf, -np.inf], np.nan)
    out["amount_20_rank"] = _cs_rank(out, out["amount_20"])
    out["state_tradeable"] = (
        (out["amount_20_rank"] > 0.20)
        & (pd.to_numeric(out["return_1d"], errors="coerce").abs() <= 0.50)
    )
    return out


def _path_smoothness(returns: pd.Series, window_return: pd.Series, window: int) -> pd.Series:
    abs_path = returns.abs().rolling(window, min_periods=max(5, window // 3)).sum()
    return _safe_div(window_return.abs(), abs_path).clip(lower=0.0, upper=1.0)


def _sign_consistency(returns: pd.Series, window: int) -> pd.Series:
    signs = np.sign(pd.to_numeric(returns, errors="coerce"))
    signed_sum = signs.rolling(window, min_periods=max(5, window // 3)).sum().abs()
    signed_count = signs.rolling(window, min_periods=max(5, window // 3)).count()
    return _safe_div(signed_sum, signed_count).clip(lower=0.0, upper=1.0)


def _jump_share(returns: pd.Series, window: int) -> pd.Series:
    abs_returns = pd.to_numeric(returns, errors="coerce").abs()
    min_periods = max(5, window // 3)
    largest = abs_returns.rolling(window, min_periods=min_periods).max()
    total = abs_returns.rolling(window, min_periods=min_periods).sum()
    count = abs_returns.rolling(window, min_periods=min_periods).count()
    ratio = _safe_div(largest, total)
    ratio = ratio.where(~((count >= min_periods) & (total.abs() <= 1e-12)), 0.0)
    return ratio.clip(lower=0.0, upper=1.0)


def _safe_div(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    with np.errstate(divide="ignore", invalid="ignore"):
        value = numerator / denominator.replace(0.0, np.nan)
    return value.replace([np.inf, -np.inf], np.nan)


def _nonzero(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce").where(lambda item: item.abs() > 1e-12)


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
            "lookback_window": 65 if "skip5" in name else 60,
        }
    )
