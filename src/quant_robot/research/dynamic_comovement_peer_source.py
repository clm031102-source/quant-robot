from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


MAPPING_METHOD = "lagged_market_residual_correlation_topk"
MAPPING_COLUMNS = [
    "asset_id",
    "peer_asset_id",
    "valid_from",
    "valid_to",
    "known_from",
    "source_end_date",
    "similarity",
    "pair_observations",
    "peer_rank",
    "peer_count",
    "mapping_method",
    "source",
]
SNAPSHOT_COLUMNS = [
    "valid_from",
    "valid_to",
    "source_end_date",
    "eligible_assets",
    "return_ready_assets",
    "residual_ready_assets",
    "mapped_assets",
    "mapping_edges",
    "reciprocity_rate",
    "median_selected_similarity",
]
STABILITY_COLUMNS = [
    "previous_valid_from",
    "valid_from",
    "comparable_assets",
    "median_jaccard",
    "median_retention",
    "complete_churn_rate",
]
DUPLICATE_COLUMNS = [
    "valid_from",
    "reference_name",
    "selected_edges",
    "evidence_edges",
    "common_edges",
    "edge_evidence_coverage",
    "edge_overlap",
]


@dataclass(frozen=True)
class DynamicPeerPolicy:
    return_window: int = 120
    min_asset_return_observations: int = 100
    market_min_cross_section: int = 30
    beta_min_observations: int = 80
    pair_min_observations: int = 80
    min_correlation: float = 0.50
    max_peers: int = 5
    min_peers: int = 3
    rebalance_months: tuple[int, ...] = (1, 4, 7, 10)
    residual_volatility_window: int = 60
    momentum_window: int = 60
    short_return_window: int = 5
    liquidity_window: int = 20


@dataclass(frozen=True)
class DynamicPeerSourceResult:
    mapping: pd.DataFrame
    snapshots: pd.DataFrame
    stability: pd.DataFrame
    duplicate_overlap: pd.DataFrame


