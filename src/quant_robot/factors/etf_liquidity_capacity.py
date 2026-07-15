from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.factors.technical import compute_basic_factors
from quant_robot.schema.factors import FACTOR_COLUMNS


ETF_LIQUIDITY_CAPACITY_FACTOR_NAMES = (
    "etf_amihud_improvement_5_60",
    "etf_amount_participation_breadth_20_60",
    "etf_amount_distribution_quality_20",
)

ETF_LIQUIDITY_REFERENCE_FACTOR_NAMES = (
    "liquidity_5",
    "liquidity_10",
    "liquidity_20",
    "liquidity_60",
    "liquidity_resilience_60",
    "amount_stability_20",
    "amount_stability_60",
    "average_amount_20",
    "average_amount_60",
    "volume_change_20",
    "volume_change_60",
    "demand_pressure_60",
    "quiet_accumulation_60",
)


def compute_etf_liquidity_capacity_factors(
    bars: pd.DataFrame,
    *,
    eligible_keys: pd.DataFrame | None = None,
) -> pd.DataFrame:
    features = _compute_features(_normalise_bars(bars))
    features = _select_eligible_keys(features, eligible_keys, validate="one_to_one")
    if features.empty:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    values = {
        "etf_amihud_improvement_5_60": features["amihud_improvement_5_60"],
        "etf_amount_participation_breadth_20_60": features["amount_participation_breadth_20_60"],
        "etf_amount_distribution_quality_20": features["amount_distribution_quality_20"],
    }
    lookbacks = {
        "etf_amihud_improvement_5_60": 65,
        "etf_amount_participation_breadth_20_60": 80,
        "etf_amount_distribution_quality_20": 20,
    }
    pieces = [_factor_frame(features, name, values[name], lookbacks[name]) for name in ETF_LIQUIDITY_CAPACITY_FACTOR_NAMES]
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def compute_etf_liquidity_reference_factors(
    bars: pd.DataFrame,
    *,
    eligible_keys: pd.DataFrame | None = None,
) -> pd.DataFrame:
    frame = _normalise_bars(bars)
    if eligible_keys is None:
        references = compute_basic_factors(
            frame,
            windows=(5, 10, 20, 60),
            factor_names=ETF_LIQUIDITY_REFERENCE_FACTOR_NAMES,
        )
    else:
        keys = _normalise_eligible_keys(eligible_keys)
        references_by_asset = []
        selected = frame[frame["asset_id"].isin(keys["asset_id"].unique())]
        for asset_id, group in selected.groupby("asset_id", sort=False):
            asset_references = compute_basic_factors(
                group,
                windows=(5, 10, 20, 60),
                factor_names=ETF_LIQUIDITY_REFERENCE_FACTOR_NAMES,
            )
            asset_keys = keys[keys["asset_id"].eq(asset_id)]
            references_by_asset.append(
                asset_references.merge(
                    asset_keys,
                    on=["date", "asset_id", "market"],
                    how="inner",
                    validate="many_to_one",
                )
            )
        references = (
            pd.concat(references_by_asset, ignore_index=True)
            if references_by_asset
            else pd.DataFrame(columns=FACTOR_COLUMNS)
        )
    return references[FACTOR_COLUMNS].sort_values(["asset_id", "date", "factor_name"]).reset_index(drop=True)


def compute_etf_adv20(
    bars: pd.DataFrame,
    *,
    eligible_keys: pd.DataFrame | None = None,
) -> pd.DataFrame:
    features = _compute_features(_normalise_bars(bars))
    features = _select_eligible_keys(features, eligible_keys, validate="one_to_one")
    return features[["date", "asset_id", "market", "adv20"]].sort_values(
        ["asset_id", "date"]
    ).reset_index(drop=True)


def _compute_features(frame: pd.DataFrame) -> pd.DataFrame:
    pieces = []
    for _, group in frame.groupby("asset_id", sort=False):
        item = group.sort_values("date").copy()
        price = item["adj_close"]
        amount = item["amount"].where(item["amount"] > 0.0)
        daily_amihud = price.pct_change().abs() / amount
        recent_impact = daily_amihud.rolling(5, min_periods=5).mean()
        prior_impact = daily_amihud.shift(5).rolling(60, min_periods=60).mean()
        with np.errstate(divide="ignore", invalid="ignore"):
            improvement = np.log(prior_impact / recent_impact)
        prior_amount_median = amount.shift(1).rolling(60, min_periods=60).median()
        above_baseline = amount.gt(prior_amount_median).astype(float).where(
            amount.notna() & prior_amount_median.notna()
        )
        amount_sum = amount.rolling(20, min_periods=20).sum()
        amount_square_sum = amount.pow(2).rolling(20, min_periods=20).sum()
        with np.errstate(divide="ignore", invalid="ignore"):
            distribution_quality = 1.0 - amount_square_sum / amount_sum.pow(2)
        item["amihud_improvement_5_60"] = improvement.replace([np.inf, -np.inf], np.nan)
        item["amount_participation_breadth_20_60"] = above_baseline.rolling(
            20,
            min_periods=20,
        ).mean()
        item["amount_distribution_quality_20"] = distribution_quality.replace([np.inf, -np.inf], np.nan)
        item["adv20"] = amount.rolling(20, min_periods=20).mean()
        pieces.append(item)
    if not pieces:
        result = frame.copy()
        for column in (
            "amihud_improvement_5_60",
            "amount_participation_breadth_20_60",
            "amount_distribution_quality_20",
            "adv20",
        ):
            result[column] = pd.Series(dtype=float)
        return result
    return pd.concat(pieces, ignore_index=True)


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "asset_id", "market", "adj_close", "volume", "amount"}
    missing = sorted(required - set(bars.columns))
    if missing:
        raise ValueError("Bars are missing columns for ETF liquidity-capacity factors: " + ", ".join(missing))
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str)
    for column in ("adj_close", "volume", "amount"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame.duplicated(["asset_id", "date"]).any():
        raise ValueError("Bars contain duplicate asset-date rows for ETF liquidity-capacity factors")
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _select_eligible_keys(
    frame: pd.DataFrame,
    eligible_keys: pd.DataFrame | None,
    *,
    validate: str,
) -> pd.DataFrame:
    if eligible_keys is None:
        return frame
    keys = _normalise_eligible_keys(eligible_keys)
    return frame.merge(keys, on=["date", "asset_id", "market"], how="inner", validate=validate)


def _normalise_eligible_keys(eligible_keys: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market"]
    missing = [column for column in required if column not in eligible_keys.columns]
    if missing:
        raise ValueError("eligible_keys are missing columns: " + ", ".join(missing))
    keys = eligible_keys[required].copy()
    keys["date"] = pd.to_datetime(keys["date"]).dt.date
    keys["asset_id"] = keys["asset_id"].astype(str)
    keys["market"] = keys["market"].astype(str)
    if keys.duplicated(required).any():
        raise ValueError("eligible_keys contain duplicate asset-date rows")
    return keys


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
