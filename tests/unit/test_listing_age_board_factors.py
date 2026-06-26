import unittest

import pandas as pd

from quant_robot.factors.listing_age_board import (
    LISTING_AGE_BOARD_FACTOR_NAMES,
    compute_listing_age_board_factors,
)


class ListingAgeBoardFactorTests(unittest.TestCase):
    def test_computes_listing_age_and_board_candidates_from_stock_basic(self) -> None:
        bars = pd.DataFrame(
            {
                "date": [pd.Timestamp("2024-01-02")] * 5 + [pd.Timestamp("2024-01-03")] * 5,
                "asset_id": [f"CN_XSHG_{idx:06d}" for idx in range(5)] * 2,
                "market": ["CN"] * 10,
            }
        )
        stock_basic = pd.DataFrame(
            {
                "asset_id": [f"CN_XSHG_{idx:06d}" for idx in range(5)],
                "symbol": ["600000.SH", "688001.SH", "300001.SZ", "920001.BJ", "601000.SH"],
                "exchange": ["XSHG", "XSHG", "XSHE", "XBEI", "XSHG"],
                "stock_market": ["主板", "科创板", "创业板", "北交所", "主板"],
                "list_date": [
                    pd.Timestamp("2000-01-01"),
                    pd.Timestamp("2023-12-01"),
                    pd.Timestamp("2020-01-01"),
                    pd.Timestamp("2022-01-01"),
                    pd.Timestamp("2010-01-01"),
                ],
                "delist_date": [pd.NaT] * 5,
            }
        )

        result = compute_listing_age_board_factors(bars, stock_basic=stock_basic)

        self.assertEqual(set(result["factor_name"].unique()), set(LISTING_AGE_BOARD_FACTOR_NAMES))
        self.assertEqual(result["market"].unique().tolist(), ["CN"])
        self.assertGreater(result["factor_value"].notna().sum(), 0)
        self.assertIn("board_permission_mainboard_preference", set(result["factor_name"]))

    def test_unknown_factor_name_is_rejected(self) -> None:
        bars = pd.DataFrame({"date": [pd.Timestamp("2024-01-02")], "asset_id": ["CN_XSHG_600000"], "market": ["CN"]})
        with self.assertRaises(ValueError):
            compute_listing_age_board_factors(bars, stock_basic=pd.DataFrame(), factor_names=("unknown_factor",))


if __name__ == "__main__":
    unittest.main()
