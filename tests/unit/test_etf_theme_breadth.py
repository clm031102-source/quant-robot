import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.factors.etf_theme_breadth import compute_etf_theme_breadth_factors
from quant_robot.storage.cn_etf_theme_map import build_cn_etf_theme_map, load_cn_etf_theme_map
from quant_robot.storage.dataset_store import DatasetStore


class EtfThemeBreadthTests(unittest.TestCase):
    def test_build_cn_etf_theme_map_classifies_all_history_etfs(self):
        fund_basic = pd.DataFrame(
            {
                "symbol": ["510300.SH", "512880.SH", "511880.SH", "150001.SZ"],
                "name": ["华泰柏瑞沪深300ETF", "国泰中证全指证券公司ETF", "银华日利货币ETF", "分级基金进取"],
                "market": ["E", "E", "E", "E"],
                "status": ["L", "L", "L", "D"],
                "fund_type": ["股票型", "股票型", "货币型", "股票型"],
                "type": ["股票型", "股票型", "货币型", "股票型"],
                "is_etf": [True, True, True, False],
                "list_date": ["2012-05-28", "2013-07-08", "2013-12-09", "2012-08-17"],
                "delist_date": [None, None, None, "2015-08-14"],
            }
        )

        theme_map = build_cn_etf_theme_map(fund_basic, source="fixture")

        self.assertEqual(set(theme_map["symbol"]), {"510300.SH", "512880.SH", "511880.SH"})
        themes = dict(zip(theme_map["symbol"], theme_map["theme"], strict=True))
        self.assertEqual(themes["510300.SH"], "broad_market")
        self.assertEqual(themes["512880.SH"], "sector_financial")
        self.assertEqual(themes["511880.SH"], "bond_cash")

    def test_load_cn_etf_theme_map_uses_latest_tushare_fund_basic_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = pd.DataFrame(
                {
                    "symbol": ["510300.SH"],
                    "name": ["华泰柏瑞沪深300ETF"],
                    "market": ["E"],
                    "fund_type": ["股票型"],
                    "type": ["股票型"],
                    "is_etf": [True],
                    "list_date": ["2012-05-28"],
                    "delist_date": [None],
                }
            )
            new = pd.concat(
                [
                    old,
                    pd.DataFrame(
                        {
                            "symbol": ["512880.SH"],
                            "name": ["国泰中证全指证券公司ETF"],
                            "market": ["E"],
                            "fund_type": ["股票型"],
                            "type": ["股票型"],
                            "is_etf": [True],
                            "list_date": ["2013-07-08"],
                            "delist_date": [None],
                        }
                    ),
                ],
                ignore_index=True,
            )
            store = DatasetStore(root)
            store.write_frame(old, "metadata/tushare_fund_basic", {"market": "E", "snapshot": "2024-01-01"})
            store.write_frame(new, "metadata/tushare_fund_basic", {"market": "E", "snapshot": "2024-02-01"})

            theme_map = load_cn_etf_theme_map(root)

            self.assertEqual(set(theme_map["symbol"]), {"510300.SH", "512880.SH"})

    def test_compute_theme_breadth_factors_are_same_day_past_only_group_proxies(self):
        bars = _theme_fixture_bars()
        theme_map = pd.DataFrame(
            {
                "asset_id": ["CN_ETF_XSHG_510001", "CN_ETF_XSHG_510002", "CN_ETF_XSHG_510003", "CN_ETF_XSHG_510004"],
                "theme": ["sector_tech", "sector_tech", "broad_market", "broad_market"],
                "known_date": [pd.Timestamp("2024-01-01").date()] * 4,
            }
        )

        factors = compute_etf_theme_breadth_factors(bars, theme_map, windows=(2,))

        day = pd.Timestamp("2024-01-03").date()
        tech_breadth = _factor_value(factors, "CN_ETF_XSHG_510001", day, "theme_momentum_breadth_2")
        tech_relative = _factor_value(factors, "CN_ETF_XSHG_510001", day, "theme_relative_strength_2")
        broad_breadth = _factor_value(factors, "CN_ETF_XSHG_510003", day, "theme_momentum_breadth_2")
        self.assertAlmostEqual(tech_breadth, 1.0)
        self.assertAlmostEqual(tech_relative, 0.075)
        self.assertAlmostEqual(broad_breadth, 0.0)

    def test_liquid_theme_strength_breaks_theme_ties_toward_more_tradable_etfs(self):
        bars = _theme_fixture_bars()
        bars["amount"] = bars["asset_id"].map(
            {
                "CN_ETF_XSHG_510001": 10_000_000.0,
                "CN_ETF_XSHG_510002": 1_000_000.0,
                "CN_ETF_XSHG_510003": 8_000_000.0,
                "CN_ETF_XSHG_510004": 2_000_000.0,
            }
        )
        theme_map = pd.DataFrame(
            {
                "asset_id": ["CN_ETF_XSHG_510001", "CN_ETF_XSHG_510002", "CN_ETF_XSHG_510003", "CN_ETF_XSHG_510004"],
                "theme": ["sector_tech", "sector_tech", "broad_market", "broad_market"],
                "known_date": [pd.Timestamp("2024-01-01").date()] * 4,
            }
        )

        factors = compute_etf_theme_breadth_factors(bars, theme_map, windows=(2,))

        day = pd.Timestamp("2024-01-03").date()
        high_liquidity = _factor_value(factors, "CN_ETF_XSHG_510001", day, "theme_rank_strength_liquid_2")
        low_liquidity = _factor_value(factors, "CN_ETF_XSHG_510002", day, "theme_rank_strength_liquid_2")
        self.assertGreater(high_liquidity, low_liquidity)


def _theme_fixture_bars() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=4).date
    paths = {
        "CN_ETF_XSHG_510001": [10.0, 11.0, 12.0, 13.0],
        "CN_ETF_XSHG_510002": [10.0, 9.0, 11.0, 12.0],
        "CN_ETF_XSHG_510003": [10.0, 10.0, 10.0, 10.0],
        "CN_ETF_XSHG_510004": [10.0, 10.0, 10.0, 10.0],
    }
    rows = []
    for asset_id, prices in paths.items():
        for date, price in zip(dates, prices, strict=True):
            rows.append(
                {
                    "date": date,
                    "asset_id": asset_id,
                    "market": "CN_ETF",
                    "adj_close": price,
                }
            )
    return pd.DataFrame(rows)


def _factor_value(factors: pd.DataFrame, asset_id: str, date: object, factor_name: str) -> float:
    row = factors[
        (factors["asset_id"] == asset_id)
        & (factors["date"] == date)
        & (factors["factor_name"] == factor_name)
    ].iloc[0]
    return float(row["factor_value"])


if __name__ == "__main__":
    unittest.main()
