from __future__ import annotations

import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.data.adapters.base import FetchRequest, MarketDataAdapter, require_optional_dependency


class YFinanceAdapter(MarketDataAdapter):
    name = "yfinance"
    supported_markets = {"HK", "US"}

    def __init__(self, client: object | None = None) -> None:
        self._client = client

    def supports(self, asset: Asset) -> bool:
        return asset.market.upper() in self.supported_markets

    def fetch_ohlcv(self, asset: Asset, request: FetchRequest) -> pd.DataFrame:
        raw = self.client.download(
            tickers=asset.symbol,
            start=request.start,
            end=request.end,
            interval=_yfinance_interval(request.frequency),
            auto_adjust=False,
            progress=False,
        )
        return _map_yfinance_download(raw)

    @property
    def client(self) -> object:
        if self._client is None:
            require_optional_dependency("yfinance")
            import yfinance as yf  # type: ignore[import-not-found]

            self._client = yf
        return self._client


def _map_yfinance_download(frame: pd.DataFrame) -> pd.DataFrame:
    if isinstance(frame.columns, pd.MultiIndex):
        frame = _flatten_yfinance_columns(frame)
    source = frame.reset_index()
    date_column = next((column for column in ("Date", "Datetime", "index") if column in source.columns), source.columns[0])
    mapped = pd.DataFrame(
        {
            "date": pd.to_datetime(source[date_column]).dt.date,
            "open": pd.to_numeric(source["Open"], errors="coerce"),
            "high": pd.to_numeric(source["High"], errors="coerce"),
            "low": pd.to_numeric(source["Low"], errors="coerce"),
            "close": pd.to_numeric(source["Close"], errors="coerce"),
            "adj_close": pd.to_numeric(source.get("Adj Close", source["Close"]), errors="coerce"),
            "volume": pd.to_numeric(source["Volume"], errors="coerce"),
        }
    )
    mapped["amount"] = mapped["close"] * mapped["volume"]
    return mapped.sort_values("date").reset_index(drop=True)


def _flatten_yfinance_columns(frame: pd.DataFrame) -> pd.DataFrame:
    price_fields = {"Open", "High", "Low", "Close", "Adj Close", "Volume"}
    columns = frame.columns
    for level in range(columns.nlevels):
        values = {str(value) for value in columns.get_level_values(level)}
        if values & price_fields:
            flattened = frame.copy()
            flattened.columns = columns.get_level_values(level)
            return flattened.loc[:, ~flattened.columns.duplicated()]

    flattened = frame.copy()
    flattened.columns = columns.get_level_values(-1)
    return flattened.loc[:, ~flattened.columns.duplicated()]


def _yfinance_interval(frequency: str) -> str:
    return {"1d": "1d", "1wk": "1wk", "1mo": "1mo"}.get(frequency, frequency)
