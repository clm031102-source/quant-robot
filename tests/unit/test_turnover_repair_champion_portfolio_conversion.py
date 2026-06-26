import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.ops.turnover_repair_champion_portfolio_conversion import (
    DEFAULT_CHAMPION_FACTOR_NAME,
    build_turnover_repair_champion_portfolio_conversion,
    summarize_turnover_repair_champion_portfolio_conversion,
)
from tests.unit.test_turnover_continuous_capacity_repair_prescreen import (
    _synthetic_bars_and_daily_basic,
)


def _costed_conversion_frames(*, amount: float = 100_000_000.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2025-01-02", periods=18)
    factor_rows = []
    bar_rows = []
    prices = {"A": 10.0, "B": 10.0, "C": 10.0}
    returns = {
        "A": [0.00, 0.010, 0.025, -0.006, 0.018, 0.012, -0.004, 0.020, 0.006, 0.014, -0.005, 0.016, 0.008, 0.012, -0.003, 0.010, 0.006, 0.004],
        "B": [0.00, 0.002, -0.001, 0.001, 0.000, 0.002, -0.001, 0.001, 0.000, 0.001, -0.001, 0.001, 0.000, 0.001, 0.000, 0.001, 0.000, 0.001],
        "C": [0.00, -0.001, 0.001, 0.000, 0.001, -0.001, 0.001, 0.000, 0.001, -0.001, 0.001, 0.000, 0.001, -0.001, 0.001, 0.000, 0.001, 0.000],
    }
    for day_idx, trade_date in enumerate(dates):
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
        if day_idx < 12:
            for asset_id, score in [("A", 3.0), ("B", 1.0), ("C", 0.0)]:
                factor_rows.append(
                    {
                        "date": trade_date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": DEFAULT_CHAMPION_FACTOR_NAME,
                        "factor_value": score,
                    }
                )
    return pd.DataFrame(factor_rows), pd.DataFrame(bar_rows)


class TurnoverRepairChampionPortfolioConversionTests(unittest.TestCase):
    def test_costed_conversion_runs_single_champion_and_never_promotes(self) -> None:
        factors, bars = _costed_conversion_frames()

        result = summarize_turnover_repair_champion_portfolio_conversion(
            factors,
            bars,
            cost_bps_values=(0.0, 50.0),
            portfolio_values=(100_000.0,),
            top_n=1,
            holding_period=2,
            rebalance_interval=2,
            max_participation_rate=0.01,
            min_signal_amount=0.0,
            market_impact_bps=0.0,
            min_overlap_adjusted_sharpe=0.0,
            max_drawdown_floor=-0.40,
        )

        self.assertEqual(result["stage"], "turnover_repair_champion_portfolio_conversion")
        self.assertEqual(result["summary"]["case_count"], 2)
        self.assertEqual({row["factor_name"] for row in result["leaderboard"]}, {DEFAULT_CHAMPION_FACTOR_NAME})
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertEqual(result["thresholds"]["periods_per_year"], 126.0)
        free = next(row for row in result["leaderboard"] if row["cost_bps"] == 0.0)
        costly = next(row for row in result["leaderboard"] if row["cost_bps"] == 50.0)
        self.assertLess(costly["total_return"], free["total_return"])
        self.assertGreater(free["trades"], 0)
        self.assertEqual(free["capacity_limited_trades"], 0)
        self.assertFalse(free["hard_blocked"])

    def test_capacity_limited_trades_block_walk_forward_even_when_return_is_positive(self) -> None:
        factors, bars = _costed_conversion_frames(amount=1_000_000.0)

        result = summarize_turnover_repair_champion_portfolio_conversion(
            factors,
            bars,
            cost_bps_values=(0.0,),
            portfolio_values=(100_000.0,),
            top_n=1,
            holding_period=2,
            rebalance_interval=2,
            max_participation_rate=0.01,
            min_signal_amount=0.0,
            market_impact_bps=0.0,
            min_overlap_adjusted_sharpe=0.0,
            max_drawdown_floor=-0.40,
        )

        row = result["leaderboard"][0]
        self.assertGreater(row["total_return"], 0.0)
        self.assertGreater(row["capacity_limited_trades"], 0)
        self.assertTrue(row["hard_blocked"])
        self.assertIn("capacity_limited_trades_present", row["blockers"])
        self.assertEqual(result["portfolio_conversion_policy"]["walk_forward_allowed_candidates"], 0)

    def test_costed_conversion_applies_tradeability_masks_to_portfolio_execution(self) -> None:
        factors, bars = _costed_conversion_frames()
        sorted_dates = sorted(pd.to_datetime(bars["date"]).dt.date.unique())
        blocked_entry_date = sorted_dates[1]
        tradeability = bars[["date", "asset_id", "market"]].copy()
        tradeability["date"] = pd.to_datetime(tradeability["date"]).dt.date
        tradeability["entry_tradeable"] = True
        tradeability["exit_tradeable"] = True
        tradeability.loc[
            (tradeability["asset_id"] == "A") & (tradeability["date"] == blocked_entry_date),
            "entry_tradeable",
        ] = False

        result = summarize_turnover_repair_champion_portfolio_conversion(
            factors,
            bars,
            tradeability_frame=tradeability,
            cost_bps_values=(10.0,),
            portfolio_values=(100_000.0,),
            top_n=1,
            holding_period=2,
            rebalance_interval=2,
            max_participation_rate=0.01,
            min_signal_amount=0.0,
            market_impact_bps=0.0,
            min_overlap_adjusted_sharpe=-10.0,
            max_drawdown_floor=-0.40,
        )

        row = result["leaderboard"][0]
        self.assertEqual(row["trades_filtered_entry_tradeability"], 1)
        self.assertEqual(row["tradeability_filtered_trades"], 1)
        self.assertEqual(result["summary"]["max_tradeability_filtered_trades"], 1)

    def test_build_generates_champion_from_turnover_repair_inputs_without_final_holdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            factor_root = Path(tmp) / "daily_basic"
            bars, daily_basic = _synthetic_bars_and_daily_basic(days=80, assets=20, include_holdout=True)
            store = DatasetStore(root)
            input_store = DatasetStore(factor_root)
            for year in [2025, 2026]:
                year_bars = bars[bars["date"].dt.year == year]
                year_inputs = daily_basic[daily_basic["date"].dt.year == year]
                store.write_frame(year_bars, "bars", {"frequency": "1d", "market": "CN", "year": str(year)})
                input_store.write_frame(
                    year_inputs,
                    "processed/factor_inputs",
                    {"frequency": "1d", "market": "CN", "year": str(year)},
                )

            result = build_turnover_repair_champion_portfolio_conversion(
                bars_roots=[root],
                factor_input_root=factor_root,
                analysis_end_date="2025-12-31",
                include_final_holdout=False,
                cost_bps_values=(0.0,),
                portfolio_values=(100_000.0,),
                top_n=5,
                holding_period=5,
                rebalance_interval=5,
                min_signal_amount=0.0,
                min_signal_date_amount=10_000_000,
                max_calendar_holding_days=15,
                min_overlap_adjusted_sharpe=-10.0,
            )

            self.assertEqual(result["summary"]["factor_names"], [DEFAULT_CHAMPION_FACTOR_NAME])
            self.assertFalse(result["holdout_policy"]["final_holdout_included"])
            self.assertLessEqual(result["data_window"]["max_signal_date"], "2025-12-31")
            self.assertEqual(result["summary"]["case_count"], 1)
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
