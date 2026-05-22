from __future__ import annotations

MARKET_DATA_COLUMNS = [
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
    "amount",
    "vwap",
    "currency",
    "source",
    "adjusted",
    "ingested_at",
]

REQUIRED_RAW_OHLCV_COLUMNS = ["date", "open", "high", "low", "close", "volume"]
