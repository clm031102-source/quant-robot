import unittest

import pandas as pd

from quant_robot.factors.cn_stock_champion import (
    CN_STOCK_CHAMPION_FACTOR_NAMES,
    compute_cn_stock_champion_factors,
)


class CnStockChampionFactorTests(unittest.TestCase):
    def test_computes_locked_rankic_neg1_downside_range_blend_with_tradeable_gate(self):
        bars = _synthetic_bars(asset_count=8, day_count=45)
        inputs = _synthetic_daily_basic(bars)

        factors = compute_cn_stock_champion_factors(
            bars,
            inputs,
            factor_names=("rankic_neg1_downside_range_blend",),
        )

        self.assertEqual(set(factors["factor_name"]), {"rankic_neg1_downside_range_blend"})
        self.assertEqual(set(factors.columns), {"date", "asset_id", "market", "factor_name", "factor_value", "lookback_window"})
        self.assertEqual(set(factors["lookback_window"]), {20})
        self.assertGreater(factors["factor_value"].notna().sum(), 0)
        high_momentum = factors[factors["asset_id"] == "CN_XSHG_000007"]
        self.assertEqual(int(high_momentum["factor_value"].notna().sum()), 0)

    def test_rejects_unknown_cn_stock_champion_factor_name(self):
        bars = _synthetic_bars(asset_count=3, day_count=25)
        inputs = _synthetic_daily_basic(bars)

        with self.assertRaisesRegex(ValueError, "Unsupported CN stock champion factor_names"):
            compute_cn_stock_champion_factors(bars, inputs, factor_names=("not_a_factor",))

    def test_exports_only_the_locked_champion_name(self):
        self.assertEqual(CN_STOCK_CHAMPION_FACTOR_NAMES, ("rankic_neg1_downside_range_blend",))


def _synthetic_bars(*, asset_count: int, day_count: int) -> pd.DataFrame:
    dates = pd.date_range("2024-11-01", periods=day_count, freq="B")
    rows = []
    for asset_index in range(asset_count):
        asset_id = f"CN_XSHG_{asset_index:06d}"
        for day_index, date in enumerate(dates):
            drift = 0.002 * day_index if asset_index == asset_count - 1 else 0.0004 * day_index
            price = 10.0 + asset_index * 0.4 + drift + (day_index % 5) * 0.03
            rows.append(
                {
                    "date": date.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "amount": 60_000_000 + asset_index * 5_000_000 + day_index * 100_000,
                    "adj_close": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "volume": 1_000_000 + asset_index * 20_000 + day_index * 1000,
                }
            )
    return pd.DataFrame(rows)


def _synthetic_daily_basic(bars: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in bars.itertuples(index=False):
        asset_number = int(str(row.asset_id).split("_")[-1])
        rows.append(
            {
                "date": row.date,
                "asset_id": row.asset_id,
                "market": row.market,
                "turnover_rate": 0.8 + asset_number * 0.08,
                "turnover_rate_f": 0.9 + asset_number * 0.08,
                "volume_ratio": 0.7 + asset_number * 0.05,
                "pe_ttm": 8.0 + asset_number,
                "pb": 0.8 + asset_number * 0.2,
                "dv_ttm": 2.0,
                "total_mv": 3_000_000_000 + asset_number * 100_000_000,
                "circ_mv": 2_000_000_000 + asset_number * 100_000_000,
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
