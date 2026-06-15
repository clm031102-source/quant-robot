from __future__ import annotations

import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.data.adapters.base import FetchRequest, MarketDataAdapter, require_optional_dependency


class AkshareAdapter(MarketDataAdapter):
    name = "akshare"
    supported_markets = {"CN", "CN_ETF"}

    def __init__(self, client: object | None = None) -> None:
        self._client = client

    def supports(self, asset: Asset) -> bool:
        return asset.market.upper() in self.supported_markets

    def fetch_ohlcv(self, asset: Asset, request: FetchRequest) -> pd.DataFrame:
        kwargs = {
            "symbol": _symbol_code(asset.symbol),
            "period": _akshare_period(request.frequency),
            "start_date": _date_to_akshare(request.start),
            "end_date": _date_to_akshare(request.end),
            "adjust": _akshare_adjust(request.adjustment),
        }
        if asset.market.upper() == "CN_ETF":
            raw = self.client.fund_etf_hist_em(**kwargs)
        else:
            raw = self.client.stock_zh_a_hist(**kwargs)
        return _map_akshare_hist(raw)

    @property
    def client(self) -> object:
        if self._client is None:
            require_optional_dependency("akshare")
            import akshare as ak  # type: ignore[import-not-found]

            self._client = ak
        return self._client


def _map_akshare_hist(frame: pd.DataFrame) -> pd.DataFrame:
    mapped = pd.DataFrame(
        {
            "date": pd.to_datetime(_column(frame, "日期", "date")).dt.date,
            "open": pd.to_numeric(_column(frame, "开盘", "open"), errors="coerce"),
            "high": pd.to_numeric(_column(frame, "最高", "high"), errors="coerce"),
            "low": pd.to_numeric(_column(frame, "最低", "low"), errors="coerce"),
            "close": pd.to_numeric(_column(frame, "收盘", "close"), errors="coerce"),
            "volume": pd.to_numeric(_column(frame, "成交量", "volume"), errors="coerce"),
        }
    )
    mapped["adj_close"] = mapped["close"]
    if "成交额" in frame.columns:
        mapped["amount"] = pd.to_numeric(frame["成交额"], errors="coerce")
    elif "amount" in frame.columns:
        mapped["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    else:
        mapped["amount"] = mapped["close"] * mapped["volume"]
    return mapped.sort_values("date").reset_index(drop=True)


def _column(frame: pd.DataFrame, cn_name: str, en_name: str) -> pd.Series:
    if cn_name in frame.columns:
        return frame[cn_name]
    if en_name in frame.columns:
        return frame[en_name]
    raise KeyError(f"AKShare response missing column {cn_name!r}/{en_name!r}")


def _symbol_code(symbol: str) -> str:
    return symbol.split(".", 1)[0]


def _date_to_akshare(value: str) -> str:
    return value.replace("-", "")


def _akshare_adjust(adjustment: str) -> str:
    return "" if adjustment in {"", "none"} else adjustment


def _akshare_period(frequency: str) -> str:
    return {"1d": "daily", "1wk": "weekly", "1mo": "monthly"}.get(frequency, frequency)
