from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

import pandas as pd

from quant_robot.ops.shortlist_event_beta_audit import (
    build_shortlist_event_beta_audit,
    write_shortlist_event_beta_audit,
)


class ShortlistEventBetaAuditTest(unittest.TestCase):
    def test_build_event_beta_audit_estimates_known_beta(self) -> None:
        dates = pd.date_range("2020-01-03", periods=80, freq="W-FRI")
        benchmark_return = [0.01 if idx % 2 == 0 else -0.004 for idx in range(len(dates))]
        strategy_return = [0.002 + 0.5 * value for value in benchmark_return]
        strategy = pd.DataFrame({"date": dates, "period_return": strategy_return})
        benchmark = pd.DataFrame(
            {
                "date": dates,
                "benchmark": ["bench"] * len(dates),
                "period_return_benchmark": benchmark_return,
            }
        )

        audit = build_shortlist_event_beta_audit(
            {"candidate": strategy},
            benchmark_source=benchmark,
            benchmarks=("bench",),
            periods_per_year=52.0,
            holding_period=4,
        )

        row = audit["rows"][0]
        self.assertAlmostEqual(row["beta"], 0.5, places=6)
        self.assertGreater(row["alpha_annualized"], 0.0)
        self.assertEqual(row["observations"], len(dates))

    def test_write_event_beta_audit_outputs_csvs(self) -> None:
        with TemporaryDirectory() as tmp:
            dates = pd.date_range("2020-01-03", periods=20, freq="W-FRI")
            strategy = pd.DataFrame({"date": dates, "period_return": [0.003] * len(dates)})
            benchmark = pd.DataFrame(
                {
                    "date": dates,
                    "benchmark": ["bench"] * len(dates),
                    "period_return_benchmark": [0.001] * len(dates),
                }
            )
            audit = build_shortlist_event_beta_audit(
                {"candidate": strategy},
                benchmark_source=benchmark,
                benchmarks=("bench",),
                periods_per_year=52.0,
                holding_period=4,
            )

            write_shortlist_event_beta_audit(tmp, audit)

            self.assertTrue((Path(tmp) / "shortlist_event_beta_audit_rows.csv").exists())
            self.assertTrue((Path(tmp) / "shortlist_event_beta_hedged_returns.csv").exists())


if __name__ == "__main__":
    unittest.main()
