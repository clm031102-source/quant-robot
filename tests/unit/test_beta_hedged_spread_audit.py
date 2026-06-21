import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.beta_hedged_spread_audit import (
    render_beta_hedged_spread_markdown,
    run_beta_hedged_spread_audit,
    write_beta_hedged_spread_audit,
)


class BetaHedgedSpreadAuditTests(unittest.TestCase):
    def test_spread_audit_scores_kept_basket_against_equal_weight_benchmark(self):
        factors, labels, bars = _inputs()

        result = run_beta_hedged_spread_audit(
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
            hedge_ratio=1.0,
            min_positive_fold_rate=0.5,
            min_overlap_adjusted_sharpe=0.0,
            max_drawdown_limit=0.5,
        )

        self.assertEqual(result["summary"]["cases"], 1)
        row = result["leaderboard"][0]
        self.assertEqual(row["factor_name"], "tail_filter")
        self.assertGreater(row["spread_total_return"], 0.0)
        self.assertEqual(row["classification"], "beta_hedged_spread_candidate")

    def test_writer_emits_spread_artifacts(self):
        factors, labels, bars = _inputs()
        result = run_beta_hedged_spread_audit(factors, labels, bars)

        markdown = render_beta_hedged_spread_markdown(result)
        self.assertIn("Beta-Hedged Spread Audit", markdown)

        with tempfile.TemporaryDirectory() as tmp:
            write_beta_hedged_spread_audit(tmp, result)

            self.assertTrue((Path(tmp) / "beta_hedged_spread_audit.json").exists())
            self.assertTrue((Path(tmp) / "beta_hedged_spread_audit.md").exists())
            self.assertTrue((Path(tmp) / "leaderboard.csv").exists())

    def test_short_benchmark_leg_costs_reduce_spread_return(self):
        factors, labels, bars = _inputs()
        base = run_beta_hedged_spread_audit(
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
            hedge_ratio=1.0,
            min_overlap_adjusted_sharpe=-1.0,
        )
        stressed = run_beta_hedged_spread_audit(
            factors,
            labels,
            bars,
            bottom_quantile=0.2,
            rebalance_interval=1,
            holding_period=1,
            cost_bps=100.0,
            market_impact_bps=0.0,
            portfolio_value=1_000_000.0,
            target_gross_exposure=0.6,
            hedge_ratio=1.0,
            min_overlap_adjusted_sharpe=-1.0,
        )

        self.assertLess(
            stressed["leaderboard"][0]["spread_total_return"],
            base["leaderboard"][0]["spread_total_return"],
        )


def _inputs():
    dates = pd.date_range("2024-01-02", periods=8, freq="D")
    factor_rows = []
    label_rows = []
    bar_rows = []
    market_prices = [100.0, 110.0, 100.0, 112.0, 102.0, 115.0, 104.0, 118.0]
    market_returns = [0.02, 0.01, -0.01, 0.03, -0.02, 0.01, 0.0, 0.02]
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
            forward_return = market_returns[day_index] + 0.01
            if asset_index == 0:
                forward_return = market_returns[day_index] - 0.03
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
