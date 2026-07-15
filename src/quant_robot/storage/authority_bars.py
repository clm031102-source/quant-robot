from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.data.quality import validate_market_data
from quant_robot.storage.dataset_store import DatasetStore


AUTHORITY_DUPLICATE_KEYS = ("asset_id", "timestamp", "frequency")
AUTHORITY_INPUT_DUPLICATE_KEYS = ("date", "asset_id", "market")


@dataclass(frozen=True)
class AuthorityBarSegment:
    root: Path
    start_date: str | None = None
    end_date: str | None = None
    adjusted_only: bool = True


@dataclass(frozen=True)
class AuthorityBarsConfig:
    market: str
    segments: tuple[AuthorityBarSegment, ...]
    stock_basic_root: Path | None = None
    enforce_official_lifecycle: bool = False
    exclude_assets_without_lifecycle_metadata: bool = False
    repair_adjusted_ratio_mass_jumps: bool = False
    exclude_adjusted_ratio_jump_assets: bool = False
    adjusted_ratio_jump_threshold: float = 2.0
    adjusted_ratio_mass_jump_asset_threshold: int = 100


def load_authority_bars_config(path: str | Path) -> AuthorityBarsConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    stock_basic_root = data.get("stock_basic_root")
    return AuthorityBarsConfig(
        market=str(data.get("market", "CN")).upper(),
        segments=tuple(_segment(item) for item in data.get("segments", [])),
        stock_basic_root=Path(str(stock_basic_root)) if stock_basic_root else None,
        enforce_official_lifecycle=bool(data.get("enforce_official_lifecycle", False)),
        exclude_assets_without_lifecycle_metadata=bool(
            data.get("exclude_assets_without_lifecycle_metadata", False)
        ),
        repair_adjusted_ratio_mass_jumps=bool(data.get("repair_adjusted_ratio_mass_jumps", False)),
        exclude_adjusted_ratio_jump_assets=bool(data.get("exclude_adjusted_ratio_jump_assets", False)),
        adjusted_ratio_jump_threshold=float(data.get("adjusted_ratio_jump_threshold", 2.0)),
        adjusted_ratio_mass_jump_asset_threshold=int(data.get("adjusted_ratio_mass_jump_asset_threshold", 100)),
    )


def load_authority_processed_bars_from_config(path: str | Path, markets: tuple[str, ...]) -> pd.DataFrame:
    config = load_authority_bars_config(path)
    requested = {market.upper() for market in markets if market.upper() != "ALL"}
    if requested and requested != {config.market}:
        raise ValueError(f"authority bars config market {config.market} does not match requested markets: {', '.join(sorted(requested))}")
    bars = load_authority_processed_dataset(
        config.segments,
        market=config.market,
        dataset="processed/bars",
        duplicate_keys=AUTHORITY_DUPLICATE_KEYS,
    )
    if config.exclude_assets_without_lifecycle_metadata and not config.enforce_official_lifecycle:
        raise ValueError(
            "exclude_assets_without_lifecycle_metadata requires enforce_official_lifecycle"
        )
    if config.enforce_official_lifecycle:
        if config.stock_basic_root is None:
            raise ValueError("enforce_official_lifecycle requires stock_basic_root")
        stock_basic = _load_official_stock_basic(config.stock_basic_root)
        bars = _filter_bars_to_official_lifecycle(
            bars,
            stock_basic,
            exclude_assets_without_metadata=config.exclude_assets_without_lifecycle_metadata,
        )
    if config.repair_adjusted_ratio_mass_jumps:
        bars = repair_adjusted_ratio_mass_jumps(
            bars,
            jump_threshold=config.adjusted_ratio_jump_threshold,
            mass_jump_asset_threshold=config.adjusted_ratio_mass_jump_asset_threshold,
        )
    if config.exclude_adjusted_ratio_jump_assets:
        bars = exclude_adjusted_ratio_jump_assets(
            bars,
            jump_threshold=config.adjusted_ratio_jump_threshold,
        )
    validate_market_data(bars)
    return bars


