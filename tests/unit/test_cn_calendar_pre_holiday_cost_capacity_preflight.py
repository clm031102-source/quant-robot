import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.cn_calendar_pre_holiday_cost_capacity_preflight import (
    DEFAULT_FACTOR_NAME,
    build_cn_calendar_pre_holiday_cost_capacity_preflight,
    summarize_cn_calendar_pre_holiday_cost_capacity_preflight,
    write_cn_calendar_pre_holiday_cost_capacity_preflight,
)
from tests.unit.test_cn_calendar_seasonality_residual_prescreen import _calendar_bars, _stock_basic


def _portfolio_frames(*, amount: float = 100_000_000.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2025-01-02", periods=28)
    factor_rows = []
    bar_rows = []
    prices = {"A": 10.0, "B": 10.0, "C": 10.0, "D": 10.0}
    returns = {
        "A": [0.000, 0.012, 0.018, -0.004, 0.014, 0.010, -0.002, 0.013, 0.006, 0.011, 0.004, 0.012, 0.005, 0.010, 0.004, 0.008, 0.004, 0.006, 0.004, 0.005, 0.003, 0.004, 0.003, 0.004, 0.002, 0.003, 0.002, 0.002],
        "B": [0.000, 0.003, 0.002, 0.001, 0.002, 0.001, 0.002, 0.001, 0.002, 0.001, 0.002, 0.001, 0.002, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001],
        "C": [0.000, -0.002, 0.001, -0.001, 0.001, -0.001, 0.001, -0.001, 0.001, -0.001, 0.001, -0.001, 0.001, -0.001, 0.001, -0.001, 0.001, -0.001, 0.001, -0.001, 0.001, -0.001, 0.001, -0.001, 0.001, -0.001, 0.001, -0.001],
        "D": [0.000, -0.003, -0.002, -0.001, -0.002, -0.001, -0.002, -0.001, -0.002, -0.001, -0.002, -0.001, -0.002, -0.001, -0.001, -0.001, -0.001, -0.001, -0.001, -0.001, -0.001, -0.001, -0.001, -0.001, -0.001, -0.001, -0.001, -0.001],
    }
    for day_idx, trade_date in enumerate(dates):
        for asset_id in ["A", "B", "C", "D"]:
            prices[asset_id] *= 1.0 + returns[asset_id][day_idx]
            bar_rows.append(
                {
                    "date": trade_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": prices[asset_id],
                    "amount": amount,
                }
            )
        if day_idx < 22:
            for asset_id, score in [("A", 4.0), ("B", 2.0), ("C", 1.0), ("D", 0.0)]:
                factor_rows.append(
                    {
                        "date": trade_date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": DEFAULT_FACTOR_NAME,
                        "factor_value": score,
                    }
                )
    return pd.DataFrame(factor_rows), pd.DataFrame(bar_rows)


class CNCalendarPreHolidayCostCapacityPreflightTests(unittest.TestCase):
    def test_cost_capacity_preflight_stresses_single_lead_and_never_promotes(self) -> None:
        factors, bars = _portfolio_frames()

        result = summarize_cn_calendar_pre_holiday_cost_capacity_preflight(
            factors,
            bars,
            cost_bps_values=(0.0, 50.0),
            portfolio_values=(100_000.0,),
            top_n=1,
            holding_period=2,
            rebalance_interval=2,
            min_signal_amount=0.0,
            market_impact_bps=0.0,
            min_overlap_adjusted_sharpe=0.0,
            max_drawdown_floor=-0.40,
        )

        self.assertEqual(result["stage"], "cn_calendar_pre_holiday_cost_capacity_preflight")
        self.assertEqual(result["thresholds"]["factor_name"], DEFAULT_FACTOR_NAME)
        self.assertEqual(result["summary"]["case_count"], 2)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        free = next(row for row in result["leaderboard"] if row["cost_bps"] == 0.0)
        costly = next(row for row in result["leaderboard"] if row["cost_bps"] == 50.0)
        self.assertLess(costly["total_return"], free["total_return"])
        self.assertFalse(free["hard_blocked"])

    def test_capacity_limited_trades_block_walk_forward(self) -> None:
        factors, bars = _portfolio_frames(amount=1_000_000.0)

        result = summarize_cn_calendar_pre_holiday_cost_capacity_preflight(
            factors,
            bars,
            cost_bps_values=(0.0,),
            portfolio_values=(100_000.0,),
            top_n=1,
            holding_period=2,
            rebalance_interval=2,
            min_signal_amount=0.0,
            market_impact_bps=0.0,
            min_overlap_adjusted_sharpe=0.0,
            max_drawdown_floor=-0.40,
        )

        row = result["leaderboard"][0]
        self.assertGreater(row["capacity_limited_trades"], 0)
        self.assertTrue(row["hard_blocked"])
        self.assertIn("capacity_limited_trades_present", row["blockers"])
        self.assertEqual(result["portfolio_preflight_policy"]["walk_forward_allowed_candidates"], 0)

    def test_build_generates_residual_lead_from_calendar_bars_without_final_holdout(self) -> None:
        result = build_cn_calendar_pre_holiday_cost_capacity_preflight(
            bars=_calendar_bars(days=130, assets=30),
            stock_basic=_stock_basic(30),
            include_final_holdout=False,
            cost_bps_values=(0.0,),
            portfolio_values=(100_000.0,),
            top_n=5,
            holding_period=5,
            rebalance_interval=1,
            min_signal_amount=0.0,
            min_signal_date_amount=0.0,
            min_cross_section=15,
            min_industries=2,
            min_assets_per_industry=2,
            min_overlap_adjusted_sharpe=-10.0,
        )

        self.assertEqual(result["summary"]["factor_names"], [DEFAULT_FACTOR_NAME])
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertGreater(result["data_window"]["factor_rows"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])

    def test_write_outputs(self) -> None:
        factors, bars = _portfolio_frames()
        result = summarize_cn_calendar_pre_holiday_cost_capacity_preflight(
            factors,
            bars,
            cost_bps_values=(0.0,),
            portfolio_values=(100_000.0,),
            top_n=1,
            holding_period=2,
            rebalance_interval=2,
            min_signal_amount=0.0,
            min_overlap_adjusted_sharpe=-10.0,
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_cn_calendar_pre_holiday_cost_capacity_preflight(output, result)
            self.assertTrue((output / "cn_calendar_pre_holiday_cost_capacity_preflight.json").exists())
            self.assertTrue((output / "cn_calendar_pre_holiday_cost_capacity_preflight.md").exists())
            self.assertTrue((output / "cn_calendar_pre_holiday_cost_capacity_preflight_leaderboard.csv").exists())


if __name__ == "__main__":
    unittest.main()
