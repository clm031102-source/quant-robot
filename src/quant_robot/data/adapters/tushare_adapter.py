from __future__ import annotations

import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.data.adapters.base import FetchRequest, MarketDataAdapter, require_optional_dependency


class TushareAdapter(MarketDataAdapter):
    name = "tushare"

    def supports(self, asset: Asset) -> bool:
        return asset.market.upper() == "CN"

    def fetch_ohlcv(self, asset: Asset, request: FetchRequest) -> pd.DataFrame:
        require_optional_dependency("tushare")
        raise NotImplementedError("Tushare live fetching requires an explicit token-enabled phase")