def build_dynamic_comovement_peer_source(
    bars: pd.DataFrame,
    eligibility: pd.DataFrame,
    *,
    analysis_start_date: str | pd.Timestamp,
    analysis_end_date: str | pd.Timestamp,
    policy: DynamicPeerPolicy = DynamicPeerPolicy(),
) -> DynamicPeerSourceResult:
    _validate_policy(policy)
    start = pd.Timestamp(analysis_start_date).normalize()
    end = pd.Timestamp(analysis_end_date).normalize()
    if start > end:
        raise ValueError("analysis_start_date must be on or before analysis_end_date")
    frame = _prepare_bars(bars, start, end)
    eligible = _prepare_eligibility(eligibility, start, end)
    calendar = pd.DatetimeIndex(sorted(frame["date"].unique()))
    scheduled = _scheduled_valid_dates(calendar, policy.rebalance_months)

    mapping_rows: list[dict[str, Any]] = []
    snapshot_rows: list[dict[str, Any]] = []
    duplicate_rows: list[dict[str, Any]] = []
    for index, valid_from in enumerate(scheduled):
        valid_location = int(calendar.get_loc(valid_from))
        valid_to = (
            calendar[int(calendar.get_loc(scheduled[index + 1])) - 1]
            if index + 1 < len(scheduled)
            else calendar[-1]
        )
        if valid_location == 0:
            snapshot_rows.append(
                _empty_snapshot_row(valid_from, valid_to, source_end_date=None)
            )
            continue
        source_end = calendar[valid_location - 1]
        source_assets = sorted(
            eligible.loc[
                eligible["date"].eq(source_end) & eligible["eligible"],
                "asset_id",
            ].unique()
        )
        window_dates = calendar[calendar <= source_end][-(policy.return_window + 1) :]
        window = frame[
            frame["date"].isin(window_dates) & frame["asset_id"].isin(source_assets)
        ].copy()
        returns, amounts = _window_matrices(window, window_dates, source_assets)
        return_counts = returns.notna().sum()
        ready_assets = sorted(
            return_counts[return_counts.ge(policy.min_asset_return_observations)].index
        )
        returns = returns.reindex(columns=ready_assets)
        amounts = amounts.reindex(columns=ready_assets)
        residuals, betas = _market_residual_returns(returns, policy)
        residual_assets = sorted(residuals.columns[residuals.notna().any()].tolist())
        residuals = residuals.reindex(columns=residual_assets)
        correlations = residuals.corr(min_periods=policy.pair_min_observations)
        pair_observations = residuals.notna().astype("int16").T.dot(
            residuals.notna().astype("int16")
        )
        selected = _select_top_peers(
            correlations,
            pair_observations,
            valid_from=valid_from,
            valid_to=valid_to,
            source_end_date=source_end,
            policy=policy,
        )
        mapping_rows.extend(selected)
        snapshot_mapping = pd.DataFrame(selected, columns=MAPPING_COLUMNS)
        mapped_assets = (
            int(snapshot_mapping["asset_id"].nunique())
            if not snapshot_mapping.empty
            else 0
        )
        reciprocity = _reciprocity_rate(snapshot_mapping)
        similarities = pd.to_numeric(
            snapshot_mapping.get("similarity", pd.Series(dtype="float64")),
            errors="coerce",
        ).dropna()
        snapshot_rows.append(
            {
                "valid_from": valid_from,
                "valid_to": valid_to,
                "source_end_date": source_end,
                "eligible_assets": int(len(source_assets)),
                "return_ready_assets": int(len(ready_assets)),
                "residual_ready_assets": int(len(residual_assets)),
                "mapped_assets": mapped_assets,
                "mapping_edges": int(len(snapshot_mapping)),
                "reciprocity_rate": reciprocity,
                "median_selected_similarity": (
                    float(similarities.median()) if not similarities.empty else 0.0
                ),
            }
        )
        exposures = _reference_exposures(
            returns,
            residuals,
            betas,
            amounts,
            policy,
        )
        for reference_name in exposures.columns:
            duplicate_rows.append(
                summarize_scalar_reference_overlap(
                    snapshot_mapping,
                    valid_from=valid_from,
                    exposures=exposures[reference_name],
                    reference_name=reference_name,
                    max_neighbors=policy.max_peers,
                )
            )

    mapping = pd.DataFrame(mapping_rows, columns=MAPPING_COLUMNS)
    if not mapping.empty:
        mapping = mapping.sort_values(
            ["valid_from", "asset_id", "peer_rank", "peer_asset_id"]
        ).reset_index(drop=True)
    validate_dynamic_peer_mapping(mapping)
    snapshots = pd.DataFrame(snapshot_rows, columns=SNAPSHOT_COLUMNS)
    stability = _summarize_stability(mapping, snapshots["valid_from"])
    duplicate_overlap = pd.DataFrame(duplicate_rows, columns=DUPLICATE_COLUMNS)
    return DynamicPeerSourceResult(
        mapping=mapping,
        snapshots=snapshots,
        stability=stability,
        duplicate_overlap=duplicate_overlap,
    )


def summarize_scalar_reference_overlap(
    mapping: pd.DataFrame,
    *,
    valid_from: str | pd.Timestamp,
    exposures: pd.Series,
    reference_name: str,
    max_neighbors: int,
) -> dict[str, Any]:
    valid_date = pd.Timestamp(valid_from).normalize()
    if mapping.empty:
        selected_edges: set[tuple[str, str]] = set()
    else:
        mapping_dates = pd.to_datetime(mapping["valid_from"], errors="coerce")
        selected_edges = {
            (str(row.asset_id), str(row.peer_asset_id))
            for row in mapping.loc[mapping_dates.eq(valid_date)].itertuples(index=False)
        }
    values = pd.to_numeric(exposures, errors="coerce").dropna()
    values.index = values.index.astype(str)
    evidence_edges = {
        edge for edge in selected_edges if edge[0] in values.index and edge[1] in values.index
    }
    reference_edges: set[tuple[str, str]] = set()
    for asset_id in sorted({edge[0] for edge in evidence_edges}):
        distances = [
            (abs(float(values.loc[asset_id]) - float(values.loc[peer_id])), peer_id)
            for peer_id in values.index
            if peer_id != asset_id
        ]
        for _, peer_id in sorted(distances, key=lambda item: (item[0], item[1]))[:max_neighbors]:
            reference_edges.add((asset_id, peer_id))
    common_edges = evidence_edges.intersection(reference_edges)
    return {
        "valid_from": valid_date,
        "reference_name": str(reference_name),
        "selected_edges": int(len(selected_edges)),
        "evidence_edges": int(len(evidence_edges)),
        "common_edges": int(len(common_edges)),
        "edge_evidence_coverage": _safe_ratio(len(evidence_edges), len(selected_edges)),
        "edge_overlap": _safe_ratio(len(common_edges), len(evidence_edges)),
    }


