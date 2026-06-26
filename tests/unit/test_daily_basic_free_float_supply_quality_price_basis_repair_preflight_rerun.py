import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun import (
    NEXT_CLEAN_WALK_FORWARD,
    STAGE,
    repair_bars_to_single_price_basis,
    summarize_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun,
)
from quant_robot.ops.daily_basic_free_float_supply_quality_residual_stability_audit import (
    STRICT_RESIDUAL_FACTOR_NAME,
)
from quant_robot.storage.dataset_store import DatasetStore


def _mixed_basis_portfolio_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2025-06-26", periods=8)
    factor_rows = []
    bar_rows = []
    state_rows = []
    for idx, trade_date in enumerate(dates):
        state_rows.append(
            {
                "date": trade_date,
                "trend_state": "neutral",
                "breadth_state": "mixed",
                "volatility_state": "normal_vol",
            }
        )
        for asset_id, base, score in [
            ("CN_XSHE_TEST1", 10.0, 3.0),
            ("CN_XSHE_TEST2", 20.0, 1.0),
        ]:
            close = base + idx * 0.1
            adjusted = trade_date >= pd.Timestamp("2025-07-01") and asset_id == "CN_XSHE_TEST1"
            bar_rows.append(
                {
                    "date": trade_date,
                    "asset_id": asset_id,
                    "symbol": asset_id,
                    "market": "CN",
                    "open": close,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "adj_close": close * 100.0 if adjusted else close,
                    "amount": 100_000_000.0,
                    "volume": 10_000_000.0,
                    "adjusted": adjusted,
                }
            )
            if idx < 5:
                factor_rows.append(
                    {
                        "date": trade_date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": STRICT_RESIDUAL_FACTOR_NAME,
                        "factor_value": score,
                    }
                )
    return pd.DataFrame(factor_rows), pd.DataFrame(bar_rows), pd.DataFrame(state_rows)


class DailyBasicFreeFloatSupplyQualityPriceBasisRepairPreflightRerunTests(unittest.TestCase):
    def test_repair_bars_to_close_basis_replaces_adjusted_close_and_flags_policy(self) -> None:
        _, bars, _ = _mixed_basis_portfolio_frames()

        repaired, summary = repair_bars_to_single_price_basis(bars, price_basis="close")

        self.assertEqual(summary["price_basis"], "close")
        self.assertEqual(summary["bar_rows"], len(bars))
        self.assertGreater(summary["repriced_bar_rows"], 0)
        self.assertTrue((repaired["adj_close"] == repaired["close"]).all())
        self.assertFalse(repaired["adjusted"].any())
        self.assertIn("original_adj_close", repaired.columns)
        self.assertIn("original_adjusted", repaired.columns)

    def test_repaired_rerun_removes_mixed_basis_phantom_alpha_without_changing_parameters(self) -> None:
        factors, bars, market_state = _mixed_basis_portfolio_frames()

        result = summarize_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun(
            factors,
            bars,
            market_state_frame=market_state,
            guard_modes=("none",),
            cost_bps_values=(10.0,),
            portfolio_values=(100_000.0,),
            top_n=1,
            holding_period=2,
            rebalance_interval=1,
            min_signal_amount=0.0,
            max_participation_rate=0.01,
            market_impact_bps=0.0,
            max_calendar_holding_days=10,
            min_overlap_adjusted_sharpe=-10.0,
            min_oos_overlap_adjusted_sharpe=-10.0,
            max_drawdown_floor=-1.0,
            train_end_date="2025-06-30",
            test_start_date="2025-07-01",
        )

        self.assertEqual(result["stage"], STAGE)
        self.assertTrue(result["price_basis_repair_policy"]["same_frozen_parameters_as_round136"])
        self.assertEqual(result["price_basis_repair_summary"]["price_basis"], "close")
        self.assertEqual(result["repaired_extreme_trade_audit"]["summary"]["phantom_alpha_trade_count"], 0)
        self.assertLess(result["summary"]["max_abs_trade_gross_return"], 1.0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertEqual(result["next_direction"], NEXT_CLEAN_WALK_FORWARD)


if __name__ == "__main__":
    unittest.main()
