import unittest

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
        hk = Asset("HK_XHKG_0700", "0700.HK", "HK", "XHKG", "stock", "HKD", "Asia/Hong_Kong", "XHKG")
        us = Asset("US_XNAS_AAPL", "AAPL", "US", "XNAS", "stock", "USD", "America/New_York", "XNYS")
        crypto = Asset("CRYPTO_BINANCE_BTC_USDT", "BTC/USDT", "CRYPTO", "BINANCE", "crypto_spot", "USDT", "UTC", "24/7")

        self.assertTrue(AkshareAdapter().supports(cn))
        self.assertTrue(AkshareAdapter().supports(hk))
        self.assertTrue(AkshareAdapter().supports(us))
        self.assertTrue(TushareAdapter().supports(cn))
        self.assertTrue(YFinanceAdapter().supports(hk))
        self.assertTrue(YFinanceAdapter().supports(us))
        self.assertTrue(CcxtAdapter().supports(crypto))
        self.assertFalse(CcxtAdapter().supports(us))


if __name__ == "__main__":
    unittest.main()
