import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.lpr_macro_regime_state_conditioned_walk_forward_validation import (
    summarize_lpr_macro_regime_state_conditioned_walk_forward_validation,
    write_lpr_macro_regime_state_conditioned_walk_forward_validation,
)


FACTOR = "synthetic_lpr_gap_widening_residual"


class LPRMacroRegimeStateConditionedWalkForwardValidationTests(unittest.TestCase):
    def test_accepts_positive_oos_candidate_after_cost_and_capacity_checks(self) -> None:
        factors, bars, exposure = _frames(test_winner_return=0.03, test_loser_return=-0.01, amount=1_000_000_000.0)

        result = summarize_lpr_macro_regime_state_conditioned_walk_forward_validation(
            _preflight(),
            factors,
            bars,
            _state_frame(),
            exposure_frame=exposure,
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-02-29",
            cost_bps=0.0,
            portfolio_value=100_000.0,
            min_ic_observations=2,
            min_test_positive_ic_rate=0.5,
            min_accepted_folds=2,
            min_selected_assets=1,
            min_regime_allowed_dates=2,
            min_regime_blocked_dates=1,
        )

        self.assertEqual(result["stage"], "lpr_macro_regime_state_conditioned_walk_forward_validation")
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["summary"]["accepted_candidates"], 1)
        self.assertEqual(result["candidate_results"][0]["validation_status"], "accepted")
        self.assertEqual(result["candidate_results"][0]["accepted_folds"], 2)
        self.assertFalse(result["portfolio_grid_policy"]["portfolio_grid_allowed"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["live_boundary_allowed"])
        self.assertTrue(result["candidate_results"][0]["moderate_exposure_challenge_passed"])

    def test_rejects_when_test_long_short_is_negative(self) -> None:
        factors, bars, exposure = _frames(test_winner_return=-0.02, test_loser_return=0.02, amount=1_000_000_000.0)

        result = summarize_lpr_macro_regime_state_conditioned_walk_forward_validation(
            _preflight(),
            factors,
            bars,
            _state_frame(),
            exposure_frame=exposure,
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-02-29",
            cost_bps=0.0,
            portfolio_value=100_000.0,
            min_ic_observations=2,
            min_test_positive_ic_rate=0.5,
            min_accepted_folds=2,
            min_selected_assets=1,
            min_regime_allowed_dates=2,
            min_regime_blocked_dates=1,
        )

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["summary"]["accepted_candidates"], 0)
        self.assertIn("accepted_folds_below_threshold", result["candidate_results"][0]["rejection_reasons"])
        self.assertTrue(
            any("test_long_short_net_mean_non_positive" in row["fold_rejection_reasons"] for row in result["fold_results"])
        )
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])

    def test_blocks_when_preflight_is_not_cleared(self) -> None:
        preflight = _preflight()
        preflight["status"] = "blocked"
        factors, bars, exposure = _frames(test_winner_return=0.03, test_loser_return=-0.01, amount=1_000_000_000.0)

        result = summarize_lpr_macro_regime_state_conditioned_walk_forward_validation(
            preflight,
            factors,
            bars,
            _state_frame(),
            exposure_frame=exposure,
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-02-29",
            min_ic_observations=1,
            min_regime_allowed_dates=1,
            min_regime_blocked_dates=1,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("walk_forward_preflight_not_cleared", result["decision"]["blockers"])
        self.assertFalse(result["decision"]["statistical_reality_check_allowed_next"])

    def test_write_outputs(self) -> None:
        factors, bars, exposure = _frames(test_winner_return=0.03, test_loser_return=-0.01, amount=1_000_000_000.0)
        result = summarize_lpr_macro_regime_state_conditioned_walk_forward_validation(
            _preflight(),
            factors,
            bars,
            _state_frame(),
            exposure_frame=exposure,
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-02-29",
            cost_bps=0.0,
            portfolio_value=100_000.0,
            min_ic_observations=2,
            min_regime_allowed_dates=2,
            min_regime_blocked_dates=1,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_lpr_macro_regime_state_conditioned_walk_forward_validation(output, result)
            self.assertTrue((output / "lpr_macro_regime_state_conditioned_walk_forward_validation.json").exists())
            self.assertTrue((output / "lpr_macro_regime_state_conditioned_walk_forward_validation.md").exists())
            self.assertTrue((output / "lpr_macro_regime_state_conditioned_walk_forward_candidates.csv").exists())
            self.assertTrue((output / "lpr_macro_regime_state_conditioned_walk_forward_folds.csv").exists())
            self.assertTrue((output / "lpr_macro_regime_state_conditioned_regime_coverage.csv").exists())


def _preflight() -> dict:
    return {
        "stage": "lpr_macro_regime_state_conditioned_walk_forward_preflight",
        "status": "cleared",
        "decision": {
            "walk_forward_preflight_cleared": True,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
        },
        "preflight_policy": {
            "walk_forward_preflight_cleared": True,
            "frozen_factor_names": [FACTOR],
        },
        "candidate_table": [
            {
                "factor_name": FACTOR,
                "base_factor_name": "synthetic_lpr_gap_widening",
                "horizon": 1,
                "state": "gap_widening",
                "walk_forward_frozen": True,
                "moderate_exposure_challenge_required": True,
                "challenge_requirements": ["challenge_realized_vol_20_exposure_in_walk_forward"],
                "max_exposure_name": "realized_vol_20",
            }
        ],
        "walk_forward_plan": [
            {
                "fold": 1,
                "train_start": "2024-01-02",
                "train_end": "2024-01-10",
                "test_start": "2024-01-11",
                "test_end": "2024-01-18",
            },
            {
                "fold": 2,
                "train_start": "2024-01-11",
                "train_end": "2024-01-18",
                "test_start": "2024-01-19",
                "test_end": "2024-01-29",
            },
        ],
        "promotion_policy": {"promotion_allowed": False},
        "live_boundary_allowed": False,
    }


def _frames(*, test_winner_return: float, test_loser_return: float, amount: float) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2024-01-02", periods=30)
    assets = ["A", "B", "C", "D", "E", "F"]
    prices = {asset: 10.0 for asset in assets}
    factor_rows = []
    bar_rows = []
    exposure_rows = []
    for index, trade_date in enumerate(dates):
        in_test = trade_date >= pd.Timestamp("2024-01-11")
        for asset_index, asset in enumerate(assets):
            high_signal = asset in {"A", "B", "C"}
            daily_return = test_winner_return if high_signal else test_loser_return
            if not in_test:
                daily_return = 0.02 if high_signal else -0.01
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
            factor_rows.append(
                {
                    "date": trade_date,
                    "asset_id": asset,
                    "market": "CN",
                    "factor_name": FACTOR,
                    "factor_value": 10.0 if high_signal else float(asset_index),
                }
            )
            exposure_rows.append(
                {
                    "date": trade_date,
                    "asset_id": asset,
                    "market": "CN",
                    "realized_vol_20": float(asset_index % 3),
                    "amount": amount,
                    "adv20_amount": amount,
                }
            )
    return pd.DataFrame(factor_rows), pd.DataFrame(bar_rows), pd.DataFrame(exposure_rows)


def _state_frame() -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=30)
    rows = []
    for index, trade_date in enumerate(dates):
        rows.append(
            {
                "available_date": trade_date,
                "lpr_shibor_gap_state": "gap_flat" if index in {4, 14, 24} else "gap_widening",
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
