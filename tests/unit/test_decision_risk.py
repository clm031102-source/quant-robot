import unittest

import pandas as pd

from quant_robot.research.decision import (
    build_benchmark_curve,
    compare_strategy_to_benchmark,
    decision_summary,
    regime_allowed_dates,
)


class DecisionRiskTests(unittest.TestCase):
    def test_equal_weight_benchmark_averages_asset_returns(self):
        bars = _bars(
            {
                "A": [100.0, 110.0, 121.0],
                "B": [50.0, 50.0, 55.0],
            }
        )

        curve = build_benchmark_curve(bars)

        self.assertEqual(list(curve["date"]), list(pd.date_range("2024-01-01", periods=3).date))
        self.assertAlmostEqual(curve.iloc[0]["benchmark_return"], 0.0)
        self.assertAlmostEqual(curve.iloc[1]["benchmark_return"], 0.05)
        self.assertAlmostEqual(curve.iloc[2]["benchmark_return"], 0.10)
        self.assertAlmostEqual(curve.iloc[-1]["benchmark_equity"], 1.155)

    def test_asset_benchmark_uses_specific_asset_path(self):
        bars = _bars(
            {
                "A": [100.0, 110.0, 121.0],
                "B": [50.0, 45.0, 40.5],
            }
        )

        curve = build_benchmark_curve(bars, benchmark_asset_id="B")

        self.assertEqual(set(curve["benchmark_asset_id"]), {"B"})
        self.assertAlmostEqual(curve.iloc[1]["benchmark_return"], -0.10)
        self.assertAlmostEqual(curve.iloc[-1]["benchmark_equity"], 0.81)

    def test_compare_strategy_to_benchmark_and_cash(self):
        equity = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=3).date,
                "period_return": [0.0, 0.10, 0.0],
                "equity": [1.0, 1.1, 1.1],
            }
        )
        benchmark = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=3).date,
                "benchmark_return": [0.0, 0.02, 0.01],
                "benchmark_equity": [1.0, 1.02, 1.0302],
            }
        )

        metrics = compare_strategy_to_benchmark(equity, benchmark, cash_annual_return=0.0, periods_per_year=252)

        self.assertAlmostEqual(metrics["strategy_total_return"], 0.10)
        self.assertAlmostEqual(metrics["benchmark_total_return"], 0.0302)
        self.assertAlmostEqual(metrics["relative_return"], 0.0698)
        self.assertAlmostEqual(metrics["cash_total_return"], 0.0)
        self.assertAlmostEqual(metrics["excess_over_cash"], 0.10)

    def test_regime_filter_blocks_dates_with_negative_benchmark_momentum(self):
        bars = _bars({"A": [100.0, 99.0, 98.0, 97.0]})

        regime = regime_allowed_dates(bars, benchmark_asset_id="A", lookback=2)

        self.assertFalse(regime.iloc[0]["regime_allowed"])
        self.assertFalse(regime.iloc[-1]["regime_allowed"])
        self.assertLess(regime.iloc[-1]["regime_momentum"], 0.0)

    def test_decision_summary_rejects_relative_return_and_drawdown_breaches(self):
        summary = decision_summary(
            {"max_drawdown": -0.31},
            {"relative_return": -0.02},
            min_relative_return=0.0,
            max_drawdown_limit=0.20,
        )

        self.assertEqual(summary["decision_status"], "rejected")
        self.assertIn("relative_return_below_threshold", summary["rejection_reasons"])
        self.assertIn("drawdown_above_limit", summary["rejection_reasons"])

    def test_decision_summary_rejects_capacity_limited_strategies(self):
        summary = decision_summary(
            {"max_drawdown": -0.10, "capacity_limited_trades": 1},
            {"relative_return": 0.10},
            min_relative_return=0.0,
            max_drawdown_limit=0.20,
        )

        self.assertEqual(summary["decision_status"], "rejected")
        self.assertIn("capacity_limited_trades_present", summary["rejection_reasons"])


def _bars(price_paths: dict[str, list[float]]) -> pd.DataFrame:
    dates = list(pd.date_range("2024-01-01", periods=max(len(path) for path in price_paths.values())).date)
    rows = []
    for asset_id, prices in price_paths.items():
        for date, price in zip(dates, prices, strict=True):
            rows.append(
                {
                    "asset_id": asset_id,
                    "date": date,
                    "market": "CN_ETF",
                    "adj_close": price,
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