def validate_dynamic_peer_mapping(mapping: pd.DataFrame) -> None:
    if mapping.empty:
        return
    required = {
        "asset_id",
        "peer_asset_id",
        "valid_from",
        "valid_to",
        "known_from",
        "source_end_date",
    }
    missing = sorted(required.difference(mapping.columns))
    if missing:
        raise ValueError("dynamic peer mapping is missing columns: " + ", ".join(missing))
    frame = mapping.copy()
    for column in ("valid_from", "valid_to", "known_from", "source_end_date"):
        frame[column] = pd.to_datetime(frame[column], errors="coerce")
    if frame[list(required - {"asset_id", "peer_asset_id"})].isna().any().any():
        raise ValueError("dynamic peer mapping contains invalid dates")
    if frame["asset_id"].astype(str).eq(frame["peer_asset_id"].astype(str)).any():
        raise ValueError("dynamic peer mapping contains self peers")
    if frame["valid_to"].lt(frame["valid_from"]).any():
        raise ValueError("dynamic peer mapping contains reversed intervals")
    if frame["source_end_date"].ge(frame["valid_from"]).any():
        raise ValueError("dynamic peer mapping contains look-ahead source dates")
    if frame["known_from"].ne(frame["valid_from"]).any():
        raise ValueError("dynamic peer mapping known_from must equal valid_from")
    if frame.duplicated(["asset_id", "peer_asset_id", "valid_from"]).any():
        raise ValueError("dynamic peer mapping contains duplicate directed edges")
    for _, group in frame.sort_values("valid_from").groupby(
        ["asset_id", "peer_asset_id"], sort=False
    ):
        previous_end = group["valid_to"].shift(1)
        if group["valid_from"].le(previous_end).fillna(False).any():
            raise ValueError("dynamic peer mapping contains overlapping directed peer intervals")


def _prepare_bars(
    bars: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    required = {"date", "asset_id", "adj_close", "amount"}
    missing = sorted(required.difference(bars.columns))
    if missing:
        raise ValueError("dynamic peer bars are missing columns: " + ", ".join(missing))
    frame = bars[list(required)].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].fillna("").astype(str).str.strip()
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    frame = frame[
        frame["date"].between(start, end)
        & frame["date"].notna()
        & frame["asset_id"].ne("")
    ].copy()
    if frame.duplicated(["asset_id", "date"]).any():
        raise ValueError("dynamic peer bars contain duplicate asset-date rows")
    frame.loc[frame["adj_close"].le(0.0), "adj_close"] = np.nan
    if frame.empty:
        raise ValueError("dynamic peer bars contain no rows in the analysis window")
    return frame.sort_values(["date", "asset_id"]).reset_index(drop=True)


def _prepare_eligibility(
    eligibility: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    required = {"date", "asset_id", "eligible"}
    missing = sorted(required.difference(eligibility.columns))
    if missing:
        raise ValueError("dynamic peer eligibility is missing columns: " + ", ".join(missing))
    frame = eligibility[list(required)].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].fillna("").astype(str).str.strip()
    frame["eligible"] = frame["eligible"].fillna(False).astype(bool)
    frame = frame[frame["date"].between(start, end)].copy()
    if frame.duplicated(["asset_id", "date"]).any():
        raise ValueError("dynamic peer eligibility contains duplicate asset-date rows")
    return frame


def _scheduled_valid_dates(
    calendar: pd.DatetimeIndex,
    months: tuple[int, ...],
) -> pd.DatetimeIndex:
    selected = calendar[calendar.month.isin(months)]
    if selected.empty:
        return pd.DatetimeIndex([])
    keys = pd.DataFrame({"date": selected})
    return pd.DatetimeIndex(
        keys.groupby([keys["date"].dt.year, keys["date"].dt.month], sort=True)["date"].min()
    )


