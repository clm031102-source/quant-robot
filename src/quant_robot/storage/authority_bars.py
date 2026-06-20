from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.data.quality import validate_market_data
from quant_robot.storage.dataset_store import DatasetStore


AUTHORITY_DUPLICATE_KEYS = ("asset_id", "timestamp", "frequency", "source")
AUTHORITY_INPUT_DUPLICATE_KEYS = ("date", "asset_id", "market", "source")


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
    repair_adjusted_ratio_mass_jumps: bool = False
    adjusted_ratio_jump_threshold: float = 2.0
    adjusted_ratio_mass_jump_asset_threshold: int = 100


def load_authority_bars_config(path: str | Path) -> AuthorityBarsConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return AuthorityBarsConfig(
        market=str(data.get("market", "CN")).upper(),
        segments=tuple(_segment(item) for item in data.get("segments", [])),
        repair_adjusted_ratio_mass_jumps=bool(data.get("repair_adjusted_ratio_mass_jumps", False)),
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
    if config.repair_adjusted_ratio_mass_jumps:
        bars = repair_adjusted_ratio_mass_jumps(
            bars,
            jump_threshold=config.adjusted_ratio_jump_threshold,
            mass_jump_asset_threshold=config.adjusted_ratio_mass_jump_asset_threshold,
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
