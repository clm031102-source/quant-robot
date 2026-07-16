from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant_robot.research.dynamic_comovement_peer_source import (
    MAPPING_METHOD,
    validate_dynamic_peer_mapping,
)
from quant_robot.schema.factors import FACTOR_COLUMNS


FACTOR_NAME = "etf_dynamic_peer_residual_dislocation_reversal_5_60"
DIRECT_EXPOSURE_NAMES = (
    "market_beta_120",
    "residual_volatility_60",
    "momentum_60",
    "short_return_5",
    "log_adv20",
)


@dataclass(frozen=True)
class DynamicPeerDislocationResult:
    factors: pd.DataFrame
    diagnostics: pd.DataFrame
    direct_exposures: pd.DataFrame
    adv20: pd.DataFrame


def compute_etf_dynamic_peer_dislocation(
    bars: pd.DataFrame,
    mapping: pd.DataFrame,
    *,
    eligible_keys: pd.DataFrame,
    market_min_cross_section: int = 30,
    beta_window: int = 120,
    beta_min_observations: int = 80,
    beta_lag: int = 1,
    residual_sum_window: int = 5,
    minimum_daily_peers: int = 3,
    robust_scale_window: int = 60,
    robust_scale_min_observations: int = 40,
    robust_scale_epsilon: float = 1e-12,
    residual_volatility_window: int = 60,
    residual_volatility_min_observations: int = 40,
    momentum_window: int = 60,
    short_return_window: int = 5,
    adv_window: int = 20,
) -> DynamicPeerDislocationResult:
    """Build the frozen point-in-time dynamic-peer dislocation candidate."""

    _validate_parameters(
        market_min_cross_section=market_min_cross_section,
        beta_window=beta_window,
        beta_min_observations=beta_min_observations,
        beta_lag=beta_lag,
        residual_sum_window=residual_sum_window,
        minimum_daily_peers=minimum_daily_peers,
        robust_scale_window=robust_scale_window,
        robust_scale_min_observations=robust_scale_min_observations,
        robust_scale_epsilon=robust_scale_epsilon,
        residual_volatility_window=residual_volatility_window,
        residual_volatility_min_observations=residual_volatility_min_observations,
        momentum_window=momentum_window,
        short_return_window=short_return_window,
        adv_window=adv_window,
    )
    frame = _normalise_bars(bars)
    keys = _normalise_eligible_keys(eligible_keys, frame)
    peer_mapping = _normalise_mapping(mapping)
    candidate_keys = _active_target_keys(keys, peer_mapping)
    features = _build_asset_features(
        frame,
        keys,
        market_min_cross_section=market_min_cross_section,
        beta_window=beta_window,
        beta_min_observations=beta_min_observations,
        beta_lag=beta_lag,
        residual_sum_window=residual_sum_window,
        residual_volatility_window=residual_volatility_window,
        residual_volatility_min_observations=residual_volatility_min_observations,
        momentum_window=momentum_window,
        short_return_window=short_return_window,
        adv_window=adv_window,
    )
    diagnostics = _attach_peer_dislocation(
        features,
        peer_mapping,
        minimum_daily_peers=minimum_daily_peers,
        robust_scale_window=robust_scale_window,
        robust_scale_min_observations=robust_scale_min_observations,
        robust_scale_epsilon=robust_scale_epsilon,
    )
    factors = _materialise_candidate(
        diagnostics,
        candidate_keys,
        lookback_window=beta_window + residual_sum_window + robust_scale_window,
    )
    direct_exposures = _materialise_direct_exposures(
        diagnostics,
        candidate_keys,
        beta_window=beta_window,
        residual_volatility_window=residual_volatility_window,
        momentum_window=momentum_window,
        short_return_window=short_return_window,
        adv_window=adv_window,
    )
    adv20 = _materialise_adv(diagnostics, candidate_keys)
    return DynamicPeerDislocationResult(
        factors=factors,
        diagnostics=diagnostics,
        direct_exposures=direct_exposures,
        adv20=adv20,
    )


