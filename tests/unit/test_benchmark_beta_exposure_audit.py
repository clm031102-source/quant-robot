import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.benchmark_beta_exposure_audit import (
    calculate_benchmark_beta_exposure,
    classify_benchmark_beta_exposure,
    render_benchmark_beta_exposure_markdown,
    run_benchmark_beta_exposure_audit,
    write_benchmark_beta_exposure_audit,
)


class BenchmarkBetaExposureAuditTests(unittest.TestCase):
    def test_beta_stats_identify_benchmark_explained_returns(self):
        dates = pd.date_range("2024-01-02", periods=8, freq="D")
        benchmark_returns = pd.Series([0.02, 0.01, -0.01, 0.03, -0.02, 0.01, 0.00, 0.02])
        strategy_returns = benchmark_returns * 0.5 + 0.0001
        strategy_curve = pd.DataFrame({"date": dates, "period_return": strategy_returns})
        benchmark_curve = pd.DataFrame({"date": dates, "period_return": benchmark_returns})

        stats = calculate_benchmark_beta_exposure(strategy_curve, benchmark_curve, periods_per_year=252.0)

        self.assertAlmostEqual(stats["beta"], 0.5, places=6)
        self.assertGreater(stats["r_squared"], 0.99)
        self.assertLess(stats["residual_sharpe"], 0.5)
        self.assertEqual(
            classify_benchmark_beta_exposure(stats),
            "beta_dominated_or_market_timing",
        )

    def test_audit_writes_beta_exposure_artifacts(self):
        factors, labels, bars = _inputs()

        result = run_benchmark_beta_exposure_audit(
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
            risk_off_exposure=0.2,
            market_state_lookback=1,
            min_alpha_t_stat=2.0,
            min_residual_sharpe=0.5,
        )

        self.assertEqual(result["summary"]["cases"], 1)
        self.assertEqual(result["leaderboard"][0]["factor_name"], "tail_filter")
        self.assertIn("dynamic_beta", result["leaderboard"][0])

        markdown = render_benchmark_beta_exposure_markdown(result)
        self.assertIn("Benchmark Beta Exposure Audit", markdown)

        with tempfile.TemporaryDirectory() as tmp:
            write_benchmark_beta_exposure_audit(tmp, result)

            self.assertTrue((Path(tmp) / "benchmark_beta_exposure_audit.json").exists())
            self.assertTrue((Path(tmp) / "benchmark_beta_exposure_audit.md").exists())
            self.assertTrue((Path(tmp) / "leaderboard.csv").exists())


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
            forward_return = market_returns[day_index]
            if asset_index == 0:
                forward_return -= 0.03
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
