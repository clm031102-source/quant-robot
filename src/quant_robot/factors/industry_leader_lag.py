from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


INDUSTRY_LEADER_LAG_FACTOR_NAMES = (
    "industry_leader_laggard_gap_reversion_5_20",
    "industry_leader_breakout_laggard_followthrough_10_5",
    "industry_leader_volume_confirmed_diffusion_5_20",
    "industry_peer_dispersion_compression_reversal_20_5",
    "industry_leader_pullback_resilience_10_5",
    "industry_laggard_lowvol_catchup_composite_20",
)


def compute_industry_leader_lag_factors(
    bars: pd.DataFrame,
    *,
    stock_basic: pd.DataFrame | None = None,
    factor_names: tuple[str, ...] | None = None,
    leader_adv_quantile: float = 0.67,
    min_industry_assets: int = 3,
) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError("Bars are missing columns for industry leader-lag factor calculation: " + ", ".join(missing))
    requested = _resolve_requested_factor_names(factor_names)

    frame = _feature_frame(
        bars,
        stock_basic=stock_basic,
        leader_adv_quantile=leader_adv_quantile,
        min_industry_assets=min_industry_assets,
    )
    valid = (
        frame["industry"].notna()
        & (frame["industry_count"] >= int(min_industry_assets))
        & (frame["leader_count"] > 0)
        & frame["adv20_amount"].notna()
    )
    leader_gap_5_20 = frame["leader_return_5_ex_self"] - frame["return_5"] + 0.25 * (
        frame["leader_return_20_ex_self"] - frame["return_20"]
    )
    breakout_followthrough = (
        0.65 * frame["leader_return_10_ex_self"]
        + 0.25 * frame["leader_range_position_20_ex_self"]
        - 0.45 * frame["return_5"]
    )
    volume_confirmed = (
        frame["leader_return_5_ex_self"] * (1.0 + frame["leader_amount_trend_20_60_ex_self"].clip(lower=-0.5))
        - frame["return_5"]
    )
    dispersion_compression = (
        frame["industry_return_20_dispersion"]
        * (frame["leader_return_5_ex_self"] - frame["return_5"])
        - 0.25 * frame["realized_vol_20"]
    )
    pullback_resilience = frame["leader_return_10_ex_self"] - frame["return_5"].clip(upper=0.0) - 0.20 * frame[
        "realized_vol_20"
    ]
    lowvol_catchup = (
        0.45 * (frame["leader_return_20_ex_self"] - frame["return_20"])
        + 0.25 * (frame["leader_return_5_ex_self"] - frame["return_5"])
        - 0.30 * frame["realized_vol_20"]
    )

    values_by_name = {
        "industry_leader_laggard_gap_reversion_5_20": _cs_z(frame, leader_gap_5_20).where(valid),
        "industry_leader_breakout_laggard_followthrough_10_5": _cs_z(frame, breakout_followthrough).where(valid),
        "industry_leader_volume_confirmed_diffusion_5_20": _cs_z(frame, volume_confirmed).where(valid),
        "industry_peer_dispersion_compression_reversal_20_5": _cs_z(frame, dispersion_compression).where(valid),
        "industry_leader_pullback_resilience_10_5": _cs_z(frame, pullback_resilience).where(valid),
        "industry_laggard_lowvol_catchup_composite_20": _cs_z(frame, lowvol_catchup).where(valid),
    }
    pieces = [_factor_frame(frame, name, values_by_name[name]) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return INDUSTRY_LEADER_LAG_FACTOR_NAMES
    supported = set(INDUSTRY_LEADER_LAG_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported industry leader-lag factor_names: {', '.join(unknown)}")
    return factor_names


def _feature_frame(
    bars: pd.DataFrame,
    *,
    stock_basic: pd.DataFrame | None,
    leader_adv_quantile: float,
    min_industry_assets: int,
) -> pd.DataFrame:
    frame = _normalise_bars(bars)
    frame = _merge_industry(frame, stock_basic)
    pieces: list[pd.DataFrame] = []
    for _, group in frame.groupby("asset_id", sort=False):
        item = group.copy()
        price = pd.to_numeric(item["adj_close"], errors="coerce")
        amount = pd.to_numeric(item["amount"], errors="coerce")
        returns = price.pct_change()
        item["return_1d"] = returns
        item["return_5"] = price.pct_change(5)
        item["return_10"] = price.pct_change(10)
        item["return_20"] = price.pct_change(20)
        item["adv20_amount"] = amount.rolling(20, min_periods=5).mean()
        item["amount_trend_20_60"] = amount.rolling(20, min_periods=5).mean() / _nonzero(
            amount.rolling(60, min_periods=20).mean()
        ) - 1.0
        item["realized_vol_20"] = returns.rolling(20, min_periods=5).std(ddof=0)
        rolling_high = price.rolling(20, min_periods=5).max()
        rolling_low = price.rolling(20, min_periods=5).min()
        item["range_position_20"] = _safe_div(price - rolling_low, rolling_high - rolling_low)
        pieces.append(item)
    features = pd.concat(pieces, ignore_index=True) if pieces else frame
    keys = ["date", "market", "industry"]
    features["industry_count"] = features.groupby(keys, dropna=False)["asset_id"].transform("nunique")
    features["industry_return_20_dispersion"] = features.groupby(keys, dropna=False)["return_20"].transform(
        lambda item: item.std(ddof=0)
    )
    features["adv20_rank_in_industry"] = features.groupby(keys, dropna=False)["adv20_amount"].rank(pct=True)
    leader_mask = (
        features["industry"].notna()
        & (features["industry_count"] >= int(min_industry_assets))
        & (features["adv20_rank_in_industry"] >= float(leader_adv_quantile))
    )
    features["_leader_weight"] = features["adv20_amount"].where(leader_mask, 0.0)
    features["leader_count"] = leader_mask.groupby(
        [features["date"], features["market"], features["industry"]],
        dropna=False,
    ).transform("sum")
    for column in ["return_5", "return_10", "return_20", "amount_trend_20_60", "range_position_20"]:
        features[f"leader_{column}_ex_self"] = _leader_weighted_average_ex_self(features, column, leader_mask)
    features["leader_count_ex_self"] = features["leader_count"] - leader_mask.astype(int)
    return features.replace([np.inf, -np.inf], np.nan)


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str)
    for column in ["adj_close", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if "industry" in frame:
        frame["industry"] = frame["industry"].astype(str)
    return (
        frame[(frame["market"] == "CN") & (frame["adj_close"] > 0) & (frame["amount"] > 0)]
        .dropna(subset=["date", "asset_id", "market", "adj_close", "amount"])
        .drop_duplicates(["asset_id", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _merge_industry(frame: pd.DataFrame, stock_basic: pd.DataFrame | None) -> pd.DataFrame:
    output = frame.copy()
    if "industry" in output and output["industry"].notna().any():
        output["industry"] = output["industry"].where(output["industry"].notna(), pd.NA)
    if stock_basic is None or stock_basic.empty:
        return output
    meta = stock_basic.copy()
    if "asset_id" not in meta:
        for candidate in ("ts_code", "symbol"):
            if candidate in meta:
                meta["asset_id"] = meta[candidate]
                break
    if "asset_id" not in meta or "industry" not in meta:
        return output
    meta = meta[["asset_id", "industry"]].dropna(subset=["asset_id"]).copy()
    meta["asset_id"] = meta["asset_id"].astype(str)
    meta["industry"] = meta["industry"].astype(str)
    meta = meta.drop_duplicates("asset_id", keep="last")
    if "industry" in output:
        merged = output.merge(meta.rename(columns={"industry": "industry_from_stock_basic"}), on="asset_id", how="left")
        merged["industry"] = merged["industry"].where(merged["industry"].notna(), merged["industry_from_stock_basic"])
        return merged.drop(columns=["industry_from_stock_basic"])
    return output.merge(meta, on="asset_id", how="left")


def _leader_weighted_average_ex_self(frame: pd.DataFrame, column: str, leader_mask: pd.Series) -> pd.Series:
    keys = [frame["date"], frame["market"], frame["industry"]]
    values = pd.to_numeric(frame[column], errors="coerce")
    weights = pd.to_numeric(frame["_leader_weight"], errors="coerce").fillna(0.0)
    weighted_value = weights * values
    sum_weight = weights.groupby(keys, dropna=False).transform("sum")
    sum_value = weighted_value.groupby(keys, dropna=False).transform("sum")
    self_weight = weights.where(leader_mask, 0.0)
    denominator = sum_weight - self_weight
    numerator = sum_value - self_weight * values
    average_ex_self = numerator / denominator.where(denominator > 0.0)
    fallback = sum_value / sum_weight.where(sum_weight > 0.0)
    return average_ex_self.where(denominator > 0.0, fallback)


def _safe_div(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    with np.errstate(divide="ignore", invalid="ignore"):
        value = numerator / denominator.replace(0.0, np.nan)
    return value.replace([np.inf, -np.inf], np.nan)


def _nonzero(values: pd.Series) -> pd.Series:
    return values.where(values.abs() > 1e-12)


def _cs_z(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    grouped = numeric.groupby([frame["date"], frame["market"]], sort=False)
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return ((numeric - mean) / std.where(std > 1e-12)).replace([np.inf, -np.inf], np.nan)


def _factor_frame(frame: pd.DataFrame, name: str, values: pd.Series) -> pd.DataFrame:
    lookback = 10 if name.endswith("_10_5") else 20
    return pd.DataFrame(
        {
            "date": pd.to_datetime(frame["date"]).dt.date.to_numpy(),
            "asset_id": frame["asset_id"].to_numpy(),
            "market": frame["market"].to_numpy(),
            "factor_name": name,
            "factor_value": values.to_numpy(),
            "lookback_window": lookback,
        }
    )
