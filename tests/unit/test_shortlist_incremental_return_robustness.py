from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.shortlist_incremental_return_robustness import (
    build_shortlist_incremental_return_robustness,
    write_shortlist_incremental_return_robustness,
)


class ShortlistIncrementalReturnRobustnessTest(unittest.TestCase):
    def test_build_identifies_stable_incremental_winner(self) -> None:
        dates = pd.date_range("2020-01-31", periods=24, freq="ME")
        base = pd.DataFrame({"date": dates, "period_return": [0.01, -0.015] * 12})
        candidate = pd.DataFrame({"date": dates, "period_return": [0.02, -0.005] * 12})

        audit = build_shortlist_incremental_return_robustness(
            base_return_source=base,
            candidate_return_sources={"steady_edge": candidate},
            periods_per_year=12.0,
            holding_period=1,
            cpcv_groups=4,
            cpcv_test_group_count=1,
            bootstrap_iterations=40,
            bootstrap_period="Q",
            random_seed=7,
            max_drawdown_floor=-0.30,
        )

        self.assertEqual(audit["summary"]["candidate_count"], 1)
        self.assertEqual(audit["summary"]["best_candidate"], "steady_edge")
        row = audit["rows"][0]
        self.assertGreater(row["delta_annualized_return"], 0.0)
        self.assertGreater(row["delta_total_return"], 0.0)
        self.assertEqual(row["cpcv_split_count"], 4)
        self.assertEqual(row["cpcv_annualized_win_rate"], 1.0)
        self.assertEqual(row["bootstrap_iteration_count"], 40)
        self.assertGreater(row["bootstrap_annualized_win_rate"], 0.90)
        self.assertEqual(row["alignment_date_count"], 24)

    def test_build_reports_date_alignment_loss(self) -> None:
        base = pd.DataFrame(
            {
                "date": pd.date_range("2021-01-31", periods=6, freq="ME"),
                "period_return": [0.01] * 6,
            }
        )
        candidate = base.iloc[:-1].copy()

        audit = build_shortlist_incremental_return_robustness(
            base_return_source=base,
            candidate_return_sources={"missing_last": candidate},
            periods_per_year=12.0,
            holding_period=1,
            cpcv_groups=3,
            cpcv_test_group_count=1,
            bootstrap_iterations=5,
            random_seed=3,
        )

        row = audit["rows"][0]
        self.assertEqual(row["alignment_date_count"], 5)
        self.assertEqual(row["base_only_date_count"], 1)
        self.assertEqual(row["candidate_only_date_count"], 0)
        self.assertIn("date_alignment_loss", row["blockers"])

    def test_write_outputs_json_and_csv_artifacts(self) -> None:
        dates = pd.date_range("2020-01-31", periods=12, freq="ME")
        base = pd.DataFrame({"date": dates, "period_return": [0.01] * 12})
        candidate = pd.DataFrame({"date": dates, "period_return": [0.02] * 12})

        audit = build_shortlist_incremental_return_robustness(
            base_return_source=base,
            candidate_return_sources={"better": candidate},
            periods_per_year=12.0,
            holding_period=1,
            cpcv_groups=3,
            cpcv_test_group_count=1,
            bootstrap_iterations=5,
            random_seed=11,
        )

        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_shortlist_incremental_return_robustness(output_dir, audit)

            self.assertTrue((output_dir / "shortlist_incremental_return_robustness.json").exists())
            self.assertTrue((output_dir / "shortlist_incremental_return_summary.csv").exists())
            self.assertTrue((output_dir / "shortlist_incremental_return_cpcv_splits.csv").exists())
            self.assertTrue((output_dir / "shortlist_incremental_return_block_bootstrap.csv").exists())


if __name__ == "__main__":
    unittest.main()
