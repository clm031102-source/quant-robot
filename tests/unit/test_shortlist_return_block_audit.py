from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.shortlist_return_block_audit import (
    build_shortlist_return_block_audit,
    summarize_return_blocks,
    write_shortlist_return_block_audit,
)


class ShortlistReturnBlockAuditTest(unittest.TestCase):
    def test_summarize_return_blocks_flags_one_year_dependency(self) -> None:
        returns = pd.DataFrame(
            {
                "date": pd.date_range("2020-01-31", periods=36, freq="ME"),
                "period_return": [-0.01] * 12 + [0.04] * 12 + [-0.01] * 12,
            }
        )

        row = summarize_return_blocks(
            returns,
            candidate_name="one_good_year",
            periods_per_year=12.0,
            holding_period=1,
        )

        self.assertEqual(row["candidate_name"], "one_good_year")
        self.assertGreater(row["annualized_return"], 0.0)
        self.assertLess(row["leave_one_year_min_annualized_return"], 0.0)
        self.assertIn("leave_one_year_annualized_return_below_min", row["blockers"])

    def test_summarize_return_blocks_uses_generic_blocker_for_positive_floor(self) -> None:
        returns = pd.DataFrame(
            {
                "date": pd.date_range("2020-01-31", periods=36, freq="ME"),
                "period_return": [0.01] * 36,
            }
        )

        row = summarize_return_blocks(
            returns,
            candidate_name="steady_but_low",
            periods_per_year=12.0,
            holding_period=1,
            min_leave_one_year_annualized_return=0.20,
        )

        self.assertGreater(row["leave_one_year_min_annualized_return"], 0.0)
        self.assertIn("leave_one_year_annualized_return_below_min", row["blockers"])
        self.assertNotIn("negative_when_best_year_removed", row["blockers"])

    def test_build_and_write_audit_reads_auto_return_column(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "candidate.csv"
            pd.DataFrame(
                {
                    "date": ["2021-01-31", "2021-02-28", "2021-03-31", "2022-01-31"],
                    "period_return_variant": [0.02, -0.01, 0.015, 0.01],
                    "period_return": [-0.50, -0.50, -0.50, -0.50],
                }
            ).to_csv(source, index=False)

            audit = build_shortlist_return_block_audit(
                {"variant_candidate": source},
                periods_per_year=12.0,
                holding_period=1,
            )

            self.assertEqual(audit["summary"]["candidate_count"], 1)
            self.assertEqual(audit["rows"][0]["return_column"], "period_return_variant")
            self.assertGreater(audit["rows"][0]["total_return"], 0.0)

            write_shortlist_return_block_audit(root / "out", audit)
            self.assertTrue((root / "out" / "shortlist_return_block_audit.json").exists())
            self.assertTrue((root / "out" / "shortlist_return_block_audit_rows.csv").exists())


if __name__ == "__main__":
    unittest.main()
