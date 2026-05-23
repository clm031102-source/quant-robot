import unittest

import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.data.adapters.akshare_adapter import AkshareAdapter
from quant_robot.data.adapters.base import FetchRequest, MarketDataAdapter
from quant_robot.data.adapters.ccxt_adapter import CcxtAdapter
from quant_robot.data.adapters.tushare_adapter import TushareAdapter
from quant_robot.data.adapters.yfinance_adapter import YFinanceAdapter


class AdapterTests(unittest.TestCase):
    def test_fetch_request_captures_range_and_adjustment(self):
        request = FetchRequest(start="2024-01-01", end="2024-01-31", frequency="1d", adjustment="qfq")

        self.assertEqual(request.frequency, "1d")
        self.assertEqual(request.adjustment, "qfq")

    def test_adapter_modules_import_without_optional_dependencies(self):
        self.assertTrue(issubclass(YFinanceAdapter, MarketDataAdapter))
        self.assertTrue(issubclass(CcxtAdapter, MarketDataAdapter))

    def test_adapters_advertise_supported_markets(self):
        cn = Asset("CN_XSHG_600519", "600519", "CN", "XSHG", "stock", "CNY", "Asia/Shanghai", "XSHG")
        etf = Asset("CN_ETF_XSHG_510300", "510300.SH", "CN_ETF", "XSHG", "etf", "CNY", "Asia/Shanghai", "XSHG")
        hk = Asset("HK_XHKG_0700", "0700.HK", "HK", "XHKG", "stock", "HKD", "Asia/Hong_Kong", "XHKG")
        us = Asset("US_XNAS_AAPL", "AAPL", "US", "XNAS", "stock", "USD", "America/New_York", "XNYS")
        crypto = Asset("CRYPTO_BINANCE_BTC_USDT", "BTC/USDT", "CRYPTO", "BINANCE", "crypto_spot", "USDT", "UTC", "24/7")

        self.assertFalse(AkshareAdapter().supports(cn))
        self.assertFalse(AkshareAdapter().supports(etf))
        self.assertFalse(AkshareAdapter().supports(hk))
        self.assertFalse(AkshareAdapter().supports(us))
        self.assertTrue(TushareAdapter().supports(cn))
        self.assertFalse(TushareAdapter().supports(etf))
        self.assertTrue(YFinanceAdapter().supports(hk))
        self.assertTrue(YFinanceAdapter().supports(us))
        self.assertTrue(CcxtAdapter().supports(crypto))
        self.assertFalse(CcxtAdapter().supports(us))

    def test_yfinance_adapter_maps_downloaded_bars(self):
        class FakeYFinance:
            def download(self, **kwargs):
                self.kwargs = kwargs
                return pd.DataFrame(
                    {
                        "Open": [100.0],
                        "High": [102.0],
                        "Low": [99.0],
                        "Close": [101.0],
                        "Adj Close": [100.5],
                        "Volume": [1000],
                    },
                    index=pd.to_datetime(["2024-01-02"]),
                )

        client = FakeYFinance()
        adapter = YFinanceAdapter(client=client)
        asset = Asset("US_XNAS_AAPL", "AAPL", "US", "XNAS", "stock", "USD", "America/New_York", "XNYS")

        result = adapter.fetch_ohlcv(asset, FetchRequest("2024-01-01", "2024-01-31"))

        self.assertEqual(client.kwargs["tickers"], "AAPL")
        self.assertEqual(result.loc[0, "adj_close"], 100.5)
        self.assertEqual(result.loc[0, "amount"], 101000.0)

    def test_yfinance_adapter_handles_single_ticker_multiindex_download(self):
        columns = pd.MultiIndex.from_tuples(
            [
                ("Open", "AAPL"),
                ("High", "AAPL"),
                ("Low", "AAPL"),
                ("Close", "AAPL"),
                ("Adj Close", "AAPL"),
                ("Volume", "AAPL"),
            ]
        )

        class FakeYFinance:
            def download(self, **kwargs):
                return pd.DataFrame(
                    [[100.0, 102.0, 99.0, 101.0, 100.5, 1000]],
                    columns=columns,
                    index=pd.to_datetime(["2024-01-02"]),
                )

        adapter = YFinanceAdapter(client=FakeYFinance())
        asset = Asset("US_XNAS_AAPL", "AAPL", "US", "XNAS", "stock", "USD", "America/New_York", "XNYS")

        result = adapter.fetch_ohlcv(asset, FetchRequest("2024-01-01", "2024-01-31"))

        self.assertEqual(result.loc[0, "open"], 100.0)
        self.assertEqual(result.loc[0, "volume"], 1000)

    def test_ccxt_adapter_maps_exchange_ohlcv_bars(self):
        class FakeExchange:
            def fetch_ohlcv(self, symbol, timeframe, since, limit):
                self.args = (symbol, timeframe, since, limit)
                return [[1704153600000, 42000.0, 43000.0, 41000.0, 42500.0, 2.0]]

        exchange = FakeExchange()
        adapter = CcxtAdapter(exchange=exchange)
        asset = Asset("CRYPTO_BINANCE_BTC_USDT", "BTC/USDT", "CRYPTO", "BINANCE", "crypto_spot", "USDT", "UTC", "24/7")

        result = adapter.fetch_ohlcv(asset, FetchRequest("2024-01-01", "2024-01-31"))

        self.assertEqual(exchange.args[0], "BTC/USDT")
        self.assertEqual(result.loc[0, "close"], 42500.0)
        self.assertEqual(result.loc[0, "amount"], 85000.0)


if __name__ == "__main__":
    unittest.main()