def repair_adjusted_ratio_mass_jumps(
    bars: pd.DataFrame,
    *,
    jump_threshold: float = 2.0,
    mass_jump_asset_threshold: int = 100,
) -> pd.DataFrame:
    required = {"date", "asset_id", "close", "adj_close"}
    if bars.empty or not required.issubset(bars.columns):
        return bars.copy()
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    ratio = pd.to_numeric(_adjusted_ratio(frame), errors="coerce")
    jumps = _adjusted_ratio_jump_frame(frame, ratio, jump_threshold)
    mass_dates = set(
        jumps.groupby(jumps["date"].dt.date)["asset_id"]
        .nunique()
        .loc[lambda counts: counts >= int(mass_jump_asset_threshold)]
        .index
    )
    if not mass_dates:
        return frame
    repaired = frame.copy()
    previous_ratio = ratio.groupby(frame["asset_id"], sort=False).shift(1)
    ratio_change = pd.to_numeric(ratio / previous_ratio, errors="coerce")
    reciprocal = 1.0 / ratio_change.where(ratio_change != 0)
    jump_score = pd.concat([ratio_change, reciprocal], axis=1).abs().max(axis=1)
    event_mask = (
        frame["date"].dt.date.isin(mass_dates)
        & ratio.notna()
        & previous_ratio.notna()
        & (ratio > 0)
        & (previous_ratio > 0)
        & (pd.to_numeric(jump_score, errors="coerce") > float(jump_threshold))
    )
    event_correction = pd.Series(1.0, index=frame.index)
    event_correction.loc[event_mask] = previous_ratio.loc[event_mask].astype(float) / ratio.loc[event_mask].astype(float)
    cumulative_correction = event_correction.groupby(frame["asset_id"], sort=False).cumprod()
    repaired["adj_close"] = pd.to_numeric(repaired["adj_close"], errors="coerce") * cumulative_correction
    return repaired


def exclude_adjusted_ratio_jump_assets(
    bars: pd.DataFrame,
    *,
    jump_threshold: float = 2.0,
) -> pd.DataFrame:
    required = {"date", "asset_id", "close", "adj_close"}
    if bars.empty or not required.issubset(bars.columns):
        return bars.copy()
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    ratio = pd.to_numeric(_adjusted_ratio(frame), errors="coerce")
    jumps = _adjusted_ratio_jump_frame(frame, ratio, jump_threshold)
    if jumps.empty:
        return frame
    blocked_assets = set(jumps["asset_id"].astype(str))
    return frame[~frame["asset_id"].astype(str).isin(blocked_assets)].reset_index(drop=True)


def load_authority_processed_dataset_from_config(
    path: str | Path,
    *,
    market: str,
    dataset: str,
    duplicate_keys: tuple[str, ...] = AUTHORITY_INPUT_DUPLICATE_KEYS,
) -> pd.DataFrame:
    config = load_authority_bars_config(path)
    if config.market != market.upper():
        raise ValueError(f"authority dataset config market {config.market} does not match requested market {market.upper()}")
    return load_authority_processed_dataset(
        config.segments,
        market=market,
        dataset=dataset,
        duplicate_keys=duplicate_keys,
    )


def load_authority_processed_bars(
    segments: tuple[AuthorityBarSegment, ...] | list[AuthorityBarSegment],
    *,
    market: str,
) -> pd.DataFrame:
    bars = load_authority_processed_dataset(
        segments,
        market=market,
        dataset="processed/bars",
        duplicate_keys=AUTHORITY_DUPLICATE_KEYS,
    )
    validate_market_data(bars)
    return bars


def load_authority_processed_dataset(
    segments: tuple[AuthorityBarSegment, ...] | list[AuthorityBarSegment],
    *,
    market: str,
    dataset: str,
    duplicate_keys: tuple[str, ...] = AUTHORITY_INPUT_DUPLICATE_KEYS,
) -> pd.DataFrame:
    frames = []
    for segment in segments:
        frames.extend(_load_segment(segment, market.upper(), dataset))
    if not frames:
        raise FileNotFoundError(f"No authority {dataset} found")
    frame = pd.concat(frames, ignore_index=True)
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    _reject_duplicate_authority_keys(frame, duplicate_keys, dataset)
    return frame


def _segment(data: dict[str, Any]) -> AuthorityBarSegment:
    return AuthorityBarSegment(
        root=Path(str(data["root"])),
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
        adjusted_only=bool(data.get("adjusted_only", True)),
    )


def _load_official_stock_basic(root: Path) -> pd.DataFrame:
    nested = root / "metadata" / "tushare_stock_basic"
    dataset_root = nested if nested.is_dir() else root
    paths = sorted(dataset_root.rglob("*.parquet")) if dataset_root.is_dir() else []
    if not paths:
        raise FileNotFoundError(f"No official stock_basic parquet found under {root}")
    frame = pd.concat((pd.read_parquet(path) for path in paths), ignore_index=True)
    required = {"asset_id", "list_date"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"official stock_basic missing columns: {', '.join(missing)}")
    metadata = frame.loc[:, [column for column in ["asset_id", "list_date", "delist_date"] if column in frame]].copy()
    if metadata["asset_id"].isna().any():
        raise ValueError("official stock_basic contains missing asset_id")
    metadata["asset_id"] = metadata["asset_id"].astype(str)
    duplicate_mask = metadata["asset_id"].duplicated(keep=False)
    if duplicate_mask.any():
        sample = metadata.loc[duplicate_mask, "asset_id"].head(5).tolist()
        raise ValueError(f"duplicate stock_basic asset_id: {sample}")
    metadata["list_date"] = pd.to_datetime(metadata["list_date"], errors="coerce")
    if "delist_date" not in metadata:
        metadata["delist_date"] = pd.NaT
    metadata["delist_date"] = pd.to_datetime(metadata["delist_date"], errors="coerce")
    reverse_mask = (
        metadata["list_date"].notna()
        & metadata["delist_date"].notna()
        & (metadata["delist_date"] < metadata["list_date"])
    )
    if reverse_mask.any():
        sample = metadata.loc[reverse_mask, "asset_id"].head(5).tolist()
        raise ValueError(f"official stock_basic delist_date precedes list_date: {sample}")
    return metadata


