import unittest

import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.data.normalize import normalize_ohlcv
from quant_robot.data.quality import validate_market_data


class NormalizeTests(unittest.TestCase):
    def test_normalize_adds_canonical_asset_fields_and_utc_timestamp(self):
        asset = Asset(
            "US_XNAS_AAPL",
            "AAPL",
            "US",
            "XNAS",
            "stock",
            "USD",
            "America/New_York",
            "XNYS",
        )
        raw = pd.DataFrame(
            {
                "date": ["2024-01-02"],
                "open": [100.0],
                "high": [110.0],
                "low": [99.0],
                "close": [105.0],
                "volume": [1000.0],
                "amount": [105000.0],
            }
        )

        result = normalize_ohlcv(raw, asset, source="fixture", frequency="1d")

        self.assertEqual(result.loc[0, "asset_id"], "US_XNAS_AAPL")
        self.assertEqual(result.loc[0, "symbol"], "AAPL")
        self.assertEqual(str(result.loc[0, "timestamp"].tz), "UTC")
        self.assertEqual(str(result.loc[0, "date"]), "2024-01-02")
        self.assertEqual(result.loc[0, "adj_close"], 105.0)
        self.assertEqual(result.loc[0, "vwap"], 105.0)

    def test_normalize_preserves_provided_adjusted_close(self):
        asset = Asset("HK_XHKG_0700", "0700.HK", "HK", "XHKG", "stock", "HKD", "Asia/Hong_Kong", "XHKG")
        raw = pd.DataFrame(
            {
                "date": ["2024-01-02"],
                "open": [100.0],
                "high": [110.0],
                "low": [99.0],
                "close": [105.0],
                "adj_close": [104.0],
                "volume": [1000.0],
            }
        )

        result = normalize_ohlcv(raw, asset, source="fixture", frequency="1d")

        self.assertEqual(result.loc[0, "adj_close"], 104.0)
        self.assertTrue(pd.isna(result.loc[0, "amount"]))

    def test_validate_rejects_duplicate_bars(self):
        asset = Asset("CN_XSHG_600519", "600519", "CN", "XSHG", "stock", "CNY", "Asia/Shanghai", "XSHG")
        raw = pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-02"],
                "open": [1.0, 1.0],
                "high": [2.0, 2.0],
                "low": [1.0, 1.0],
                "close": [1.5, 1.5],
                "volume": [10.0, 10.0],
            }
        )

        result = normalize_ohlcv(raw, asset, source="fixture", frequency="1d")

        with self.assertRaises(ValueError):
            validate_market_data(result)

    def test_validate_rejects_inconsistent_ohlc(self):
        asset = Asset("US_XNAS_AAPL", "AAPL", "US", "XNAS", "stock", "USD", "America/New_York", "XNYS")
        raw = pd.DataFrame(
            {
                "date": ["2024-01-02"],
                "open": [100.0],
                "high": [99.0],
                "low": [95.0],
                "close": [105.0],
                "volume": [1000.0],
            }
        )

        result = normalize_ohlcv(raw, asset, source="fixture", frequency="1d")

        with self.assertRaises(ValueError):
            validate_market_data(result)

    def test_validate_rejects_missing_required_price_values(self):
        asset = Asset("US_XNAS_AAPL", "AAPL", "US", "XNAS", "stock", "USD", "America/New_York", "XNYS")
        raw = pd.DataFrame(
            {
                "date": ["2024-01-02"],
                "open": [100.0],
                "high": [101.0],
                "low": [99.0],
                "close": ["bad"],
                "volume": [1000.0],
            }
        )

        result = normalize_ohlcv(raw, asset, source="fixture", frequency="1d")

        with self.assertRaisesRegex(ValueError, "missing required values"):
            validate_market_data(result)


if __name__ == "__main__":
    unittest.main()
