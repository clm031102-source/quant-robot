from __future__ import annotations

import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.data.adapters.base import FetchRequest, MarketDataAdapter, require_optional_dependency


class CcxtAdapter(MarketDataAdapter):
    name = "ccxt"

    def __init__(self, exchange: object | None = None, exchange_id: str = "binance", limit: int = 1000) -> None:
        self._exchange = exchange
        self.exchange_id = exchange_id
        self.limit = limit

    def supports(self, asset: Asset) -> bool:
        return asset.market.upper() == "CRYPTO"

    def fetch_ohlcv(self, asset: Asset, request: FetchRequest) -> pd.DataFrame:
        since = int(pd.Timestamp(request.start, tz="UTC").timestamp() * 1000)
        rows = self.exchange.fetch_ohlcv(asset.symbol, _ccxt_timeframe(request.frequency), since, self.limit)
        frame = pd.DataFrame(rows, columns=["timestamp_ms", "open", "high", "low", "close", "volume"])
        if frame.empty:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "adj_close", "volume", "amount"])
        timestamps = pd.to_datetime(frame["timestamp_ms"], unit="ms", utc=True)
        mapped = pd.DataFrame(
            {
                "date": timestamps.dt.date,
                "open": pd.to_numeric(frame["open"], errors="coerce"),
                "high": pd.to_numeric(frame["high"], errors="coerce"),
                "low": pd.to_numeric(frame["low"], errors="coerce"),
                "close": pd.to_numeric(frame["close"], errors="coerce"),
                "adj_close": pd.to_numeric(frame["close"], errors="coerce"),
                "volume": pd.to_numeric(frame["volume"], errors="coerce"),
            }
        )
        mapped["amount"] = mapped["close"] * mapped["volume"]
        end_date = pd.to_datetime(request.end).date()
        return mapped[mapped["date"] <= end_date].sort_values("date").reset_index(drop=True)

    @property
    def exchange(self) -> object:
        if self._exchange is None:
            require_optional_dependency("ccxt")
            import ccxt  # type: ignore[import-not-found]

            self._exchange = getattr(ccxt, self.exchange_id)()
        return self._exchange


def _ccxt_timeframe(frequency: str) -> str:
    return {"1d": "1d", "1h": "1h", "1m": "1m"}.get(frequency, frequency)
