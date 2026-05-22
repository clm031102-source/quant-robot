from __future__ import annotations

from pathlib import Path

import pandas as pd


def parse_tradingview_csv(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    columns = {_canonical_column(column): column for column in frame.columns}
    required = ["time", "open", "high", "low", "close", "volume"]
    missing = [column for column in required if column not in columns]
    if missing:
        raise ValueError(f"TradingView CSV is missing columns: {', '.join(missing)}")

    timestamps = pd.to_datetime(frame[columns["time"]], utc=True, errors="coerce")
    return pd.DataFrame(
        {
            "date": timestamps.dt.date,
            "open": pd.to_numeric(frame[columns["open"]], errors="coerce"),
            "high": pd.to_numeric(frame[columns["high"]], errors="coerce"),
            "low": pd.to_numeric(frame[columns["low"]], errors="coerce"),
            "close": pd.to_numeric(frame[columns["close"]], errors="coerce"),
            "volume": pd.to_numeric(frame[columns["volume"]], errors="coerce"),
        }
    ).sort_values(["date"]).reset_index(drop=True)


def _canonical_column(column: str) -> str:
    normalized = column.strip().lower().replace(" ", "_")
    if normalized in {"volume", "vol"}:
        return "volume"
    if normalized in {"time", "date", "datetime"}:
        return "time"
    return normalized
