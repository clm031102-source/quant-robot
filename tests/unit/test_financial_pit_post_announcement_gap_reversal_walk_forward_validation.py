import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.financial_pit_post_announcement_gap_reversal_walk_forward_validation import (
    run_financial_pit_post_announcement_gap_reversal_walk_forward_validation_from_frames,
    write_financial_pit_post_announcement_gap_reversal_walk_forward_validation,
)


FACTOR = "pead_gap_overreaction_reversal_low_liquidity_penalized_1_5"


class FinancialPitPostAnnouncementGapReversalWalkForwardValidationTests(unittest.TestCase):
    def test_walk_forward_validation_accepts_positive_cost_capacity_clean_case(self) -> None:
        factors, bars = _frames(amount=1_000_000_000.0, winner_return=0.02, loser_return=-0.01)

        result = run_financial_pit_post_announcement_gap_reversal_walk_forward_validation_from_frames(
            factor_frame=factors,
            bars=bars,
            preflight=_preflight(),
            top_n_values=(1,),
            cost_bps_values=(0.0,),
            portfolio_values=(100_000.0,),
            rebalance_intervals=(1,),
            min_test_overlap_adjusted_sharpe=-10.0,
            min_accepted_folds=2,
            min_test_trades=1,
            min_regime_states=1,
        )

        self.assertEqual(result["stage"], "financial_pit_post_announcement_gap_reversal_walk_forward_cost_capacity_regime_validation")
        self.assertEqual(result["summary"]["cases"], 1)
        self.assertEqual(result["leaderboard"][0]["validation_status"], "accepted")
        self.assertEqual(result["leaderboard"][0]["accepted_folds"], 2)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])

    def test_capacity_limited_test_trades_reject_case(self) -> None:
        factors, bars = _frames(amount=1_000.0, winner_return=0.02, loser_return=-0.01)

        result = run_financial_pit_post_announcement_gap_reversal_walk_forward_validation_from_frames(
            factor_frame=factors,
            bars=bars,
            preflight=_preflight(),
            top_n_values=(1,),
            cost_bps_values=(0.0,),
            portfolio_values=(1_000_000.0,),
            rebalance_intervals=(1,),
            min_test_overlap_adjusted_sharpe=-10.0,
            min_accepted_folds=2,
            min_test_trades=1,
            min_signal_amount=0.0,
            min_regime_states=1,
        )

        row = result["leaderboard"][0]
        self.assertEqual(row["validation_status"], "rejected")
        self.assertIn("test_capacity_limited_trades_present", row["rejection_reasons"])
        self.assertGreater(row["test_capacity_limited_trades"], 0)

    def test_write_outputs(self) -> None:
        factors, bars = _frames(amount=1_000_000_000.0, winner_return=0.02, loser_return=-0.01)
        result = run_financial_pit_post_announcement_gap_reversal_walk_forward_validation_from_frames(
            factor_frame=factors,
            bars=bars,
            preflight=_preflight(),
            top_n_values=(1,),
            cost_bps_values=(0.0,),
            portfolio_values=(100_000.0,),
            rebalance_intervals=(1,),
            min_test_overlap_adjusted_sharpe=-10.0,
            min_accepted_folds=2,
            min_test_trades=1,
            min_regime_states=1,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_financial_pit_post_announcement_gap_reversal_walk_forward_validation(output, result)
            self.assertTrue((output / "financial_pit_post_announcement_gap_reversal_walk_forward_validation.json").exists())
            self.assertTrue((output / "financial_pit_post_announcement_gap_reversal_walk_forward_validation.md").exists())
            self.assertTrue((output / "walk_forward_leaderboard.csv").exists())
            self.assertTrue((output / "walk_forward_folds.csv").exists())
            self.assertTrue((output / "walk_forward_regime_coverage.csv").exists())


def _frames(*, amount: float, winner_return: float, loser_return: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2020-01-02", periods=36)
    assets = ["A", "B", "C", "D"]
    prices = {asset: 10.0 for asset in assets}
    factor_rows = []
    bar_rows = []
    for index, trade_date in enumerate(dates):
        for asset in assets:
            daily_return = winner_return if asset == "A" else loser_return
            prices[asset] *= 1.0 + daily_return
            bar_rows.append(
                {
                    "date": trade_date,
                    "asset_id": asset,
                    "market": "CN",
                    "adj_close": prices[asset],
                    "amount": amount,
                }
            )
            if index < len(dates) - 3:
                factor_rows.append(
                    {
                        "date": trade_date,
                        "asset_id": asset,
                        "market": "CN",
                        "factor_name": FACTOR,
                        "factor_value": 10.0 if asset == "A" else float(assets.index(asset)),
                    }
                )
    return pd.DataFrame(factor_rows), pd.DataFrame(bar_rows)


def _preflight() -> dict:
    return {
        "status": "cleared",
        "preflight_policy": {
            "walk_forward_preflight_cleared": True,
            "frozen_factor_names": [FACTOR],
        },
        "walk_forward_plan": [
            {
                "fold": "fold_1",
                "train_start": "2020-01-02",
                "train_end": "2020-01-17",
                "test_start": "2020-01-20",
                "test_end": "2020-01-29",
                "purpose": "synthetic",
            },
            {
                "fold": "fold_2",
                "train_start": "2020-01-02",
                "train_end": "2020-01-29",
                "test_start": "2020-01-30",
                "test_end": "2020-02-10",
                "purpose": "synthetic",
            },
        ],
        "promotion_policy": {"promotion_allowed": False},
    }


if __name__ == "__main__":
    unittest.main()
