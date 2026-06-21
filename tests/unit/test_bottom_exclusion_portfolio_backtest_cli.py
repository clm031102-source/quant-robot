import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_bottom_exclusion_portfolio_backtest import run_bottom_exclusion_portfolio_backtest_cli


class BottomExclusionPortfolioBacktestCliTests(unittest.TestCase):
    def test_run_bottom_exclusion_portfolio_backtest_accepts_factor_label_and_bar_files(self):
        factors, labels, bars = _inputs()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            factors_path = root / "factors.csv"
            labels_path = root / "labels.csv"
            bars_path = root / "bars.csv"
            output_dir = root / "backtest"
            factors.to_csv(factors_path, index=False)
            labels.to_csv(labels_path, index=False)
            bars.to_csv(bars_path, index=False)

            result = run_bottom_exclusion_portfolio_backtest_cli(
                factors=factors_path,
                labels=labels_path,
                bars=bars_path,
                output_dir=output_dir,
                bottom_quantile=0.2,
                rebalance_interval=1,
                holding_period=1,
                cost_bps=0.0,
                market_impact_bps=0.0,
                min_positive_relative_fold_rate=0.5,
            )

            self.assertEqual(result["summary"]["cases"], 1)
            self.assertEqual(result["leaderboard"][0]["classification"], "costed_risk_filter_candidate")
            self.assertTrue((output_dir / "bottom_exclusion_portfolio_backtest.json").exists())
            self.assertTrue((output_dir / "leaderboard.csv").exists())


def _inputs():
    factor_rows = []
    label_rows = []
    bar_rows = []
    for day_index, day in enumerate(pd.date_range("2024-01-02", periods=6, freq="D")):
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
                    "forward_return": (-0.05 - 0.001 * day_index)
                    if asset_index == 0
                    else (0.02 + 0.001 * (day_index % 2)),
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
                    "amount": 1_000_000_000.0,
                }
            )
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), pd.DataFrame(bar_rows)


if __name__ == "__main__":
    unittest.main()
