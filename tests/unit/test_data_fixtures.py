import unittest

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.data.quality import validate_market_data


class DataFixturesTests(unittest.TestCase):
    def test_demo_market_bars_cover_four_markets_and_validate_schema(self):
        bars = load_demo_market_bars()

        self.assertEqual(set(bars["market"]), {"CN", "HK", "US", "CRYPTO"})
        self.assertGreaterEqual(bars["asset_id"].nunique(), 8)
        validate_market_data(bars)


if __name__ == "__main__":
    unittest.main()
