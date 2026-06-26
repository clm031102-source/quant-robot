import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.dynamic_cash_overlay_backtest import (
    run_dynamic_cash_overlay_backtest,
    render_dynamic_cash_overlay_markdown,
    write_dynamic_cash_overlay_backtest,
)


class DynamicCashOverlayBacktestTests(unittest.TestCase):
    def test_dynamic_overlay_reduces_exposure_on_negative_market_state_dates(self):
        factors, labels, bars = _inputs()

        result = run_dynamic_cash_overlay_backtest(
            factors,
            labels,
            bars,
            bottom_quantile=0.2,
            rebalance_interval=1,
            holding_period=1,
            cost_bps=0.0,
            market_impact_bps=0.0,
            portfolio_value=1_000_000.0,
            target_gross_exposure=0.6,
            risk_off_exposure=0.0,
            market_state_lookback=1,
            min_positive_relative_fold_rate=0.5,
            min_overlap_adjusted_sharpe=0.0,
            max_drawdown_limit=0.5,
        )

        self.assertEqual(result["summary"]["cases"], 1)
        self.assertLess(result["summary"]["risk_on_rate"], 1.0)
        self.assertGreater(result["summary"]["risk_on_rate"], 0.0)

        row = result["leaderboard"][0]
        self.assertEqual(row["factor_name"], "tail_filter")
        self.assertGreaterEqual(row["dynamic_total_return"], 0.0)
        self.assertGreater(row["dynamic_max_drawdown"], row["static_max_drawdown"])
        self.assertEqual(row["classification"], "dynamic_cash_overlay_candidate")

    def test_writer_emits_artifacts(self):
        factors, labels, bars = _inputs()
        result = run_dynamic_cash_overlay_backtest(
            factors,
            labels,
            bars,
            bottom_quantile=0.2,
            rebalance_interval=1,
            holding_period=1,
            cost_bps=0.0,
            market_impact_bps=0.0,
            portfolio_value=1_000_000.0,
            target_gross_exposure=0.6,
            risk_off_exposure=0.0,
            market_state_lookback=1,
        )

        markdown = render_dynamic_cash_overlay_markdown(result)

        self.assertIn("Dynamic Cash Overlay Backtest", markdown)
        with tempfile.TemporaryDirectory() as tmp:
            write_dynamic_cash_overlay_backtest(tmp, result)

            self.assertTrue((Path(tmp) / "dynamic_cash_overlay_backtest.json").exists())
            self.assertTrue((Path(tmp) / "dynamic_cash_overlay_backtest.md").exists())
            self.assertTrue((Path(tmp) / "leaderboard.csv").exists())
            self.assertTrue((Path(tmp) / "market_state.csv").exists())


def _inputs():
    dates = pd.date_range("2024-01-02", periods=8, freq="D")
    factor_rows = []
    label_rows = []
    bar_rows = []
    market_prices = [100.0, 110.0, 100.0, 112.0, 102.0, 115.0, 104.0, 118.0]
    for day_index, day in enumerate(dates):
        risk_on_like = day_index % 2 == 1
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
            forward_return = -0.04 if not risk_on_like else 0.03
            if asset_index == 0:
                forward_return = -0.08
            label_rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "horizon": 1,
                    "execution_lag": 1,
                    "forward_return": forward_return,
                    "entry_date": day.date(),
                    "exit_date": day.date(),
                }
            )
            bar_rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": market_prices[day_index],
                    "amount": 1_000_000_000.0,
                }
            )
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), pd.DataFrame(bar_rows)


if __name__ == "__main__":
    unittest.main()
