from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


ETF_SKIP_MOMENTUM_FACTOR_NAMES = (
    "etf_skip5_momentum_60",
    "etf_skip20_momentum_120",
    "fip_smooth_momentum_skip5_60",
)

ETF_PRICE_ROTATION_REFERENCE_FACTOR_NAMES = (
    "momentum_20",
    "momentum_60",
    "risk_adjusted_momentum_20",
    "risk_adjusted_momentum_60",
    "reversal_5",
    "reversal_20",
    "market_relative_strength_20",
    "market_relative_strength_60",
)


def compute_etf_skip_momentum_factors(
    bars: pd.DataFrame,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    frame = _normalise_bars(bars, require_amount=True)
    requested = ETF_SKIP_MOMENTUM_FACTOR_NAMES if factor_names is None else tuple(factor_names)
    unknown = [name for name in requested if name not in ETF_SKIP_MOMENTUM_FACTOR_NAMES]
    if unknown:
        raise ValueError("Unsupported ETF skip-momentum factor_names: " + ", ".join(unknown))
    requested_set = set(requested)
    feature_pieces = [_candidate_features(group) for _, group in frame.groupby("asset_id", sort=False)]
    features = pd.concat(feature_pieces, ignore_index=True) if feature_pieces else frame.iloc[0:0].copy()
    if features.empty:
        return pd.DataFrame(columns=FACTOR_COLUMNS)

    values: dict[str, pd.Series] = {}
    if "etf_skip5_momentum_60" in requested_set:
        values["etf_skip5_momentum_60"] = features["skip5_return_60"]
    if "etf_skip20_momentum_120" in requested_set:
        values["etf_skip20_momentum_120"] = features["skip20_return_120"]
    if "fip_smooth_momentum_skip5_60" in requested_set:
        amount_rank = _cross_sectional_rank(features, features["amount_20"])
        tradeable = amount_rank.gt(0.20) & features["return_1d"].abs().le(0.50)
        values["fip_smooth_momentum_skip5_60"] = (
            _cross_sectional_zscore(features, features["skip5_return_60"])
            + 0.70 * _cross_sectional_zscore(features, features["skip5_information_continuity_60"])
            - 0.25 * _cross_sectional_zscore(features, features["realized_vol_20"])
        ).where(tradeable)

    lookbacks = {
        "etf_skip5_momentum_60": 65,
        "etf_skip20_momentum_120": 140,
        "fip_smooth_momentum_skip5_60": 65,
    }
    pieces = [_factor_frame(features, name, values[name], lookbacks[name]) for name in requested]
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def compute_etf_price_rotation_reference_factors(bars: pd.DataFrame) -> pd.DataFrame:
    frame = _normalise_bars(bars, require_amount=False)
    pieces: list[pd.DataFrame] = []
    for _, group in frame.groupby("asset_id", sort=False):
        item = group.sort_values("date").copy()
        price = item["adj_close"]
        returns = price.pct_change()
        momentum_20 = price / price.shift(20) - 1.0
        momentum_60 = price / price.shift(60) - 1.0
        values = {
            "momentum_20": momentum_20,
            "momentum_60": momentum_60,
            "risk_adjusted_momentum_20": _safe_div(momentum_20, returns.rolling(20).std(ddof=0)),
            "risk_adjusted_momentum_60": _safe_div(momentum_60, returns.rolling(60).std(ddof=0)),
            "reversal_5": -(price / price.shift(5) - 1.0),
            "reversal_20": -momentum_20,
        }
        for name, factor_values in values.items():
            pieces.append(_factor_frame(item, name, factor_values, int(name.rsplit("_", 1)[-1])))
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    base = pd.concat(pieces, ignore_index=True)
    relatives = []
    for window in (20, 60):
        source = base[base["factor_name"] == f"momentum_{window}"].copy()
        median = source.groupby(["date", "market"], sort=False)["factor_value"].transform("median")
        source["factor_name"] = f"market_relative_strength_{window}"
        source["factor_value"] = source["factor_value"] - median
        relatives.append(source)
    return pd.concat([base, *relatives], ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _candidate_features(group: pd.DataFrame) -> pd.DataFrame:
    item = group.sort_values("date").copy()
    price = item["adj_close"]
    amount = item["amount"]
    returns = price.pct_change()
    shifted_returns = returns.shift(5)
    item["return_1d"] = returns
    item["skip5_return_60"] = price.shift(5) / price.shift(65) - 1.0
    item["skip20_return_120"] = price.shift(20) / price.shift(140) - 1.0
    item["amount_20"] = amount.rolling(20, min_periods=5).mean()
    item["realized_vol_20"] = returns.rolling(20, min_periods=5).std(ddof=0)
    path_smoothness = _path_smoothness(shifted_returns, item["skip5_return_60"], 60)
    sign_consistency = _sign_consistency(shifted_returns, 60)
    jump_share = _jump_share(shifted_returns, 60)
    item["skip5_information_continuity_60"] = 0.50 * path_smoothness + 0.50 * sign_consistency - jump_share
    return item


def _normalise_bars(bars: pd.DataFrame, *, require_amount: bool) -> pd.DataFrame:
    required = {"date", "asset_id", "market", "adj_close"}
    if require_amount:
        required.add("amount")
    missing = sorted(required - set(bars.columns))
    if missing:
        raise ValueError("Bars are missing columns for ETF skip-momentum factors: " + ", ".join(missing))
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str)
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    if require_amount:
        frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    duplicates = frame.duplicated(["asset_id", "date"], keep=False)
    if duplicates.any():
        raise ValueError("Bars contain duplicate asset-date rows for ETF skip-momentum factors")
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _path_smoothness(returns: pd.Series, window_return: pd.Series, window: int) -> pd.Series:
    abs_path = returns.abs().rolling(window, min_periods=max(5, window // 3)).sum()
    return _safe_div(window_return.abs(), abs_path).clip(lower=0.0, upper=1.0)


def _sign_consistency(returns: pd.Series, window: int) -> pd.Series:
    signs = np.sign(pd.to_numeric(returns, errors="coerce"))
    min_periods = max(5, window // 3)
    signed_sum = signs.rolling(window, min_periods=min_periods).sum().abs()
    signed_count = signs.rolling(window, min_periods=min_periods).count()
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
        values = numerator / denominator.replace(0.0, np.nan)
    return values.replace([np.inf, -np.inf], np.nan)


def _cross_sectional_rank(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.groupby([frame["date"], frame["market"]], sort=False).rank(pct=True)


def _cross_sectional_zscore(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    grouped = numeric.groupby([frame["date"], frame["market"]], sort=False)
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return ((numeric - mean) / std.where(std > 1e-12)).replace([np.inf, -np.inf], np.nan)


def _factor_frame(frame: pd.DataFrame, name: str, values: pd.Series, lookback: int) -> pd.DataFrame:
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
