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


def load_authority_bars_config(path: str | Path) -> AuthorityBarsConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return AuthorityBarsConfig(
        market=str(data.get("market", "CN")).upper(),
        segments=tuple(_segment(item) for item in data.get("segments", [])),
    )


def load_authority_processed_bars_from_config(path: str | Path, markets: tuple[str, ...]) -> pd.DataFrame:
    config = load_authority_bars_config(path)
    requested = {market.upper() for market in markets if market.upper() != "ALL"}
    if requested and requested != {config.market}:
        raise ValueError(f"authority bars config market {config.market} does not match requested markets: {', '.join(sorted(requested))}")
    return load_authority_processed_bars(config.segments, market=config.market)


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
