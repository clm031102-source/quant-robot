from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


INDUSTRY_BREADTH_REGIME_FACTOR_NAMES = (
    "industry_breadth_repair_laggard_rebound_20",
    "industry_breadth_volume_confirmed_repair_20",
    "industry_dispersion_compression_breakout_20",
    "industry_internal_dispersion_laggard_reversal_20",
    "industry_breadth_overheat_runup_avoidance_10",
    "industry_breadth_turning_point_resilience_20",
)


def compute_industry_breadth_regime_factors(
    bars: pd.DataFrame,
    *,
    stock_basic: pd.DataFrame | None = None,
    factor_names: tuple[str, ...] | None = None,
    min_industry_assets: int = 8,
) -> pd.DataFrame:
    """Compute industry breadth/dispersion state factors from PIT bar data."""

    required = ["date", "asset_id", "market", "adj_close", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(
            "Bars are missing columns for industry breadth-regime factor calculation: " + ", ".join(missing)
        )
    requested = _resolve_requested_factor_names(factor_names)

    frame = _feature_frame(bars, stock_basic=stock_basic, min_industry_assets=min_industry_assets)
    valid = (
        frame["industry"].notna()
        & (frame["industry_count"] >= int(min_industry_assets))
        & frame["adv20_amount"].notna()
        & (frame["adv20_amount"] > 0)
    )

    breadth_repair_laggard = (
        0.70 * frame["industry_breadth_20_change_20"]
        + 0.35 * frame["industry_breadth_60_change_20"]
        - 0.45 * frame["idio_return_20"]
        - 0.20 * frame["realized_vol_20"]
    )
    volume_confirmed_repair = (
        frame["industry_breadth_20_change_20"]
        * (1.0 + frame["industry_amount_trend_20_60"].clip(lower=-0.5, upper=1.0))
        - 0.35 * frame["idio_return_20"]
    )
    dispersion_compression_breakout = (
        -0.65 * frame["industry_return_20_dispersion_z"]
        + 0.45 * frame["industry_breadth_20_change_20"]
        + 0.30 * frame["idio_return_5"]
        - 0.20 * frame["realized_vol_20"]
    )
    dispersion_laggard_reversal = (
        0.70 * frame["industry_return_20_dispersion_z"]
        - 0.55 * frame["idio_return_20"]
        + 0.25 * frame["industry_breadth_20_change_20"]
        - 0.20 * frame["realized_vol_20"]
    )
    overheat_runup_avoidance = -(
        0.70 * frame["industry_breadth_20_z"]
        + 0.50 * frame["industry_breadth_60_z"]
        + 0.45 * frame["idio_return_10"]
        + 0.20 * frame["amount_trend_20_60"].clip(lower=-0.5, upper=1.5)
    )
    turning_point_resilience = (
        0.55 * frame["industry_breadth_20_change_20"]
        + 0.35 * frame["industry_return_5_mean"]
        + 0.30 * frame["idio_return_5"]
        - 0.25 * frame["realized_vol_20"]
    )

    values_by_name = {
        "industry_breadth_repair_laggard_rebound_20": _cs_z(frame, breadth_repair_laggard).where(valid),
        "industry_breadth_volume_confirmed_repair_20": _cs_z(frame, volume_confirmed_repair).where(valid),
        "industry_dispersion_compression_breakout_20": _cs_z(frame, dispersion_compression_breakout).where(valid),
        "industry_internal_dispersion_laggard_reversal_20": _cs_z(frame, dispersion_laggard_reversal).where(valid),
        "industry_breadth_overheat_runup_avoidance_10": _cs_z(frame, overheat_runup_avoidance).where(valid),
        "industry_breadth_turning_point_resilience_20": _cs_z(frame, turning_point_resilience).where(valid),
    }
    pieces = [_factor_frame(frame, name, values_by_name[name]) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return INDUSTRY_BREADTH_REGIME_FACTOR_NAMES
    supported = set(INDUSTRY_BREADTH_REGIME_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported industry breadth-regime factor_names: {', '.join(unknown)}")
    return factor_names


def _feature_frame(
    bars: pd.DataFrame,
    *,
    stock_basic: pd.DataFrame | None,
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
        item["return_60"] = price.pct_change(60)
        item["adv20_amount"] = amount.rolling(20, min_periods=5).mean()
        item["amount_trend_20_60"] = amount.rolling(20, min_periods=5).mean() / _nonzero(
            amount.rolling(60, min_periods=20).mean()
        ) - 1.0
        item["realized_vol_20"] = returns.rolling(20, min_periods=5).std(ddof=0)
        pieces.append(item)
    features = pd.concat(pieces, ignore_index=True) if pieces else frame
    keys = ["date", "market", "industry"]
    features["industry_count"] = features.groupby(keys, dropna=False)["asset_id"].transform("nunique")
    features["industry_return_5_mean"] = features.groupby(keys, dropna=False)["return_5"].transform("mean")
    features["industry_return_20_mean"] = features.groupby(keys, dropna=False)["return_20"].transform("mean")
    features["industry_return_20_dispersion"] = features.groupby(keys, dropna=False)["return_20"].transform(
        lambda item: item.std(ddof=0)
    )
    features["industry_amount_trend_20_60"] = features.groupby(keys, dropna=False)[
        "amount_trend_20_60"
    ].transform("mean")
    features["industry_breadth_20"] = (features["return_20"] > 0).astype(float).groupby(
        [features["date"], features["market"], features["industry"]],
        dropna=False,
    ).transform("mean")
    features["industry_breadth_60"] = (features["return_60"] > 0).astype(float).groupby(
        [features["date"], features["market"], features["industry"]],
        dropna=False,
    ).transform("mean")
    features = _add_industry_state_history(features)
    features["idio_return_5"] = features["return_5"] - features["industry_return_5_mean"]
    features["idio_return_10"] = features["return_10"] - features.groupby(keys, dropna=False)["return_10"].transform(
        "mean"
    )
    features["idio_return_20"] = features["return_20"] - features["industry_return_20_mean"]
    return features.replace([np.inf, -np.inf], np.nan)


def _add_industry_state_history(features: pd.DataFrame) -> pd.DataFrame:
    industry_cols = [
        "date",
        "market",
        "industry",
        "industry_breadth_20",
        "industry_breadth_60",
        "industry_return_20_dispersion",
    ]
    states = features[industry_cols].drop_duplicates(["date", "market", "industry"]).sort_values(
        ["market", "industry", "date"]
    )
    state_pieces: list[pd.DataFrame] = []
    for _, group in states.groupby(["market", "industry"], dropna=False, sort=False):
        item = group.copy()
        for column in ["industry_breadth_20", "industry_breadth_60", "industry_return_20_dispersion"]:
            numeric = pd.to_numeric(item[column], errors="coerce")
            item[f"{column}_mean20"] = numeric.rolling(20, min_periods=5).mean()
        state_pieces.append(item)
    state = pd.concat(state_pieces, ignore_index=True) if state_pieces else states
    state["industry_breadth_20_change_20"] = state["industry_breadth_20"] - state["industry_breadth_20_mean20"]
    state["industry_breadth_60_change_20"] = state["industry_breadth_60"] - state["industry_breadth_60_mean20"]
    merged = features.merge(
        state[
            [
                "date",
                "market",
                "industry",
                "industry_breadth_20_change_20",
                "industry_breadth_60_change_20",
            ]
        ],
        on=["date", "market", "industry"],
        how="left",
        validate="many_to_one",
    )
    merged["industry_return_20_dispersion_z"] = _cs_z(merged, merged["industry_return_20_dispersion"])
    merged["industry_breadth_20_z"] = _cs_z(merged, merged["industry_breadth_20"])
    merged["industry_breadth_60_z"] = _cs_z(merged, merged["industry_breadth_60"])
    return merged


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


def _nonzero(values: pd.Series) -> pd.Series:
    return values.where(values.abs() > 1e-12)


def _cs_z(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    grouped = numeric.groupby([frame["date"], frame["market"]], sort=False)
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return ((numeric - mean) / std.where(std > 1e-12)).replace([np.inf, -np.inf], np.nan)


def _factor_frame(frame: pd.DataFrame, name: str, values: pd.Series) -> pd.DataFrame:
    lookback = 10 if name.endswith("_10") else 20
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

