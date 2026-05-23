import unittest

from quant_robot.assets.calendars import calendar_for_market
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


if __name__ == "__main__":
    unittest.main()
