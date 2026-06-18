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

        self.assertTrue(AkshareAdapter().supports(cn))
        self.assertTrue(AkshareAdapter().supports(etf))
        self.assertFalse(AkshareAdapter().supports(hk))
        self.assertFalse(AkshareAdapter().supports(us))
        self.assertTrue(TushareAdapter().supports(cn))
        self.assertTrue(TushareAdapter().supports(etf))
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

    def test_ccxt_adapter_paginates_until_end_date(self):
        class FakeExchange:
            def __init__(self):
                self.calls = []
                self.rows = [
                    [1704067200000, 42000.0, 43000.0, 41000.0, 42500.0, 2.0],
                    [1704153600000, 42500.0, 43500.0, 42000.0, 43000.0, 3.0],
                    [1704240000000, 43000.0, 44000.0, 42500.0, 43500.0, 4.0],
                ]

            def fetch_ohlcv(self, symbol, timeframe, since, limit):
                self.calls.append((symbol, timeframe, since, limit))
                page = [row for row in self.rows if row[0] >= since]
                return page[:limit]

        exchange = FakeExchange()
        adapter = CcxtAdapter(exchange=exchange, limit=2)
        asset = Asset("CRYPTO_BINANCE_BTC_USDT", "BTC/USDT", "CRYPTO", "BINANCE", "crypto_spot", "USDT", "UTC", "24/7")

        result = adapter.fetch_ohlcv(asset, FetchRequest("2024-01-01", "2024-01-03"))

        self.assertEqual(len(exchange.calls), 2)
        self.assertEqual(list(result["close"]), [42500.0, 43000.0, 43500.0])

    def test_akshare_adapter_maps_cn_stock_daily_bars(self):
        class FakeAkshare:
            def stock_zh_a_hist(self, **kwargs):
                self.kwargs = kwargs
                return pd.DataFrame(
                    {
                        "日期": ["2024-01-02"],
                        "开盘": [10.0],
                        "最高": [10.5],
                        "最低": [9.8],
                        "收盘": [10.2],
                        "成交量": [10000],
                        "成交额": [102000.0],
                    }
                )

        client = FakeAkshare()
        adapter = AkshareAdapter(client=client)
        asset = Asset("CN_XSHG_600519", "600519.SH", "CN", "XSHG", "stock", "CNY", "Asia/Shanghai", "XSHG")

        result = adapter.fetch_ohlcv(asset, FetchRequest("2024-01-01", "2024-01-31", adjustment="qfq"))

        self.assertEqual(client.kwargs["symbol"], "600519")
        self.assertEqual(client.kwargs["period"], "daily")
        self.assertEqual(client.kwargs["start_date"], "20240101")
        self.assertEqual(client.kwargs["end_date"], "20240131")
        self.assertEqual(client.kwargs["adjust"], "qfq")
        self.assertEqual(result.loc[0, "close"], 10.2)
        self.assertEqual(result.loc[0, "amount"], 102000.0)

    def test_akshare_adapter_maps_cn_etf_daily_bars(self):
        class FakeAkshare:
            def fund_etf_hist_em(self, **kwargs):
                self.kwargs = kwargs
                return pd.DataFrame(
                    {
                        "日期": ["2024-01-02"],
                        "开盘": [3.0],
                        "最高": [3.2],
                        "最低": [2.9],
                        "收盘": [3.1],
                        "成交量": [5000],
                    }
                )

        client = FakeAkshare()
        adapter = AkshareAdapter(client=client)
        asset = Asset("CN_ETF_XSHG_510300", "510300.SH", "CN_ETF", "XSHG", "etf", "CNY", "Asia/Shanghai", "XSHG")

        result = adapter.fetch_ohlcv(asset, FetchRequest("2024-01-01", "2024-01-31"))

        self.assertEqual(client.kwargs["symbol"], "510300")
        self.assertEqual(result.loc[0, "adj_close"], 3.1)
        self.assertEqual(result.loc[0, "amount"], 15500.0)

    def test_tushare_adapter_fetches_exchange_traded_fund_basic(self):
        class FakeTushare:
            def fund_basic(self, **kwargs):
                self.kwargs = kwargs
                return pd.DataFrame(
                    {
                        "ts_code": ["510300.SH"],
                        "name": ["CSI 300 ETF"],
                        "management": ["Manager A"],
                        "custodian": ["Bank A"],
                        "fund_type": ["Equity"],
                        "found_date": ["20120528"],
                        "due_date": [""],
                        "list_date": ["20120601"],
                        "issue_date": ["20120501"],
                        "delist_date": [""],
                        "status": ["L"],
                        "invest_type": ["Passive"],
                        "type": ["ETF"],
                        "market": ["E"],
                    }
                )

        client = FakeTushare()
        adapter = TushareAdapter(client=client)

        result = adapter.fetch_fund_basic()

        self.assertEqual(client.kwargs["market"], "E")
        self.assertEqual(client.kwargs["status"], "L")
        self.assertEqual(result.loc[0, "symbol"], "510300.SH")
        self.assertTrue(bool(result.loc[0, "is_etf"]))

    def test_tushare_adapter_fetches_etf_share_size_by_trade_date_and_exchange(self):
        class FakeTushare:
            def etf_share_size(self, **kwargs):
                self.kwargs = kwargs
                return pd.DataFrame(
                    {
                        "trade_date": ["20240102"],
                        "ts_code": ["510300.SH"],
                        "etf_name": ["CSI 300 ETF"],
                        "total_share": [100.0],
                        "total_size": [400.0],
                        "nav": [4.0],
                        "close": [4.04],
                        "exchange": ["SSE"],
                    }
                )

        client = FakeTushare()
        adapter = TushareAdapter(client=client)

        result = adapter.fetch_etf_share_size_by_trade_date("2024-01-02", exchange="SSE")

        self.assertEqual(client.kwargs["trade_date"], "20240102")
        self.assertEqual(client.kwargs["exchange"], "SSE")
        self.assertIn("total_share", client.kwargs["fields"])
        self.assertEqual(result.loc[0, "symbol"], "510300.SH")
        self.assertEqual(result.loc[0, "total_size"], 400.0 * 10000.0)

    def test_tushare_adapter_fetches_fund_portfolio(self):
        class FakeTushare:
            def fund_portfolio(self, **kwargs):
                self.kwargs = kwargs
                return pd.DataFrame(
                    {
                        "ts_code": ["510300.SH"],
                        "ann_date": ["20240110"],
                        "end_date": ["20231231"],
                        "symbol": ["600519.SH"],
                        "mkv": [123.4],
                        "amount": [10.0],
                        "stk_mkv_ratio": [4.37],
                        "stk_float_ratio": [0.01],
                    }
                )

        client = FakeTushare()
        adapter = TushareAdapter(client=client)

        result = adapter.fetch_fund_portfolio("510300.SH", start_date="2024-01-01", end_date="2024-12-31")

        self.assertEqual(client.kwargs["ts_code"], "510300.SH")
        self.assertEqual(client.kwargs["start_date"], "20240101")
        self.assertEqual(client.kwargs["end_date"], "20241231")
        self.assertIn("ann_date", client.kwargs["fields"])
        self.assertEqual(result.loc[0, "fund_symbol"], "510300.SH")
        self.assertEqual(str(result.loc[0, "known_date"]), "2024-01-10")


if __name__ == "__main__":
    unittest.main()
