import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.dragon_tiger_size_residual_repair import (
    REPAIR_FACTOR_NAMES,
    build_dragon_tiger_size_residual_repair_prescreen,
    compute_dragon_tiger_size_residual_factor_frame,
    write_dragon_tiger_size_residual_repair_prescreen,
)


class DragonTigerSizeResidualRepairTests(unittest.TestCase):
    def test_residual_frame_reduces_log_adv20_exposure(self) -> None:
        dates = pd.bdate_range("2024-01-03", periods=4)
        rows = []
        for date_value in dates:
            for asset_idx in range(20):
                size = float(asset_idx)
                alpha = float(asset_idx % 5)
                rows.append(
                    {
                        "date": date_value,
                        "event_date": date_value - pd.offsets.BDay(1),
                        "asset_id": f"CN_XSHE_{asset_idx:06d}",
                        "market": "CN",
                        "factor_name": "dragon_tiger_net_buy_continuation_1d",
                        "factor_value": size * 10.0 + alpha,
                        "amount": 20_000_000.0 + asset_idx,
                        "adv20_amount": 20_000_000.0 + asset_idx,
                        "log_adv20": size,
                        "pit_lag_trade_days": 1,
                        "source_event_count": 1,
                    }
                )

        repaired = compute_dragon_tiger_size_residual_factor_frame(pd.DataFrame(rows))

        self.assertEqual(set(repaired["factor_name"]), {"dragon_tiger_net_buy_continuation_size_residual_1d"})
        for _, group in repaired.groupby("date"):
            corr = 0.0
            if group["factor_value"].nunique(dropna=True) > 1:
                corr = group["factor_value"].rank(method="average").corr(group["log_adv20"].rank(method="average"))
            self.assertLess(abs(float(corr)), 0.05)

    def test_build_and_writer_keep_promotion_blocked(self) -> None:
        bars = _bars(assets=20, days=18)
        stock_day = _dragon_tiger_stock_day(assets=20, event_dates=pd.bdate_range("2024-01-02", periods=8))
        stock_basic = _stock_basic(assets=20)

        result = build_dragon_tiger_size_residual_repair_prescreen(
            stock_day=stock_day,
            bars=bars,
            stock_basic=stock_basic,
            horizons=(1,),
            execution_lag=0,
            min_cross_section=20,
            min_ic_observations=4,
            min_neutral_ic_t_stat=0.0,
        )

        self.assertEqual(result["stage"], "dragon_tiger_size_residual_repair_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 2)
        self.assertEqual(result["summary"]["factor_names_with_rows"], 2)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])
        self.assertEqual(set(result["summary"]["horizons"]), {1})

        with tempfile.TemporaryDirectory() as tmp:
            write_dragon_tiger_size_residual_repair_prescreen(tmp, result)
            output = Path(tmp)
            self.assertTrue((output / "dragon_tiger_size_residual_repair_prescreen.json").exists())
            self.assertTrue((output / "dragon_tiger_size_residual_repair_prescreen.md").exists())
            self.assertTrue((output / "dragon_tiger_size_residual_repair_results.csv").exists())


def _dragon_tiger_stock_day(assets: int, event_dates: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    for event_date in event_dates:
        for asset_idx in range(assets):
            rows.append(
                {
                    "date": event_date,
                    "available_date": event_date + pd.offsets.BDay(1),
                    "asset_id": f"CN_XSHE_{asset_idx:06d}",
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "source": "fixture",
                    "top_list_event_count": 1.0,
                    "top_list_reason_count": 1.0,
                    "top_list_amount_sum": 100_000_000.0 + asset_idx,
                    "top_list_net_amount_sum": (asset_idx % 10) * 1_000_000.0 + asset_idx * 10_000.0,
                    "top_list_abs_pct_change_max": 3.0 + asset_idx,
                    "top_list_amount_rate_max": 5.0 + asset_idx,
                    "top_inst_event_count": 1.0,
                    "top_inst_reason_count": 1.0,
                    "top_inst_buy_sum": 30_000_000.0 + (asset_idx % 10) * 500_000.0,
                    "top_inst_sell_sum": 20_000_000.0,
                    "top_inst_net_buy_sum": 10_000_000.0 + (asset_idx % 10) * 500_000.0 + asset_idx * 10_000.0,
                    "top_inst_abs_net_buy_sum": 10_000_000.0 + (asset_idx % 10) * 500_000.0,
                }
            )
    return pd.DataFrame(rows)


def _bars(assets: int, days: int) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=days)
    rows = []
    for asset_idx in range(assets):
        price = 10.0 + asset_idx
        for day_idx, date_value in enumerate(dates):
            price += 0.01 + (asset_idx % 5) * 0.001
            rows.append(
                {
                    "date": date_value,
                    "asset_id": f"CN_XSHE_{asset_idx:06d}",
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
