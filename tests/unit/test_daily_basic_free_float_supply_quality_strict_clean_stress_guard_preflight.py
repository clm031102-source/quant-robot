import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.daily_basic_free_float_supply_quality_residual_stability_audit import (
    STRICT_RESIDUAL_FACTOR_NAME,
)
from quant_robot.ops.daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight import (
    DEFAULT_LEAD_FACTOR_NAME,
    NEXT_EXTREME_TRADE_AUDIT,
    STAGE,
    apply_stress_guard_to_factor_frame,
    build_daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight,
    summarize_daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight,
)
from quant_robot.storage.dataset_store import DatasetStore
from tests.unit.test_daily_basic_non_price_public_carry_prescreen import (
    _synthetic_bars,
    _synthetic_daily_basic,
)


def _portfolio_frames(*, amount: float = 100_000_000.0) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2025-01-02", periods=26)
    factor_rows = []
    bar_rows = []
    market_rows = []
    prices = {"A": 10.0, "B": 10.0, "C": 10.0}
    returns = {
        "A": [
            0.000,
            0.012,
            0.010,
            0.011,
            0.009,
            0.010,
            0.012,
            0.011,
            0.010,
            0.009,
            0.012,
            0.010,
            0.011,
            0.009,
            0.010,
            0.012,
            0.011,
            0.010,
            0.009,
            0.012,
            0.010,
            0.011,
            0.009,
            0.010,
            0.012,
            0.010,
        ],
        "B": [
            0.000,
            -0.001,
            0.001,
            -0.001,
            0.001,
            -0.001,
            0.001,
            -0.001,
            0.001,
            -0.001,
            0.001,
            -0.001,
            0.001,
            -0.001,
            0.001,
            -0.001,
            0.001,
            -0.001,
            0.001,
            -0.001,
            0.001,
            -0.001,
            0.001,
            -0.001,
            0.001,
            0.000,
        ],
        "C": [
            0.000,
            -0.002,
            -0.001,
            -0.002,
            -0.001,
            -0.002,
            -0.001,
            -0.002,
            -0.001,
            -0.002,
            -0.001,
            -0.002,
            -0.001,
            -0.002,
            -0.001,
            -0.002,
            -0.001,
            -0.002,
            -0.001,
            -0.002,
            -0.001,
            -0.002,
            -0.001,
            -0.002,
            -0.001,
            0.000,
        ],
    }
    stress_dates = {dates[0], dates[4], dates[8]}
    for day_idx, trade_date in enumerate(dates):
        market_rows.append(
            {
                "date": trade_date,
                "trend_state": "stress" if trade_date in stress_dates else "neutral",
                "breadth_state": "weak" if trade_date in stress_dates else "mixed",
                "volatility_state": "high_vol" if trade_date in stress_dates else "normal_vol",
            }
        )
        for asset_id in ["A", "B", "C"]:
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
        if day_idx < 20:
            for asset_id, score in [("A", 3.0), ("B", 1.0), ("C", 0.0)]:
                factor_rows.append(
                    {
                        "date": trade_date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": STRICT_RESIDUAL_FACTOR_NAME,
                        "factor_value": score,
                    }
                )
    return pd.DataFrame(factor_rows), pd.DataFrame(bar_rows), pd.DataFrame(market_rows)