def _window_matrices(
    window: pd.DataFrame,
    window_dates: pd.DatetimeIndex,
    assets: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    close = window.pivot(index="date", columns="asset_id", values="adj_close").reindex(
        index=window_dates,
        columns=assets,
    )
    amount = window.pivot(index="date", columns="asset_id", values="amount").reindex(
        index=window_dates,
        columns=assets,
    )
    returns = close.pct_change(fill_method=None).iloc[1:]
    return returns, amount.iloc[1:]


def _market_residual_returns(
    returns: pd.DataFrame,
    policy: DynamicPeerPolicy,
) -> tuple[pd.DataFrame, pd.Series]:
    if returns.empty:
        return pd.DataFrame(index=returns.index), pd.Series(dtype="float64")
    counts = returns.notna().sum(axis=1)
    market = returns.median(axis=1, skipna=True).where(
        counts.ge(policy.market_min_cross_section)
    )
    residuals: dict[str, pd.Series] = {}
    betas: dict[str, float] = {}
    for asset_id in returns.columns:
        paired = pd.concat(
            [returns[asset_id].rename("asset"), market.rename("market")],
            axis=1,
        ).dropna()
        if len(paired) < policy.beta_min_observations:
            continue
        market_variance = float(paired["market"].var(ddof=0))
        if not np.isfinite(market_variance) or market_variance <= 0.0:
            continue
        covariance = float(paired[["asset", "market"]].cov(ddof=0).iloc[0, 1])
        beta = covariance / market_variance
        alpha = float(paired["asset"].mean() - beta * paired["market"].mean())
        residuals[str(asset_id)] = returns[asset_id] - alpha - beta * market
        betas[str(asset_id)] = beta
    return pd.DataFrame(residuals, index=returns.index), pd.Series(betas, dtype="float64")


def _select_top_peers(
    correlations: pd.DataFrame,
    pair_observations: pd.DataFrame,
    *,
    valid_from: pd.Timestamp,
    valid_to: pd.Timestamp,
    source_end_date: pd.Timestamp,
    policy: DynamicPeerPolicy,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset_id in correlations.columns:
        candidates = []
        for peer_asset_id, similarity in correlations[asset_id].items():
            if peer_asset_id == asset_id or pd.isna(similarity):
                continue
            observations = int(pair_observations.loc[asset_id, peer_asset_id])
            if observations < policy.pair_min_observations:
                continue
            value = float(np.clip(similarity, -1.0, 1.0))
            if value < policy.min_correlation:
                continue
            candidates.append((peer_asset_id, value, observations))
        selected = sorted(candidates, key=lambda item: (-item[1], str(item[0])))[: policy.max_peers]
        if len(selected) < policy.min_peers:
            continue
        for rank, (peer_asset_id, similarity, observations) in enumerate(selected, start=1):
            rows.append(
                {
                    "asset_id": str(asset_id),
                    "peer_asset_id": str(peer_asset_id),
                    "valid_from": valid_from,
                    "valid_to": valid_to,
                    "known_from": valid_from,
                    "source_end_date": source_end_date,
                    "similarity": similarity,
                    "pair_observations": observations,
                    "peer_rank": rank,
                    "peer_count": len(selected),
                    "mapping_method": MAPPING_METHOD,
                    "source": "processed_cn_etf_adjusted_close",
                }
            )
    return rows


def _reference_exposures(
    returns: pd.DataFrame,
    residuals: pd.DataFrame,
    betas: pd.Series,
    amounts: pd.DataFrame,
    policy: DynamicPeerPolicy,
) -> pd.DataFrame:
    assets = residuals.columns
    output = pd.DataFrame(index=assets)
    output["market_beta_120"] = betas.reindex(assets)
    output["residual_volatility_60"] = _tail_std(
        residuals,
        policy.residual_volatility_window,
    )
    output["momentum_60"] = _tail_compound(returns, policy.momentum_window)
    output["short_return_5"] = _tail_compound(returns, policy.short_return_window)
    liquidity = amounts.tail(policy.liquidity_window)
    liquidity_count = liquidity.notna().sum()
    liquidity_value = liquidity.median()
    liquidity_value = liquidity_value.where(
        liquidity_count.ge(min(policy.liquidity_window, len(amounts)))
    )
    output["log_adv20"] = np.log1p(liquidity_value.reindex(assets).clip(lower=0.0))
    return output


def _tail_std(frame: pd.DataFrame, window: int) -> pd.Series:
    tail = frame.tail(window)
    minimum = min(window, len(frame))
    return tail.std(ddof=1).where(tail.notna().sum().ge(minimum))


def _tail_compound(frame: pd.DataFrame, window: int) -> pd.Series:
    tail = frame.tail(window)
    minimum = min(window, len(frame))
    values = (1.0 + tail).prod(skipna=True) - 1.0
    return values.where(tail.notna().sum().ge(minimum))


def _reciprocity_rate(mapping: pd.DataFrame) -> float:
    if mapping.empty:
        return 0.0
    edges = {
        (str(row.asset_id), str(row.peer_asset_id))
        for row in mapping.itertuples(index=False)
    }
    return _safe_ratio(sum((peer, asset) in edges for asset, peer in edges), len(edges))


def _summarize_stability(
    mapping: pd.DataFrame,
    valid_dates: pd.Series,
) -> pd.DataFrame:
    dates = sorted(pd.to_datetime(valid_dates, errors="coerce").dropna().unique())
    rows = []
    mapping_dates = (
        pd.to_datetime(mapping["valid_from"], errors="coerce")
        if not mapping.empty
        else pd.Series(dtype="datetime64[ns]")
    )
    for previous_date, current_date in zip(dates, dates[1:]):
        previous = _peer_sets(mapping.loc[mapping_dates.eq(previous_date)]) if not mapping.empty else {}
        current = _peer_sets(mapping.loc[mapping_dates.eq(current_date)]) if not mapping.empty else {}
        comparable = sorted(set(previous).intersection(current))
        jaccards = []
        retentions = []
        complete_churn = 0
        for asset_id in comparable:
            intersection = previous[asset_id].intersection(current[asset_id])
            union = previous[asset_id].union(current[asset_id])
            jaccards.append(_safe_ratio(len(intersection), len(union)))
            retentions.append(_safe_ratio(len(intersection), len(previous[asset_id])))
            complete_churn += int(not intersection)
        rows.append(
            {
                "previous_valid_from": pd.Timestamp(previous_date),
                "valid_from": pd.Timestamp(current_date),
                "comparable_assets": int(len(comparable)),
                "median_jaccard": float(np.median(jaccards)) if jaccards else 0.0,
                "median_retention": float(np.median(retentions)) if retentions else 0.0,
                "complete_churn_rate": _safe_ratio(complete_churn, len(comparable)),
            }
        )
    return pd.DataFrame(rows, columns=STABILITY_COLUMNS)


def _peer_sets(mapping: pd.DataFrame) -> dict[str, set[str]]:
    return {
        str(asset_id): set(frame["peer_asset_id"].astype(str))
        for asset_id, frame in mapping.groupby("asset_id", sort=False)
    }


def _empty_snapshot_row(
    valid_from: pd.Timestamp,
    valid_to: pd.Timestamp,
    *,
    source_end_date: pd.Timestamp | None,
) -> dict[str, Any]:
    return {
        "valid_from": valid_from,
        "valid_to": valid_to,
        "source_end_date": source_end_date,
        "eligible_assets": 0,
        "return_ready_assets": 0,
        "residual_ready_assets": 0,
        "mapped_assets": 0,
        "mapping_edges": 0,
        "reciprocity_rate": 0.0,
        "median_selected_similarity": 0.0,
    }


def _validate_policy(policy: DynamicPeerPolicy) -> None:
    positive_fields = {
        "return_window": policy.return_window,
        "min_asset_return_observations": policy.min_asset_return_observations,
        "market_min_cross_section": policy.market_min_cross_section,
        "beta_min_observations": policy.beta_min_observations,
        "pair_min_observations": policy.pair_min_observations,
        "max_peers": policy.max_peers,
        "min_peers": policy.min_peers,
        "residual_volatility_window": policy.residual_volatility_window,
        "momentum_window": policy.momentum_window,
        "short_return_window": policy.short_return_window,
        "liquidity_window": policy.liquidity_window,
    }
    invalid = [name for name, value in positive_fields.items() if int(value) < 1]
    if invalid:
        raise ValueError("dynamic peer policy requires positive values: " + ", ".join(invalid))
    if policy.min_asset_return_observations > policy.return_window:
        raise ValueError("min_asset_return_observations cannot exceed return_window")
    if policy.beta_min_observations > policy.return_window:
        raise ValueError("beta_min_observations cannot exceed return_window")
    if policy.pair_min_observations > policy.return_window:
        raise ValueError("pair_min_observations cannot exceed return_window")
    if policy.min_peers > policy.max_peers:
        raise ValueError("min_peers cannot exceed max_peers")
    if not -1.0 <= policy.min_correlation <= 1.0:
        raise ValueError("min_correlation must be between -1 and 1")
    months = tuple(int(month) for month in policy.rebalance_months)
    if not months or len(set(months)) != len(months) or any(month < 1 or month > 12 for month in months):
        raise ValueError("rebalance_months must contain unique calendar months")


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return 0.0 if not denominator else float(numerator) / float(denominator)
