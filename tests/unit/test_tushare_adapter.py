import unittest

import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.data.adapters.base import FetchRequest
from quant_robot.data.adapters.tushare_adapter import TushareAdapter


class FakeTushareClient:
    def __init__(self) -> None:
        self.calls = []

    def daily(self, **kwargs):
        self.calls.append(("daily", kwargs))
        return pd.DataFrame(
            {
                "ts_code": [kwargs.get("ts_code", "000001.SZ") or "000001.SZ"],
                "trade_date": [kwargs.get("trade_date", "20240102") or "20240102"],
                "open": [10.0],
                "high": [11.0],
                "low": [9.5],
                "close": [10.5],
                "vol": [100.0],
                "amount": [200.0],
            }
        )

    def fund_daily(self, **kwargs):
        self.calls.append(("fund_daily", kwargs))
        return pd.DataFrame(
            {
                "ts_code": [kwargs.get("ts_code", "510300.SH") or "510300.SH"],
                "trade_date": [kwargs.get("trade_date", "20240102") or "20240102"],
                "open": [4.0],
                "high": [4.1],
                "low": [3.9],
                "close": [4.05],
                "vol": [1000.0],
                "amount": [4050.0],
            }
        )

    def adj_factor(self, **kwargs):
        self.calls.append(("adj_factor", kwargs))
        return pd.DataFrame({"ts_code": ["000001.SZ"], "trade_date": ["20240102"], "adj_factor": [100.0]})

    def trade_cal(self, **kwargs):
        self.calls.append(("trade_cal", kwargs))
        return pd.DataFrame({"exchange": ["SSE"], "cal_date": ["20240102"], "is_open": [1]})

    def stock_basic(self, **kwargs):
        self.calls.append(("stock_basic", kwargs))
        return pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "symbol": ["000001"],
                "name": ["平安银行"],
                "exchange": ["SZSE"],
                "list_status": ["L"],
            }
        )


class TushareAdapterTests(unittest.TestCase):
    def test_fetch_ohlcv_uses_injected_client_and_maps_daily_data(self):
        client = FakeTushareClient()
        adapter = TushareAdapter(client=client)
        asset = Asset("CN_XSHE_000001", "000001.SZ", "CN", "XSHE", "stock", "CNY", "Asia/Shanghai", "XSHE")
        request = FetchRequest(start="2024-01-01", end="2024-01-31", frequency="1d", adjustment="none")

        result = adapter.fetch_ohlcv(asset, request)

        self.assertEqual(result.loc[0, "symbol"], "000001.SZ")
        self.assertEqual(result.loc[0, "volume"], 10000.0)
        self.assertEqual(client.calls[0][0], "daily")
        self.assertEqual(client.calls[0][1]["ts_code"], "000001.SZ")

    def test_fetch_daily_by_trade_date_supports_full_market_mode(self):
        client = FakeTushareClient()
        adapter = TushareAdapter(client=client)

        result = adapter.fetch_daily_by_trade_date("20240102")

        self.assertEqual(result.loc[0, "amount"], 200000.0)
        self.assertEqual(client.calls[0][1]["trade_date"], "20240102")

    def test_fetch_cn_etf_ohlcv_uses_fund_daily_endpoint(self):
        client = FakeTushareClient()
        adapter = TushareAdapter(client=client)
        asset = Asset("CN_ETF_XSHG_510300", "510300.SH", "CN_ETF", "XSHG", "etf", "CNY", "Asia/Shanghai", "XSHG")
        request = FetchRequest(start="2024-01-01", end="2024-01-31", frequency="1d", adjustment="none")

        result = adapter.fetch_ohlcv(asset, request)

        self.assertTrue(adapter.supports(asset))
        self.assertEqual(result.loc[0, "symbol"], "510300.SH")
        self.assertEqual(result.loc[0, "volume"], 100000.0)
        self.assertEqual(client.calls[0][0], "fund_daily")
        self.assertEqual(client.calls[0][1]["ts_code"], "510300.SH")

    def test_fetch_etf_daily_by_trade_date_supports_full_market_mode(self):
        client = FakeTushareClient()
        adapter = TushareAdapter(client=client)

        result = adapter.fetch_etf_daily_by_trade_date("20240102")

        self.assertEqual(result.loc[0, "symbol"], "510300.SH")
        self.assertEqual(client.calls[0][0], "fund_daily")
        self.assertEqual(client.calls[0][1]["trade_date"], "20240102")

    def test_fetch_metadata_methods_map_contracts(self):
        adapter = TushareAdapter(client=FakeTushareClient())

        self.assertEqual(str(adapter.fetch_trade_calendar("20240101", "20240131").loc[0, "date"]), "2024-01-02")
        self.assertEqual(adapter.fetch_stock_basic().loc[0, "asset_id"], "CN_XSHE_000001")
        self.assertEqual(adapter.fetch_adj_factor("000001.SZ", "20240101", "20240131").loc[0, "adj_factor"], 100.0)


if __name__ == "__main__":
    unittest.main()
