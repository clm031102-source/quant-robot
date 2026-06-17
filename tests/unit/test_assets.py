import unittest

import pandas as pd

from quant_robot.assets.calendars import calendar_for_market
from quant_robot.assets.etf_universe import cn_etf_assets_from_tushare_fund_basic, filter_tushare_cn_etf_fund_basic
from quant_robot.assets.models import Asset
from quant_robot.assets.registry import AssetRegistry


class AssetTests(unittest.TestCase):
    def test_asset_import_smoke(self):
        asset = Asset(
            asset_id="US_XNAS_AAPL",
            symbol="AAPL",
            market="US",
            exchange="XNAS",
            asset_type="stock",
            currency="USD",
            timezone="America/New_York",
            calendar="XNYS",
        )

        self.assertEqual(asset.asset_id, "US_XNAS_AAPL")

    def test_asset_requires_canonical_fields(self):
        asset = Asset(
            asset_id="CN_XSHG_600519",
            symbol="600519",
            market="CN",
            exchange="XSHG",
            asset_type="stock",
            currency="CNY",
            timezone="Asia/Shanghai",
            calendar="XSHG",
        )

        self.assertEqual(asset.market, "CN")
        self.assertEqual(asset.timezone, "Asia/Shanghai")

    def test_asset_rejects_empty_required_fields(self):
        with self.assertRaises(ValueError):
            Asset(
                asset_id="",
                symbol="AAPL",
                market="US",
                exchange="XNAS",
                asset_type="stock",
                currency="USD",
                timezone="America/New_York",
                calendar="XNYS",
            )

    def test_registry_finds_asset_by_id(self):
        asset = Asset(
            asset_id="CRYPTO_BINANCE_BTC_USDT",
            symbol="BTC/USDT",
            market="CRYPTO",
            exchange="BINANCE",
            asset_type="crypto_spot",
            currency="USDT",
            timezone="UTC",
            calendar="24/7",
        )
        registry = AssetRegistry([asset])

        self.assertEqual(registry.get("CRYPTO_BINANCE_BTC_USDT"), asset)

    def test_registry_rejects_duplicate_asset_ids(self):
        asset = Asset(
            asset_id="US_XNAS_AAPL",
            symbol="AAPL",
            market="US",
            exchange="XNAS",
            asset_type="stock",
            currency="USD",
            timezone="America/New_York",
            calendar="XNYS",
        )

        with self.assertRaises(ValueError):
            AssetRegistry([asset, asset])

    def test_calendar_for_market_defaults(self):
        self.assertEqual(calendar_for_market("CN", "XSHG"), "XSHG")
        self.assertEqual(calendar_for_market("CN_ETF", "XSHE"), "XSHE")
        self.assertEqual(calendar_for_market("HK", "XHKG"), "XHKG")
        self.assertEqual(calendar_for_market("US", "XNAS"), "XNYS")
        self.assertEqual(calendar_for_market("CRYPTO", "BINANCE"), "24/7")

    def test_filter_tushare_cn_etf_fund_basic_keeps_point_in_time_active_etfs(self):
        funds = pd.DataFrame(
            {
                "symbol": ["510300.SH", "159915.SZ", "501001.SH", "588000.SH", "510500.SH"],
                "name": ["CSI 300 ETF", "ChiNext ETF", "Listed LOF", "STAR 50 ETF", "CSI 500 ETF"],
                "fund_type": ["Equity", "Equity", "Mixed", "ETF", "Equity"],
                "type": ["ETF", "ETF", "LOF", "ETF", "ETF"],
                "market": ["E", "E", "E", "E", "E"],
                "status": ["L", "L", "L", "L", "D"],
                "list_date": [
                    pd.Timestamp("2012-06-01").date(),
                    pd.Timestamp("2015-01-01").date(),
                    pd.Timestamp("2016-01-01").date(),
                    pd.Timestamp("2026-01-01").date(),
                    pd.Timestamp("2013-01-01").date(),
                ],
                "delist_date": [pd.NaT, pd.NaT, pd.NaT, pd.NaT, pd.Timestamp("2024-01-01").date()],
                "is_active": [True, True, True, True, False],
                "is_exchange_traded": [True, True, True, True, True],
                "is_etf": [True, True, False, True, True],
            }
        )

        filtered = filter_tushare_cn_etf_fund_basic(funds, as_of="2024-12-31")
        assets = cn_etf_assets_from_tushare_fund_basic(funds, as_of="2024-12-31")

        self.assertEqual(filtered["symbol"].tolist(), ["159915.SZ", "510300.SH"])
        self.assertEqual({asset.asset_id for asset in assets}, {"CN_ETF_XSHG_510300", "CN_ETF_XSHE_159915"})
        self.assertTrue(all(asset.market == "CN_ETF" for asset in assets))


if __name__ == "__main__":
    unittest.main()
