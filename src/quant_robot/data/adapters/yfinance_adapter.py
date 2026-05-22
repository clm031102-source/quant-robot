from __future__ import annotations

import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.data.adapters.base import FetchRequest, MarketDataAdapter, require_optional_dependency


class YFinanceAdapter(MarketDataAdapter):
    name = "yfinance"
    supported_markets = {"HK", "US"}

    def supports(self, asset: Asset) -> bool:
        return asset.market.upper() in self.supported_markets

    def fetch_ohlcv(self, asset: Asset, request: FetchRequest) -> pd.DataFrame:
        require_optional_dependency("yfinance")
        raise NotImplementedError("yfinance live fetching is intentionally outside the phase-one fixture loop")
