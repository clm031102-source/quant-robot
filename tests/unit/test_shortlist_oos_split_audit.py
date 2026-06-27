from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

import pandas as pd

from quant_robot.ops.shortlist_oos_split_audit import build_shortlist_oos_split_audit


class ShortlistOosSplitAuditTest(unittest.TestCase):
    def test_build_shortlist_oos_split_audit_summarizes_candidate_splits(self) -> None:
        dates = pd.date_range("2018-01-05", periods=260, freq="W-FRI")
        period_returns = [0.008 if idx % 2 == 0 else 0.004 for idx in range(len(dates))]
        returns = pd.DataFrame({"date": dates, "period_return": period_returns})

        audit = build_shortlist_oos_split_audit(
            {"steady": returns},
            train_years=(2,),
            test_years=1,
            periods_per_year=52.0,
            holding_period=4,
        )

        self.assertEqual(audit["summary"]["candidate_count"], 1)
        self.assertGreater(audit["rows"][0]["split_count"], 0)
        self.assertGreater(audit["rows"][0]["mean_oos_annualized_return"], 0.0)
        self.assertEqual(audit["rows"][0]["strict_pass_rate"], 1.0)

    def test_build_shortlist_oos_split_audit_accepts_source_specs(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "returns.csv"
            pd.DataFrame(
                {
                    "date": pd.date_range("2018-01-05", periods=260, freq="W-FRI"),
                    "custom_return": [0.005] * 260,
                }
            ).to_csv(path, index=False)

            audit = build_shortlist_oos_split_audit(
                {"custom": {"path": path, "return_column": "custom_return"}},
                train_years=(2,),
                periods_per_year=52.0,
                holding_period=4,
            )

            self.assertEqual(audit["rows"][0]["return_column"], "custom_return")


if __name__ == "__main__":
    unittest.main()
