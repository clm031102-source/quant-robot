from __future__ import annotations

import pandas as pd

from quant_robot.schema.market_data import MARKET_DATA_COLUMNS


def validate_market_data(frame: pd.DataFrame) -> None:
    missing = [column for column in MARKET_DATA_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Market data is missing columns: {', '.join(missing)}")

    _validate_required_values(frame)

    duplicate_keys = ["asset_id", "timestamp", "frequency", "source"]
    if frame.duplicated(duplicate_keys).any():
        raise ValueError("Market data contains duplicate bars")

    _validate_non_negative(frame, ["open", "high", "low", "close", "adj_close", "volume", "amount"])
    _validate_ohlc(frame)
    _validate_monotonic_dates(frame)


def _validate_required_values(frame: pd.DataFrame) -> None:
    required = [
        "asset_id",
        "symbol",
        "market",
        "exchange",
        "asset_type",
        "timestamp",
        "date",
        "timezone",
        "calendar",
        "frequency",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "currency",
        "source",
        "adjusted",
        "ingested_at",
    ]
    missing_values = [column for column in required if frame[column].isna().any()]
    if missing_values:
        raise ValueError("Market data contains missing required values: " + ", ".join(missing_values))


def _validate_non_negative(frame: pd.DataFrame, columns: list[str]) -> None:
    for column in columns:
        values = frame[column].dropna()
        if (values < 0).any():
            raise ValueError(f"Market data column {column} contains negative values")


def _validate_ohlc(frame: pd.DataFrame) -> None:
    complete = frame[["open", "high", "low", "close"]].dropna()
    if complete.empty:
        return
    if (complete["high"] < complete["low"]).any():
        raise ValueError("Market data contains high below low")
    if (complete["high"] < complete[["open", "close"]].max(axis=1)).any():
        raise ValueError("Market data contains high below open or close")
    if (complete["low"] > complete[["open", "close"]].min(axis=1)).any():
        raise ValueError("Market data contains low above open or close")


def _validate_monotonic_dates(frame: pd.DataFrame) -> None:
    for asset_id, group in frame.sort_values(["asset_id", "timestamp"]).groupby("asset_id"):
        if not group["timestamp"].is_monotonic_increasing:
            raise ValueError(f"Market data timestamps are not monotonic for {asset_id}")
