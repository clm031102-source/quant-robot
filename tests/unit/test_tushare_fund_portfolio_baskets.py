import unittest

import pandas as pd

from quant_robot.data.ingest.tushare_fund_portfolio import build_etf_moneyflow_baskets_from_fund_portfolio


class TushareFundPortfolioBasketTests(unittest.TestCase):
    def test_build_baskets_are_point_in_time_by_announcement_date(self):
        portfolio = pd.DataFrame(
            {
                "fund_symbol": ["510300.SH", "510300.SH", "510300.SH"],
                "known_date": [
                    pd.Timestamp("2024-01-10").date(),
                    pd.Timestamp("2024-01-10").date(),
                    pd.Timestamp("2024-04-20").date(),
                ],
                "period_end_date": [
                    pd.Timestamp("2023-12-31").date(),
                    pd.Timestamp("2023-12-31").date(),
                    pd.Timestamp("2024-03-31").date(),
                ],
                "stock_symbol": ["600519.SH", "000001.SZ", "600519.SH"],
                "mkv": [60.0, 40.0, 100.0],
                "amount": [1.0, 2.0, 3.0],
                "stk_mkv_ratio": [6.0, 4.0, 10.0],
                "stk_float_ratio": [0.1, 0.2, 0.3],
            }
        )

        baskets = build_etf_moneyflow_baskets_from_fund_portfolio(portfolio, eligible_etf_symbols=["510300.SH"])

        first_window = baskets[baskets["known_date"] == pd.Timestamp("2024-01-10").date()]
        second_window = baskets[baskets["known_date"] == pd.Timestamp("2024-04-20").date()]
        self.assertEqual(set(baskets["etf_asset_id"]), {"CN_ETF_XSHG_510300"})
        self.assertEqual(set(first_window["stock_asset_id"]), {"CN_XSHG_600519", "CN_XSHE_000001"})
        self.assertAlmostEqual(first_window[first_window["stock_symbol"] == "600519.SH"].iloc[0]["weight"], 0.6)
        self.assertAlmostEqual(first_window[first_window["stock_symbol"] == "000001.SZ"].iloc[0]["weight"], 0.4)
        self.assertEqual(set(first_window["end_date"]), {pd.Timestamp("2024-04-19").date()})
        self.assertAlmostEqual(second_window.iloc[0]["weight"], 1.0)
        self.assertTrue(pd.isna(second_window.iloc[0]["end_date"]))

    def test_build_baskets_reject_missing_known_date(self):
        portfolio = pd.DataFrame(
            {
                "fund_symbol": ["510300.SH"],
                "known_date": [pd.NaT],
                "period_end_date": [pd.Timestamp("2023-12-31").date()],
                "stock_symbol": ["600519.SH"],
                "mkv": [60.0],
            }
        )

        with self.assertRaisesRegex(ValueError, "known_date"):
            build_etf_moneyflow_baskets_from_fund_portfolio(portfolio)


if __name__ == "__main__":
    unittest.main()