def _build_asset_features(
    bars: pd.DataFrame,
    eligible_keys: pd.DataFrame,
    *,
    market_min_cross_section: int,
    beta_window: int,
    beta_min_observations: int,
    beta_lag: int,
    residual_sum_window: int,
    residual_volatility_window: int,
    residual_volatility_min_observations: int,
    momentum_window: int,
    short_return_window: int,
    adv_window: int,
) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []
    for market, market_bars in bars.groupby("market", sort=True):
        prices = (
            market_bars.pivot(index="date", columns="asset_id", values="adj_close")
            .sort_index()
            .sort_index(axis=1)
        )
        amounts = market_bars.pivot(index="date", columns="asset_id", values="amount").reindex(
            index=prices.index,
            columns=prices.columns,
        )
        returns = prices.pct_change(fill_method=None)
        market_keys = eligible_keys[eligible_keys["market"].eq(market)]
        eligibility = pd.DataFrame(False, index=prices.index, columns=prices.columns)
        if not market_keys.empty:
            row_index = pd.MultiIndex.from_frame(market_keys[["date", "asset_id"]])
            eligible_matrix = pd.Series(True, index=row_index).unstack(fill_value=False)
            eligibility.loc[
                eligible_matrix.index.intersection(eligibility.index),
                eligible_matrix.columns.intersection(eligibility.columns),
            ] = eligible_matrix.reindex(
                index=eligibility.index,
                columns=eligibility.columns,
                fill_value=False,
            )
        eligible_returns = returns.where(eligibility)
        eligible_count = eligible_returns.count(axis=1)
        market_return = eligible_returns.median(axis=1, skipna=True).where(
            eligible_count.ge(market_min_cross_section)
        )

        for asset_id in prices.columns:
            asset_return = returns[asset_id]
            paired = asset_return.notna() & market_return.notna()
            paired_asset = asset_return.where(paired)
            paired_market = market_return.where(paired)
            covariance = paired_asset.rolling(
                beta_window,
                min_periods=beta_min_observations,
            ).cov(paired_market)
            variance = paired_market.rolling(
                beta_window,
                min_periods=beta_min_observations,
            ).var()
            beta = covariance / variance.where(variance.abs() > 1e-12)
            alpha = paired_asset.rolling(
                beta_window,
                min_periods=beta_min_observations,
            ).mean() - beta * paired_market.rolling(
                beta_window,
                min_periods=beta_min_observations,
            ).mean()
            lagged_beta = beta.shift(beta_lag)
            lagged_alpha = alpha.shift(beta_lag)
            residual = asset_return - lagged_alpha - lagged_beta * market_return
            residual_sum = residual.rolling(
                residual_sum_window,
                min_periods=residual_sum_window,
            ).sum()
            residual_volatility = residual.rolling(
                residual_volatility_window,
                min_periods=residual_volatility_min_observations,
            ).std(ddof=0)
            adv = amounts[asset_id].rolling(adv_window, min_periods=adv_window).mean()
            item = pd.DataFrame(
                {
                    "date": prices.index,
                    "asset_id": str(asset_id),
                    "market": str(market),
                    "eligible": eligibility[asset_id].to_numpy(dtype=bool),
                    "asset_return": asset_return.to_numpy(),
                    "market_return": market_return.to_numpy(),
                    "market_alpha": lagged_alpha.to_numpy(),
                    "market_beta": lagged_beta.to_numpy(),
                    "residual": residual.to_numpy(),
                    "residual_sum": residual_sum.to_numpy(),
                    "residual_volatility": residual_volatility.to_numpy(),
                    "momentum": (prices[asset_id] / prices[asset_id].shift(momentum_window) - 1.0).to_numpy(),
                    "short_return": (
                        prices[asset_id] / prices[asset_id].shift(short_return_window) - 1.0
                    ).to_numpy(),
                    "adv20": adv.to_numpy(),
                    "log_adv20": np.log(adv.where(adv > 0.0)).to_numpy(),
                }
            )
            pieces.append(item)
    if not pieces:
        return pd.DataFrame(
            columns=[
                "date",
                "asset_id",
                "market",
                "eligible",
                "asset_return",
                "market_return",
                "market_alpha",
                "market_beta",
                "residual",
                "residual_sum",
                "residual_volatility",
                "momentum",
                "short_return",
                "adv20",
                "log_adv20",
            ]
        )
    return pd.concat(pieces, ignore_index=True).sort_values(
        ["asset_id", "date"]
    ).reset_index(drop=True)