def _filter_bars_to_official_lifecycle(
    bars: pd.DataFrame,
    stock_basic: pd.DataFrame,
    *,
    exclude_assets_without_metadata: bool,
) -> pd.DataFrame:
    metadata = stock_basic.rename(
        columns={"list_date": "_official_list_date", "delist_date": "_official_delist_date"}
    )
    frame = bars.copy()
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame = frame.merge(metadata, on="asset_id", how="left", validate="many_to_one")
    dates = pd.to_datetime(frame["date"], errors="coerce")
    known = frame["_official_list_date"].notna()
    within_lifecycle = (
        known
        & dates.ge(frame["_official_list_date"])
        & (
            frame["_official_delist_date"].isna()
            | dates.le(frame["_official_delist_date"])
        )
    )
    keep = within_lifecycle if exclude_assets_without_metadata else within_lifecycle | ~known
    return frame.loc[keep, bars.columns].reset_index(drop=True)


def _adjusted_ratio(frame: pd.DataFrame) -> pd.Series:
    close = pd.to_numeric(frame["close"], errors="coerce")
    adj_close = pd.to_numeric(frame["adj_close"], errors="coerce")
    return (adj_close / close.where(close > 0)).replace([float("inf"), float("-inf")], pd.NA)


def _adjusted_ratio_jump_frame(frame: pd.DataFrame, ratio: pd.Series, threshold: float) -> pd.DataFrame:
    work = frame.loc[:, ["date", "asset_id"]].copy()
    work["adjusted_ratio"] = ratio
    work = work.dropna(subset=["date", "asset_id", "adjusted_ratio"]).sort_values(["asset_id", "date"])
    previous = work.groupby("asset_id", sort=False)["adjusted_ratio"].shift(1)
    ratio_change = pd.to_numeric(work["adjusted_ratio"] / previous, errors="coerce")
    reciprocal = 1.0 / ratio_change.where(ratio_change != 0)
    work["adjusted_ratio_jump"] = pd.concat([ratio_change, reciprocal], axis=1).abs().max(axis=1)
    return work[pd.to_numeric(work["adjusted_ratio_jump"], errors="coerce") > float(threshold)]


def _load_segment(segment: AuthorityBarSegment, market: str, dataset: str) -> list[pd.DataFrame]:
    store = DatasetStore(segment.root)
    base = store.partition_path(dataset, {"frequency": "1d", "market": market})
    frames = []
    for year_path in sorted(base.glob("year=*")):
        year = year_path.name.split("=", 1)[1]
        frame = store.read_frame(dataset, {"frequency": "1d", "market": market, "year": year})
        frame = _filter_segment_frame(frame, segment)
        if not frame.empty:
            frames.append(frame)
    return frames


def _filter_segment_frame(frame: pd.DataFrame, segment: AuthorityBarSegment) -> pd.DataFrame:
    result = frame.copy()
    if segment.adjusted_only and "adjusted" in result.columns:
        result = result[_bool_series(result["adjusted"])]
    dates = pd.to_datetime(result["date"]).dt.date
    if segment.start_date:
        result = result[dates >= pd.to_datetime(segment.start_date).date()]
        dates = pd.to_datetime(result["date"]).dt.date
    if segment.end_date:
        result = result[dates <= pd.to_datetime(segment.end_date).date()]
    return result.reset_index(drop=True)


def _bool_series(values: pd.Series) -> pd.Series:
    if values.dtype == bool:
        return values
    return values.astype(str).str.lower().isin({"true", "1", "yes"})


def _reject_duplicate_authority_keys(frame: pd.DataFrame, duplicate_keys: tuple[str, ...], dataset: str) -> None:
    duplicate_mask = frame.duplicated(list(duplicate_keys), keep=False)
    if not duplicate_mask.any():
        return
    sample = frame.loc[duplicate_mask, list(duplicate_keys)].head(5).to_dict(orient="records")
    label = "bars" if dataset == "processed/bars" else dataset
    raise ValueError(f"duplicate authority {label}: {sample}")
