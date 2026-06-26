import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.dragon_tiger_pit_ic_prescreen import (
    DRAGON_TIGER_CANDIDATE_NAMES,
    build_dragon_tiger_pit_ic_prescreen,
    compute_dragon_tiger_factor_frame,
    write_dragon_tiger_pit_ic_prescreen,
)


class DragonTigerPitIcPrescreenTests(unittest.TestCase):
    def test_compute_factor_frame_uses_available_date_not_event_date(self) -> None:
        stock_day = _dragon_tiger_stock_day(assets=5, event_dates=pd.bdate_range("2024-01-02", periods=1))
        bars = _bars(assets=5, days=12)

        factors = compute_dragon_tiger_factor_frame(stock_day, bars)

        self.assertEqual(set(factors["factor_name"]), set(DRAGON_TIGER_CANDIDATE_NAMES))
        self.assertEqual(set(pd.to_datetime(factors["event_date"]).dt.date.astype(str)), {"2024-01-02"})
        self.assertEqual(set(pd.to_datetime(factors["date"]).dt.date.astype(str)), {"2024-01-03"})
        self.assertTrue((pd.to_datetime(factors["date"]) > pd.to_datetime(factors["event_date"])).all())
        self.assertTrue((factors["pit_lag_trade_days"] == 1).all())
        self.assertTrue(factors["factor_value"].notna().all())

    def test_same_day_available_date_rows_are_dropped(self) -> None:
        stock_day = _dragon_tiger_stock_day(assets=3, event_dates=pd.bdate_range("2024-01-02", periods=1))
        stock_day.loc[0, "available_date"] = stock_day.loc[0, "date"]

        factors = compute_dragon_tiger_factor_frame(stock_day, _bars(assets=3, days=8))

        same_day_asset = stock_day.loc[0, "asset_id"]
        self.assertNotIn(same_day_asset, set(factors["asset_id"]))

    def test_build_and_writer_keep_portfolio_and_promotion_blocked(self) -> None:
        bars = _bars(assets=20, days=18)
        stock_basic = _stock_basic(assets=20)
        stock_day = _dragon_tiger_stock_day(assets=20, event_dates=pd.bdate_range("2024-01-02", periods=8))

        result = build_dragon_tiger_pit_ic_prescreen(
            stock_day=stock_day,
            bars=bars,
            stock_basic=stock_basic,
            horizons=(1,),
            execution_lag=0,
            min_cross_section=20,
            min_ic_observations=4,
            min_neutral_ic_t_stat=0.0,
        )

        self.assertEqual(result["stage"], "dragon_tiger_pit_event_ic_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 5)
        self.assertEqual(result["summary"]["factor_names_with_rows"], 5)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])

        with tempfile.TemporaryDirectory() as tmp:
            write_dragon_tiger_pit_ic_prescreen(tmp, result)
            output = Path(tmp)
            self.assertTrue((output / "dragon_tiger_pit_ic_prescreen.json").exists())
            self.assertTrue((output / "dragon_tiger_pit_ic_prescreen.md").exists())
            self.assertTrue((output / "dragon_tiger_pit_ic_results.csv").exists())
            self.assertTrue((output / "dragon_tiger_pit_ic_observations.csv").exists())
            self.assertTrue((output / "dragon_tiger_pit_neutral_observations.csv").exists())


def _dragon_tiger_stock_day(assets: int, event_dates: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    for date_idx, event_date in enumerate(event_dates):
        for asset_idx in range(assets):
            net_amount = (asset_idx - assets / 2) * 1_000_000.0
            amount = 100_000_000.0 + asset_idx * 1_000_000.0
            rows.append(
                {
                    "date": event_date,
                    "available_date": event_date + pd.offsets.BDay(1),
                    "asset_id": f"CN_XSHE_{asset_idx:06d}",
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "source": "fixture",
                    "top_list_event_count": 1.0 + (asset_idx % 2),
                    "top_list_reason_count": 1.0,
                    "top_list_amount_sum": amount,
                    "top_list_net_amount_sum": net_amount,
                    "top_list_abs_pct_change_max": 3.0 + asset_idx * 0.1 + date_idx * 0.01,
                    "top_list_amount_rate_max": 5.0 + asset_idx * 0.2,
                    "top_inst_event_count": 1.0,
                    "top_inst_reason_count": 1.0,
                    "top_inst_buy_sum": 30_000_000.0 + asset_idx * 100_000.0,
                    "top_inst_sell_sum": 20_000_000.0 + (assets - asset_idx) * 100_000.0,
                    "top_inst_net_buy_sum": 10_000_000.0 + asset_idx * 200_000.0,
                    "top_inst_abs_net_buy_sum": abs(10_000_000.0 + asset_idx * 200_000.0),
                }
            )
    return pd.DataFrame(rows)


def _bars(assets: int, days: int) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=days)
    rows = []
    for asset_idx in range(assets):
        price = 10.0 + asset_idx
        for day_idx, date_value in enumerate(dates):
            price = price * (1.0 + (asset_idx % 5) * 0.001 + day_idx * 0.00001)
            rows.append(
                {
                    "date": date_value,
                    "asset_id": f"CN_XSHE_{asset_idx:06d}",
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "amount": 30_000_000.0 + asset_idx * 1_000_000.0 + day_idx,
                }
            )
    return pd.DataFrame(rows)


def _stock_basic(assets: int) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "asset_id": f"CN_XSHE_{asset_idx:06d}",
                "symbol": f"{asset_idx:06d}.SZ",
                "market": "CN",
                "industry": "Tech" if asset_idx < assets // 2 else "Bank",
            }
            for asset_idx in range(assets)
        ]
    )


if __name__ == "__main__":
    unittest.main()