def _attach_peer_dislocation(
    features: pd.DataFrame,
    mapping: pd.DataFrame,
    *,
    minimum_daily_peers: int,
    robust_scale_window: int,
    robust_scale_min_observations: int,
    robust_scale_epsilon: float,
) -> pd.DataFrame:
    eligible = features[features["eligible"]][
        ["date", "asset_id", "market", "residual_sum"]
    ].copy()
    contributions: list[pd.DataFrame] = []
    for (valid_from, valid_to), edges in mapping.groupby(
        ["valid_from", "valid_to"],
        sort=True,
    ):
        active = eligible[eligible["date"].between(valid_from, valid_to)].copy()
        if active.empty:
            continue
        target = active.rename(columns={"residual_sum": "target_residual_sum"})
        joined = target.merge(
            edges[["asset_id", "peer_asset_id"]],
            on="asset_id",
            how="inner",
            validate="many_to_many",
        )
        peer = active.rename(
            columns={
                "asset_id": "peer_asset_id",
                "market": "peer_market",
                "residual_sum": "peer_residual_sum",
            }
        )
        joined = joined.merge(
            peer,
            on=["date", "peer_asset_id"],
            how="inner",
            validate="many_to_one",
        )
        joined = joined[joined["market"].eq(joined["peer_market"])]
        contributions.append(
            joined[
                [
                    "date",
                    "asset_id",
                    "market",
                    "target_residual_sum",
                    "peer_residual_sum",
                ]
            ]
        )

    if contributions:
        peer_values = pd.concat(contributions, ignore_index=True)
        peer_summary = (
            peer_values.groupby(["date", "asset_id", "market"], as_index=False)
            .agg(
                target_residual_sum=("target_residual_sum", "first"),
                peer_median_residual_sum=("peer_residual_sum", "median"),
                peer_count=("peer_residual_sum", "count"),
            )
            .sort_values(["asset_id", "date"])
        )
        enough_peers = peer_summary["peer_count"].ge(minimum_daily_peers)
        peer_summary["raw_dislocation"] = (
            peer_summary["target_residual_sum"]
            - peer_summary["peer_median_residual_sum"]
        ).where(enough_peers)
        peer_summary = peer_summary.drop(columns="target_residual_sum")
    else:
        peer_summary = pd.DataFrame(
            columns=[
                "date",
                "asset_id",
                "market",
                "peer_median_residual_sum",
                "peer_count",
                "raw_dislocation",
            ]
        )

    output = features.merge(
        peer_summary,
        on=["date", "asset_id", "market"],
        how="left",
        validate="one_to_one",
    ).sort_values(["asset_id", "date"])
    output["peer_count"] = output["peer_count"].fillna(0).astype(int)
    enriched: list[pd.DataFrame] = []
    for _, group in output.groupby(["market", "asset_id"], sort=False):
        item = group.sort_values("date").copy()
        prior = item["raw_dislocation"].shift(1)
        rolling = prior.rolling(
            robust_scale_window,
            min_periods=robust_scale_min_observations,
        )
        item["robust_observations"] = prior.rolling(
            robust_scale_window,
            min_periods=1,
        ).count().astype(int)
        item["robust_center"] = rolling.median()
        item["robust_scale"] = 1.4826 * rolling.apply(_median_absolute_deviation, raw=True)
        valid_scale = item["robust_scale"].gt(robust_scale_epsilon)
        item["factor_value"] = (
            -(item["raw_dislocation"] - item["robust_center"]) / item["robust_scale"]
        ).where(valid_scale)
        enriched.append(item)
    return pd.concat(enriched, ignore_index=True).sort_values(
        ["asset_id", "date"]
    ).reset_index(drop=True)


