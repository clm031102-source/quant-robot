from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class EtfEligibilityPolicy:
    min_prior_observations: int = 252
    liquidity_window: int = 20
    min_trailing_median_amount: float = 5_000_000.0
    max_stale_rate: float = 0.05
    max_abs_return: float = 0.20


def load_official_etf_lifecycle(metadata_root: str | Path) -> pd.DataFrame:
    root = Path(metadata_root)
    files = [root] if root.is_file() else sorted(root.rglob("*.parquet")) + sorted(root.rglob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No official ETF lifecycle files found under {root}")
    frames = []
    for path in files:
        frame = _normalise_lifecycle(_read_lifecycle_file(path))
        frame = frame[frame["is_etf"]].copy()
        _validate_lifecycle(frame)
        frame["_snapshot_date"] = _snapshot_date_for_path(path)
        frames.append(frame)
    lifecycle = _consolidate_dated_lifecycle(pd.concat(frames, ignore_index=True))
    _validate_lifecycle(lifecycle)
    return lifecycle.sort_values("symbol").reset_index(drop=True)


def build_point_in_time_etf_eligibility(
    bars: pd.DataFrame,
    lifecycle: pd.DataFrame,
    *,
    policy: EtfEligibilityPolicy = EtfEligibilityPolicy(),
) -> pd.DataFrame:
    _validate_policy(policy)
    frame = _normalise_bars(bars)
    official = _normalise_lifecycle(lifecycle)
    _validate_lifecycle(official)
    official = official.rename(
        columns={
            "is_etf": "official_is_etf",
            "list_date": "official_list_date",
            "delist_date": "official_delist_date",
        }
    )
    merged = frame.merge(
        official[["symbol", "official_is_etf", "official_list_date", "official_delist_date"]],
        on="symbol",
        how="left",
        validate="many_to_one",
        indicator=True,
    )
    merged["official_metadata_present"] = merged["_merge"].eq("both")
    merged["official_etf"] = merged["official_is_etf"].fillna(False).astype(bool)
    merged["within_official_lifecycle"] = (
        merged["official_etf"]
        & merged["official_list_date"].notna()
        & merged["date"].ge(merged["official_list_date"])
        & (merged["official_delist_date"].isna() | merged["date"].le(merged["official_delist_date"]))
    )

    pieces = [_eligibility_features(group, policy) for _, group in merged.groupby("asset_id", sort=False)]
    result = pd.concat(pieces, ignore_index=True) if pieces else merged.iloc[0:0].copy()
    result["history_ready"] = result["prior_observations"].ge(policy.min_prior_observations)
    result["liquidity_ready"] = result["trailing_median_amount"].ge(policy.min_trailing_median_amount)
    result["stale_price_ready"] = result["trailing_stale_rate"].le(policy.max_stale_rate)
    result["positive_price_amount"] = result["adj_close"].gt(0.0) & result["amount"].gt(0.0)
    result["price_move_ready"] = result["return_1d"].abs().le(policy.max_abs_return)
    result["eligible"] = result[
        [
            "official_metadata_present",
            "official_etf",
            "within_official_lifecycle",
            "history_ready",
            "liquidity_ready",
            "stale_price_ready",
            "positive_price_amount",
            "price_move_ready",
        ]
    ].all(axis=1)
    return result.drop(columns=["_merge"]).sort_values(["asset_id", "date"]).reset_index(drop=True)


def _eligibility_features(group: pd.DataFrame, policy: EtfEligibilityPolicy) -> pd.DataFrame:
    item = group.sort_values("date").copy()
    within = item["within_official_lifecycle"].astype(bool)
    price = pd.to_numeric(item["adj_close"], errors="coerce").where(within)
    amount = pd.to_numeric(item["amount"], errors="coerce").where(within)
    previous_price = price.shift(1)
    stale = price.eq(previous_price).where(within)
    item["prior_observations"] = within.astype(int).cumsum() - within.astype(int)
    item["trailing_median_amount"] = amount.rolling(
        policy.liquidity_window,
        min_periods=policy.liquidity_window,
    ).median()
    item["trailing_stale_rate"] = stale.astype(float).rolling(
        policy.liquidity_window,
        min_periods=policy.liquidity_window,
    ).mean()
    item["return_1d"] = price / previous_price - 1.0
    return item


def _read_lifecycle_file(path: Path) -> pd.DataFrame:
    if path.suffix.casefold() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def _snapshot_date_for_path(path: Path) -> pd.Timestamp | None:
    for part in reversed(path.parts):
        if not part.startswith("snapshot="):
            continue
        value = pd.to_datetime(part.split("=", 1)[1], errors="coerce")
        return None if pd.isna(value) else pd.Timestamp(value).normalize()
    return None


def _consolidate_dated_lifecycle(lifecycle: pd.DataFrame) -> pd.DataFrame:
    duplicate_rows = lifecycle[lifecycle["symbol"].duplicated(keep=False)]
    if not duplicate_rows.empty:
        invalid_symbols = []
        for symbol, group in duplicate_rows.groupby("symbol", sort=True):
            snapshots = group["_snapshot_date"]
            if snapshots.isna().any() or snapshots.duplicated().any():
                invalid_symbols.append(str(symbol))
        if invalid_symbols:
            raise ValueError(
                "duplicate official ETF lifecycle symbols: " + ", ".join(invalid_symbols[:10])
            )
    return (
        lifecycle.sort_values(["symbol", "_snapshot_date"], na_position="first")
        .drop_duplicates("symbol", keep="last")
        .drop(columns="_snapshot_date")
        .reset_index(drop=True)
    )


def _normalise_lifecycle(lifecycle: pd.DataFrame) -> pd.DataFrame:
    required = {"symbol", "is_etf", "list_date", "delist_date"}
    missing = sorted(required - set(lifecycle.columns))
    if missing:
        raise ValueError("Official ETF lifecycle is missing columns: " + ", ".join(missing))
    frame = lifecycle[["symbol", "is_etf", "list_date", "delist_date"]].copy()
    frame["symbol"] = frame["symbol"].astype(str).str.strip().str.upper()
    frame["is_etf"] = frame["is_etf"].map(_as_bool)
    frame["list_date"] = pd.to_datetime(frame["list_date"], errors="coerce")
    frame["delist_date"] = pd.to_datetime(frame["delist_date"], errors="coerce")
    return frame


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "asset_id", "symbol", "market", "adj_close", "amount"}
    missing = sorted(required - set(bars.columns))
    if missing:
        raise ValueError("ETF bars are missing columns: " + ", ".join(missing))
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["symbol"] = frame["symbol"].astype(str).str.strip().str.upper()
    frame["market"] = frame["market"].astype(str)
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    if frame[["date", "asset_id", "symbol"]].isna().any().any():
        raise ValueError("ETF bars contain missing date, asset_id, or symbol values")
    duplicates = frame.duplicated(["asset_id", "date"], keep=False)
    if duplicates.any():
        raise ValueError("ETF bars contain duplicate asset-date rows")
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _validate_lifecycle(lifecycle: pd.DataFrame) -> None:
    duplicates = lifecycle["symbol"].duplicated(keep=False)
    if duplicates.any():
        symbols = sorted(lifecycle.loc[duplicates, "symbol"].astype(str).unique())
        raise ValueError("duplicate official ETF lifecycle symbols: " + ", ".join(symbols[:10]))
    reversed_rows = lifecycle[
        lifecycle["list_date"].notna()
        & lifecycle["delist_date"].notna()
        & lifecycle["delist_date"].lt(lifecycle["list_date"])
    ]
    if not reversed_rows.empty:
        raise ValueError("reversed official ETF lifecycle: " + ", ".join(reversed_rows["symbol"].astype(str)))


def _validate_policy(policy: EtfEligibilityPolicy) -> None:
    if policy.min_prior_observations < 0:
        raise ValueError("min_prior_observations must be non-negative")
    if policy.liquidity_window < 1:
        raise ValueError("liquidity_window must be positive")
    if policy.min_trailing_median_amount < 0.0:
        raise ValueError("min_trailing_median_amount must be non-negative")
    if not 0.0 <= policy.max_stale_rate <= 1.0:
        raise ValueError("max_stale_rate must be between zero and one")
    if policy.max_abs_return <= 0.0:
        raise ValueError("max_abs_return must be positive")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().casefold() in {"1", "true", "yes", "y"}
