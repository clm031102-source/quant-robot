import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.bottom_exclusion_walk_forward import (
    run_bottom_exclusion_walk_forward,
    write_bottom_exclusion_walk_forward,
)
from scripts.run_bottom_exclusion_walk_forward import run_bottom_exclusion_walk_forward_cli


class BottomExclusionWalkForwardTests(unittest.TestCase):
    def test_rolling_walk_forward_keeps_train_and_test_dates_strictly_separated(self):
        factors, labels, bars = _inputs(bottom_return=-0.05, kept_return=0.02, amount=1_000_000_000.0)

        result = run_bottom_exclusion_walk_forward(
            factors,
            labels,
            bars,
            rolling_train_days=5,
            rolling_test_days=3,
            rolling_step_days=3,
            bottom_quantile=0.2,
            rebalance_interval=1,
            holding_period=1,
            cost_bps=0.0,
            market_impact_bps=0.0,
            portfolio_value=1_000_000.0,
            min_accepted_folds=2,
            min_test_overlap_adjusted_sharpe=0.0,
            max_test_drawdown_limit=0.5,
        )

        self.assertEqual(result["summary"]["cases"], 1)
        self.assertGreaterEqual(result["summary"]["folds"], 2)
        row = result["leaderboard"][0]
        self.assertEqual(row["validation_status"], "accepted")
        self.assertGreaterEqual(row["accepted_folds"], 2)
        self.assertEqual(row["strict_split_status"], "pass")
        self.assertEqual(row["strict_split_violations"], 0)
        self.assertTrue(all(pd.to_datetime(fold["test_start_date"]) > pd.to_datetime(fold["train_end_date"]) for fold in result["folds"]))

    def test_rolling_walk_forward_rejects_when_test_folds_do_not_clear_gate(self):
        factors, labels, bars = _inputs(bottom_return=0.05, kept_return=-0.02, amount=1_000_000_000.0)

        result = run_bottom_exclusion_walk_forward(
            factors,
            labels,
            bars,
            rolling_train_days=5,
            rolling_test_days=3,
            rolling_step_days=3,
            bottom_quantile=0.2,
            rebalance_interval=1,
            holding_period=1,
            cost_bps=0.0,
            market_impact_bps=0.0,
            portfolio_value=1_000_000.0,
            min_accepted_folds=2,
            min_test_overlap_adjusted_sharpe=0.0,
            max_test_drawdown_limit=0.5,
        )

        row = result["leaderboard"][0]
        self.assertEqual(row["validation_status"], "rejected")
        self.assertIn("accepted_folds_below_min", row["rejection_reasons"])

    def test_write_bottom_exclusion_walk_forward_artifacts(self):
        factors, labels, bars = _inputs(bottom_return=-0.05, kept_return=0.02, amount=1_000_000_000.0)
        result = run_bottom_exclusion_walk_forward(
            factors,
            labels,
            bars,
            rolling_train_days=5,
            rolling_test_days=3,
            rolling_step_days=3,
            bottom_quantile=0.2,
            rebalance_interval=1,
            holding_period=1,
            cost_bps=0.0,
            market_impact_bps=0.0,
            min_accepted_folds=2,
            min_test_overlap_adjusted_sharpe=0.0,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_bottom_exclusion_walk_forward(output_dir, result)

            self.assertTrue((output_dir / "bottom_exclusion_walk_forward.json").exists())
            self.assertTrue((output_dir / "bottom_exclusion_walk_forward.md").exists())
            self.assertTrue((output_dir / "walk_forward_leaderboard.csv").exists())
            self.assertTrue((output_dir / "walk_forward_folds.csv").exists())

    def test_cli_accepts_factor_label_and_bar_files(self):
        factors, labels, bars = _inputs(bottom_return=-0.05, kept_return=0.02, amount=1_000_000_000.0)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            factors_path = root / "factors.csv"
            labels_path = root / "labels.csv"
            bars_path = root / "bars.csv"
            output_dir = root / "walk_forward"
            factors.to_csv(factors_path, index=False)
            labels.to_csv(labels_path, index=False)
            bars.to_csv(bars_path, index=False)

            result = run_bottom_exclusion_walk_forward_cli(
                factors=factors_path,
                labels=labels_path,
                bars=bars_path,
                output_dir=output_dir,
                rolling_train_days=5,
                rolling_test_days=3,
                rolling_step_days=3,
                bottom_quantile=0.2,
                rebalance_interval=1,
                holding_period=1,
                cost_bps=0.0,
                market_impact_bps=0.0,
                min_accepted_folds=2,
                min_test_overlap_adjusted_sharpe=0.0,
            )

            self.assertEqual(result["summary"]["cases"], 1)
            self.assertEqual(result["leaderboard"][0]["validation_status"], "accepted")
            self.assertTrue((output_dir / "bottom_exclusion_walk_forward.json").exists())


def _inputs(*, bottom_return: float, kept_return: float, amount: float):
    factor_rows = []
    label_rows = []
    bar_rows = []
    dates = pd.date_range("2024-01-02", periods=14, freq="D")
    for day_index, day in enumerate(dates):
        for asset_index in range(5):
            asset_id = f"asset_{asset_index}"
            factor_rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "tail_filter",
                    "factor_value": float(asset_index + 1),
                }
            )
            label_rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "horizon": 1,
                    "execution_lag": 1,
                    "forward_return": (bottom_return - 0.001 * (day_index % 3))
                    if asset_index == 0
                    else (kept_return + 0.001 * (day_index % 2)),
                    "entry_date": day.date(),
                    "exit_date": day.date(),
                }
            )
            bar_rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": 10.0,
                    "amount": amount,
                }
            )
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), pd.DataFrame(bar_rows)


if __name__ == "__main__":
    unittest.main()