class DailyBasicFreeFloatSupplyQualityStrictCleanStressGuardPreflightTests(unittest.TestCase):
    def test_stress_guard_removes_stress_dates_and_never_promotes(self) -> None:
        factors, bars, market_state = _portfolio_frames()

        guarded = apply_stress_guard_to_factor_frame(
            factors,
            market_state,
            guard_mode="block_stress_rebalance_dates",
        )
        self.assertLess(guarded["date"].nunique(), factors["date"].nunique())
        self.assertFalse(
            set(pd.to_datetime(guarded["date"]).dt.date).intersection(
                set(pd.to_datetime(market_state[market_state["trend_state"] == "stress"]["date"]).dt.date)
            )
        )

        result = summarize_daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight(
            factors,
            bars,
            market_state_frame=market_state,
            cost_bps_values=(0.0, 20.0),
            portfolio_values=(100_000.0,),
            top_n=1,
            holding_period=2,
            rebalance_interval=2,
            min_signal_amount=0.0,
            max_participation_rate=0.01,
            market_impact_bps=0.0,
            max_calendar_holding_days=10,
            min_overlap_adjusted_sharpe=-10.0,
            min_oos_overlap_adjusted_sharpe=-10.0,
            train_end_date="2025-01-20",
            test_start_date="2025-01-21",
        )

        self.assertEqual(result["stage"], STAGE)
        self.assertEqual(result["summary"]["case_count"], 4)
        self.assertEqual(result["summary"]["guard_mode_count"], 2)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        rows = {(row["guard_mode"], row["cost_bps"]): row for row in result["leaderboard"]}
        self.assertLess(
            rows[("block_stress_rebalance_dates", 0.0)]["guarded_signal_rows"],
            rows[("none", 0.0)]["guarded_signal_rows"],
        )
        self.assertIn("test_overlap_autocorr_adjusted_sharpe", rows[("none", 20.0)])
        self.assertIn("train_overlap_autocorr_adjusted_sharpe", rows[("none", 20.0)])
        self.assertIn("stress_guard_mode", result["thresholds"])

    def test_capacity_limited_trades_block_walk_forward_candidate_even_when_return_positive(self) -> None:
        factors, bars, market_state = _portfolio_frames(amount=1_000_000.0)

        result = summarize_daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight(
            factors,
            bars,
            market_state_frame=market_state,
            cost_bps_values=(0.0,),
            portfolio_values=(100_000.0,),
            top_n=1,
            holding_period=2,
            rebalance_interval=2,
            min_signal_amount=0.0,
            max_participation_rate=0.01,
            market_impact_bps=0.0,
            max_calendar_holding_days=10,
            min_overlap_adjusted_sharpe=-10.0,
            min_oos_overlap_adjusted_sharpe=-10.0,
            train_end_date="2025-01-20",
            test_start_date="2025-01-21",
        )

        row = result["leaderboard"][0]
        self.assertGreater(row["total_return"], 0.0)
        self.assertGreater(row["capacity_limited_trades"], 0)
        self.assertTrue(row["hard_blocked"])
        self.assertIn("capacity_limited_trades_present", row["blockers"])
        self.assertEqual(result["portfolio_preflight_policy"]["walk_forward_allowed_candidates"], 0)

    def test_only_extreme_trade_blockers_route_to_extreme_trade_audit_not_hibernation(self) -> None:
        factors, bars, market_state = _portfolio_frames()
        bars = bars.copy()
        mask = (bars["asset_id"] == "A") & (bars["date"] >= pd.Timestamp("2025-01-10"))
        bars.loc[mask, "adj_close"] = pd.to_numeric(bars.loc[mask, "adj_close"]) * 2.0

        result = summarize_daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight(
            factors,
            bars,
            market_state_frame=market_state,
            guard_modes=("none",),
            cost_bps_values=(10.0,),
            portfolio_values=(100_000.0,),
            top_n=1,
            holding_period=2,
            rebalance_interval=2,
            min_signal_amount=0.0,
            max_participation_rate=0.01,
            market_impact_bps=0.0,
            max_calendar_holding_days=10,
            min_overlap_adjusted_sharpe=-10.0,
            min_oos_overlap_adjusted_sharpe=-10.0,
            max_drawdown_floor=-1.0,
            train_end_date="2025-01-08",
            test_start_date="2025-01-09",
        )

        self.assertEqual(result["next_direction"], NEXT_EXTREME_TRADE_AUDIT)
        self.assertEqual(result["portfolio_preflight_policy"]["walk_forward_allowed_candidates"], 0)
        self.assertIn("extreme_trade_return_present", result["leaderboard"][0]["blockers"])
        self.assertGreater(result["extreme_trade_diagnostic"]["extreme_trade_count"], 0)

    def test_build_excludes_final_holdout_and_uses_strict_clean_residual(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            output_daily_basic = Path(tmp) / "daily_basic"
            bars = _synthetic_bars(days=80, assets=40, include_holdout=True)
            daily_basic = _synthetic_daily_basic(days=80, assets=40, include_holdout=True)
            bars_store = DatasetStore(root)
            daily_basic_store = DatasetStore(output_daily_basic)
            for year in [2025, 2026]:
                bars_store.write_frame(
                    bars[bars["date"].dt.year == year],
                    "bars",
                    {"frequency": "1d", "market": "CN", "year": str(year)},
                )
                daily_basic_store.write_frame(
                    daily_basic[daily_basic["date"].dt.year == year],
                    "processed/factor_inputs",
                    {"frequency": "1d", "market": "CN", "year": str(year)},
                )

            result = build_daily_basic_free_float_supply_quality_strict_clean_stress_guard_preflight(
                bars_roots=[root],
                daily_basic_roots=[output_daily_basic],
                analysis_end_date="2025-12-31",
                include_final_holdout=False,
                cost_bps_values=(0.0,),
                portfolio_values=(100_000.0,),
                top_n=5,
                holding_period=5,
                rebalance_interval=5,
                min_cross_section=20,
                min_signal_amount=0.0,
                min_signal_date_amount=10_000_000,
                max_calendar_holding_days=15,
                min_overlap_adjusted_sharpe=-10.0,
                min_oos_overlap_adjusted_sharpe=-10.0,
                train_end_date="2025-02-28",
                test_start_date="2025-03-03",
            )

        self.assertEqual(result["lead_factor_name"], DEFAULT_LEAD_FACTOR_NAME)
        self.assertEqual(result["summary"]["factor_names"], [STRICT_RESIDUAL_FACTOR_NAME])
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertLessEqual(result["data_window"]["max_signal_date"], "2025-12-31")
        self.assertGreater(result["data_window"]["strict_clean_residual_rows"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
