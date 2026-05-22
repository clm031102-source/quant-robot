from __future__ import annotations

import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.data.adapters.base import FetchRequest, MarketDataAdapter, require_optional_dependency


class AkshareAdapter(MarketDataAdapter):
    name = "akshare"
    supported_markets = {"CN", "HK", "US"}

    def supports(self, asset: Asset) -> bool:
        return asset.market.upper() in self.supported_markets

    def fetch_ohlcv(self, asset: Asset, request: FetchRequest) -> pd.DataFrame:
        require_optional_dependency("akshare")
        raise NotImplementedError("AKShare live fetching is intentionally outside the phase-one fixture loop")
