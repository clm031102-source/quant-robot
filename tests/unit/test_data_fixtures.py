import unittest

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.data.quality import validate_market_data


class DataFixturesTests(unittest.TestCase):
    def test_demo_market_bars_cover_research_markets_and_validate_schema(self):
        bars = load_demo_market_bars()

        self.assertEqual(set(bars["market"]), {"CN", "CN_ETF", "HK", "US", "CRYPTO"})
        self.assertGreaterEqual(bars["asset_id"].nunique(), 12)
        self.assertGreaterEqual((bars["asset_type"] == "etf").sum(), 1)
        validate_market_data(bars)

    def test_market_data_rejects_cross_source_duplicate_bars(self):
        bars = load_demo_market_bars()
        duplicate = bars.iloc[[0]].copy()
        duplicate["source"] = "second_provider"

        with self.assertRaisesRegex(ValueError, "duplicate bars"):
            validate_market_data(pd.concat([bars, duplicate], ignore_index=True))

    def test_market_data_rejects_out_of_order_rows_for_an_asset(self):
        bars = load_demo_market_bars()
        asset_id = bars["asset_id"].value_counts().index[0]
        asset_rows = bars[bars["asset_id"] == asset_id].sort_values("timestamp", ascending=False)
        other_rows = bars[bars["asset_id"] != asset_id]

        with self.assertRaisesRegex(ValueError, "not monotonic"):
            validate_market_data(pd.concat([asset_rows, other_rows], ignore_index=True))


if __name__ == "__main__":
    unittest.main()
