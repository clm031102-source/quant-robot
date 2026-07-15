from __future__ import annotations

import math
from typing import Any

import pandas as pd


def summarize_top_quantile_capacity(
    factors: pd.DataFrame,
    labels: pd.DataFrame,
    adv20: pd.DataFrame,
    *,
    candidate_names: tuple[str, ...],
    horizons: tuple[int, ...],
    min_cross_section: int,
    portfolio_value_cny: float,
    position_count: int,
    max_one_way_participation_rate: float,
) -> list[dict[str, Any]]:
    if min_cross_section < 5:
        raise ValueError("min_cross_section must be at least 5 for quintile capacity")
    if portfolio_value_cny <= 0.0:
        raise ValueError("portfolio_value_cny must be positive")
    if position_count < 1:
        raise ValueError("position_count must be positive")
    if not 0.0 < max_one_way_participation_rate <= 1.0:
        raise ValueError("max_one_way_participation_rate must be in (0, 1]")
    factor_frame = _normalise_factors(factors)
    label_frame = _normalise_labels(labels)
    capacity_frame = _normalise_adv20(adv20)
    position_notional = portfolio_value_cny / position_count
    minimum_adv20 = position_notional / max_one_way_participation_rate
    rows = []
    for factor_name in candidate_names:
        candidate = factor_frame[factor_frame["factor_name"].eq(factor_name)]
        for horizon in horizons:
            horizon_labels = label_frame[label_frame["horizon"].eq(int(horizon))]
            merged = candidate.merge(
                horizon_labels[["date", "asset_id", "market", "forward_return"]],
                on=["date", "asset_id", "market"],
                how="inner",
                validate="one_to_one",
            ).merge(
                capacity_frame,
                on=["date", "asset_id", "market"],
                how="left",
                validate="one_to_one",
            )
            top_asset_observations = 0
            top_adv20: list[float] = []
            for _, group in merged.groupby("date", sort=True):
                clean = group.dropna(subset=["factor_value", "forward_return"])
                if len(clean) < min_cross_section:
                    continue
                quantiles = _quintiles(clean["factor_value"])
                if quantiles is None:
                    continue
                top = clean.loc[quantiles.eq(4)]
                top_asset_observations += len(top)
                valid_adv20 = pd.to_numeric(top["adv20"], errors="coerce")
                valid_adv20 = valid_adv20[valid_adv20.gt(0.0) & valid_adv20.map(math.isfinite)]
                top_adv20.extend(float(value) for value in valid_adv20)
            series = pd.Series(top_adv20, dtype=float)
            p10 = float(series.quantile(0.10)) if not series.empty else None
            median = float(series.median()) if not series.empty else None
            coverage = len(series) / top_asset_observations if top_asset_observations else 0.0
            rows.append(
                {
                    "factor_name": str(factor_name),
                    "horizon": int(horizon),
                    "top_quantile_asset_observations": int(top_asset_observations),
                    "top_quantile_adv20_observations": int(len(series)),
                    "top_quantile_adv20_coverage_rate": float(coverage),
                    "top_quantile_adv20_median_cny": median,
                    "top_quantile_adv20_p10_cny": p10,
                    "position_notional_cny": float(position_notional),
                    "p10_one_way_participation_rate": float(position_notional / p10) if p10 else None,
                    "max_one_way_participation_rate": float(max_one_way_participation_rate),
                    "minimum_top_quantile_adv20_p10_cny": float(minimum_adv20),
                }
            )
    return rows


def _normalise_factors(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "factor_name", "factor_value"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("Factor frame is missing columns: " + ", ".join(missing))
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"])
    result["asset_id"] = result["asset_id"].astype(str)
    result["market"] = result["market"].astype(str)
    result["factor_name"] = result["factor_name"].astype(str)
    result["factor_value"] = pd.to_numeric(result["factor_value"], errors="coerce")
    if result.duplicated(["date", "asset_id", "market", "factor_name"]).any():
        raise ValueError("Factor frame contains duplicate factor rows")
    return result


def _normalise_labels(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "horizon", "forward_return"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("Label frame is missing columns: " + ", ".join(missing))
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"])
    result["asset_id"] = result["asset_id"].astype(str)
    result["market"] = result["market"].astype(str)
    result["horizon"] = pd.to_numeric(result["horizon"], errors="raise").astype(int)
    result["forward_return"] = pd.to_numeric(result["forward_return"], errors="coerce")
    if result.duplicated(["date", "asset_id", "market", "horizon"]).any():
        raise ValueError("Label frame contains duplicate label rows")
    return result


def _normalise_adv20(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adv20"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError("ADV20 frame is missing columns: " + ", ".join(missing))
    result = frame[required].copy()
    result["date"] = pd.to_datetime(result["date"])
    result["asset_id"] = result["asset_id"].astype(str)
    result["market"] = result["market"].astype(str)
    result["adv20"] = pd.to_numeric(result["adv20"], errors="coerce")
    if result.duplicated(["date", "asset_id", "market"]).any():
        raise ValueError("ADV20 frame contains duplicate asset-date rows")
    return result


def _quintiles(values: pd.Series) -> pd.Series | None:
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.nunique() < 5:
        return None
    try:
        return pd.qcut(numeric.rank(method="first"), q=5, labels=False)
    except ValueError:
        return None
