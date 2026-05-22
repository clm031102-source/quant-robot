from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.schema.market_data import MARKET_DATA_COLUMNS, REQUIRED_RAW_OHLCV_COLUMNS


def normalize_ohlcv(raw: pd.DataFrame, asset: Asset, source: str, frequency: str) -> pd.DataFrame:
    missing = [column for column in REQUIRED_RAW_OHLCV_COLUMNS if column not in raw.columns]
    if missing:
        raise ValueError(f"Raw OHLCV data is missing columns: {', '.join(missing)}")

    frame = raw.copy()
    local_dates = pd.to_datetime(frame["date"])
    timestamps = _to_utc_timestamp(local_dates, asset.timezone)

    normalized = pd.DataFrame(
        {
            "asset_id": asset.asset_id,
            "symbol": asset.symbol,
            "market": asset.market,
            "exchange": asset.exchange,
            "asset_type": asset.asset_type,
            "timestamp": timestamps,
            "date": local_dates.dt.date,
            "timezone": asset.timezone,
            "calendar": asset.calendar,
            "frequency": frequency,
            "open": pd.to_numeric(frame["open"], errors="coerce"),
            "high": pd.to_numeric(frame["high"], errors="coerce"),
            "low": pd.to_numeric(frame["low"], errors="coerce"),
            "close": pd.to_numeric(frame["close"], errors="coerce"),
            "adj_close": pd.to_numeric(frame.get("adj_close", frame["close"]), errors="coerce"),
            "volume": pd.to_numeric(frame["volume"], errors="coerce"),
            "amount": pd.to_numeric(frame.get("amount", np.nan), errors="coerce"),
            "currency": asset.currency,
            "source": source,
            "adjusted": "adj_close" in frame.columns,
            "ingested_at": pd.Timestamp.now(tz="UTC"),
        }
    )
    normalized["vwap"] = _safe_vwap(normalized["amount"], normalized["volume"])
    return normalized[MARKET_DATA_COLUMNS].sort_values(["asset_id", "timestamp"]).reset_index(drop=True)


def _to_utc_timestamp(values: pd.Series, timezone: str) -> pd.Series:
    if values.dt.tz is None:
        return values.dt.tz_localize(timezone).dt.tz_convert("UTC")
    return values.dt.tz_convert("UTC")


def _safe_vwap(amount: pd.Series, volume: pd.Series) -> pd.Series:
    with np.errstate(divide="ignore", invalid="ignore"):
        vwap = amount / volume.replace(0, np.nan)
    return vwap.replace([np.inf, -np.inf], np.nan)