def _materialise_candidate(
    diagnostics: pd.DataFrame,
    eligible_keys: pd.DataFrame,
    *,
    lookback_window: int,
) -> pd.DataFrame:
    values = diagnostics[["date", "asset_id", "market", "factor_value"]]
    output = eligible_keys.merge(
        values,
        on=["date", "asset_id", "market"],
        how="left",
        validate="one_to_one",
    )
    output["factor_name"] = FACTOR_NAME
    output["lookback_window"] = int(lookback_window)
    output["date"] = output["date"].dt.date
    return output[FACTOR_COLUMNS].sort_values(["asset_id", "date"]).reset_index(drop=True)


def _materialise_direct_exposures(
    diagnostics: pd.DataFrame,
    eligible_keys: pd.DataFrame,
    *,
    beta_window: int,
    residual_volatility_window: int,
    momentum_window: int,
    short_return_window: int,
    adv_window: int,
) -> pd.DataFrame:
    specifications = (
        ("market_beta_120", "market_beta", beta_window),
        ("residual_volatility_60", "residual_volatility", residual_volatility_window),
        ("momentum_60", "momentum", momentum_window),
        ("short_return_5", "short_return", short_return_window),
        ("log_adv20", "log_adv20", adv_window),
    )
    pieces: list[pd.DataFrame] = []
    for factor_name, source_column, lookback_window in specifications:
        values = diagnostics[["date", "asset_id", "market", source_column]].rename(
            columns={source_column: "factor_value"}
        )
        item = eligible_keys.merge(
            values,
            on=["date", "asset_id", "market"],
            how="left",
            validate="one_to_one",
        )
        item["factor_name"] = factor_name
        item["lookback_window"] = int(lookback_window)
        pieces.append(item[FACTOR_COLUMNS])
    output = pd.concat(pieces, ignore_index=True)
    output["date"] = output["date"].dt.date
    return output.sort_values(["asset_id", "date", "factor_name"]).reset_index(drop=True)


def _materialise_adv(
    diagnostics: pd.DataFrame,
    eligible_keys: pd.DataFrame,
) -> pd.DataFrame:
    values = diagnostics[["date", "asset_id", "market", "adv20"]]
    output = eligible_keys.merge(
        values,
        on=["date", "asset_id", "market"],
        how="left",
        validate="one_to_one",
    )
    output["date"] = output["date"].dt.date
    return output.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError("Bars are missing columns: " + ", ".join(missing))
    frame = bars[required].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].fillna("").astype(str).str.strip()
    frame["market"] = frame["market"].fillna("").astype(str).str.strip()
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    if frame["date"].isna().any() or frame["asset_id"].eq("").any() or frame["market"].eq("").any():
        raise ValueError("Bars contain invalid date, asset_id, or market values")
    if frame.duplicated(["date", "asset_id", "market"]).any():
        raise ValueError("Bars contain duplicate asset-date rows")
    if frame.groupby("asset_id")["market"].nunique().gt(1).any():
        raise ValueError("Each asset_id must belong to exactly one market")
    frame.loc[frame["adj_close"].le(0.0), "adj_close"] = np.nan
    frame.loc[frame["amount"].lt(0.0), "amount"] = np.nan
    return frame.sort_values(["market", "asset_id", "date"]).reset_index(drop=True)


def _normalise_eligible_keys(
    eligible_keys: pd.DataFrame,
    bars: pd.DataFrame,
) -> pd.DataFrame:
    required = ["date", "asset_id", "market"]
    missing = [column for column in required if column not in eligible_keys.columns]
    if missing:
        raise ValueError("Eligible keys are missing columns: " + ", ".join(missing))
    keys = eligible_keys[required].copy()
    keys["date"] = pd.to_datetime(keys["date"], errors="coerce")
    keys["asset_id"] = keys["asset_id"].fillna("").astype(str).str.strip()
    keys["market"] = keys["market"].fillna("").astype(str).str.strip()
    if keys.isna().any().any() or keys["asset_id"].eq("").any() or keys["market"].eq("").any():
        raise ValueError("Eligible keys contain invalid values")
    if keys.duplicated(required).any():
        raise ValueError("Eligible keys contain duplicate asset-date rows")
    missing_bars = keys.merge(
        bars[required],
        on=required,
        how="left",
        indicator=True,
        validate="one_to_one",
    )["_merge"].ne("both")
    if missing_bars.any():
        raise ValueError("Eligible keys reference missing bar rows")
    return keys.sort_values(["market", "asset_id", "date"]).reset_index(drop=True)


def _normalise_mapping(mapping: pd.DataFrame) -> pd.DataFrame:
    if "mapping_method" not in mapping.columns:
        raise ValueError("Dynamic peer mapping is missing mapping method")
    frame = mapping.copy()
    methods = frame["mapping_method"].fillna("").astype(str).str.strip()
    if not methods.eq(MAPPING_METHOD).all():
        raise ValueError("Dynamic peer mapping method does not match the frozen method")
    validate_dynamic_peer_mapping(frame)
    for column in ("valid_from", "valid_to", "known_from", "source_end_date"):
        frame[column] = pd.to_datetime(frame[column], errors="raise")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["peer_asset_id"] = frame["peer_asset_id"].astype(str)
    return frame.sort_values(
        ["valid_from", "valid_to", "asset_id", "peer_asset_id"]
    ).reset_index(drop=True)


def _active_target_keys(
    eligible_keys: pd.DataFrame,
    mapping: pd.DataFrame,
) -> pd.DataFrame:
    intervals = mapping[["asset_id", "valid_from", "valid_to"]].drop_duplicates()
    joined = eligible_keys.merge(
        intervals,
        on="asset_id",
        how="inner",
        validate="many_to_many",
    )
    active = joined[joined["date"].between(joined["valid_from"], joined["valid_to"])][
        ["date", "asset_id", "market"]
    ].drop_duplicates()
    return active.sort_values(["market", "asset_id", "date"]).reset_index(drop=True)


def _median_absolute_deviation(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if not len(finite):
        return np.nan
    center = np.median(finite)
    return float(np.median(np.abs(finite - center)))


def _validate_parameters(**parameters: int | float) -> None:
    market_min_cross_section = int(parameters["market_min_cross_section"])
    beta_window = int(parameters["beta_window"])
    beta_min_observations = int(parameters["beta_min_observations"])
    beta_lag = int(parameters["beta_lag"])
    residual_sum_window = int(parameters["residual_sum_window"])
    minimum_daily_peers = int(parameters["minimum_daily_peers"])
    robust_scale_window = int(parameters["robust_scale_window"])
    robust_scale_min_observations = int(parameters["robust_scale_min_observations"])
    robust_scale_epsilon = float(parameters["robust_scale_epsilon"])
    residual_volatility_window = int(parameters["residual_volatility_window"])
    residual_volatility_min_observations = int(
        parameters["residual_volatility_min_observations"]
    )
    if market_min_cross_section < 1 or minimum_daily_peers < 1:
        raise ValueError("Cross-section and peer minimums must be positive")
    pairs = (
        ("beta", beta_window, beta_min_observations),
        ("robust scale", robust_scale_window, robust_scale_min_observations),
        (
            "residual volatility",
            residual_volatility_window,
            residual_volatility_min_observations,
        ),
    )
    for label, window, minimum in pairs:
        if window < 1 or minimum < 1 or minimum > window:
            raise ValueError(f"Invalid {label} window/minimum observations")
    for label in ("residual_sum_window", "momentum_window", "short_return_window", "adv_window"):
        if int(parameters[label]) < 1:
            raise ValueError(f"{label} must be positive")
    if beta_lag != 1:
        raise ValueError("beta_lag must remain frozen at 1")
    if not np.isfinite(robust_scale_epsilon) or robust_scale_epsilon < 0.0:
        raise ValueError("robust_scale_epsilon must be finite and non-negative")
