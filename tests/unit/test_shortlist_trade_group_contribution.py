from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.shortlist_trade_group_contribution import (
    build_trade_group_contribution_audit,
    write_trade_group_contribution_audit,
)


class ShortlistTradeGroupContributionTest(unittest.TestCase):
    def test_group_contribution_summary_handles_missing_and_allowed_rate(self) -> None:
        trades = pd.DataFrame(
            {
                "exit_date": pd.to_datetime(["2020-01-10", "2020-01-10", "2020-01-17", "2021-01-15"]),
                "entry_cash_proxy_weighted_return": [0.10, -0.03, 0.02, -0.01],
                "industry": ["tech", "tech", None, "bank"],
                "entry_allowed": [True, False, True, True],
            }
        )

        audit = build_trade_group_contribution_audit(
            trades_source=trades,
            group_columns=("industry",),
            top_n=2,
        )

        rows = pd.DataFrame(audit["group_contribution_summary"])
        tech = rows[rows["group_value"] == "tech"].iloc[0]
        missing = rows[rows["group_value"] == "MISSING"].iloc[0]
        summary = audit["summary"]["columns"]["industry"]

        self.assertEqual(int(tech["trade_count"]), 2)
        self.assertAlmostEqual(float(tech["contribution_sum"]), 0.07)
        self.assertAlmostEqual(float(tech["entry_allowed_rate"]), 0.5)
        self.assertAlmostEqual(float(missing["contribution_sum"]), 0.02)
        self.assertEqual(summary["best_group"], "tech")
        self.assertEqual(summary["worst_group"], "bank")

    def test_by_year_and_writer_outputs_files(self) -> None:
        with TemporaryDirectory() as tmp:
            trades = pd.DataFrame(
                {
                    "exit_date": pd.to_datetime(["2020-01-10", "2021-01-15"]),
                    "entry_cash_proxy_weighted_return": [0.01, 0.02],
                    "industry": ["tech", "bank"],
                    "entry_allowed": [True, True],
                }
            )
            audit = build_trade_group_contribution_audit(
                trades_source=trades,
                group_columns=("industry",),
            )

            write_trade_group_contribution_audit(tmp, audit)

            by_year = pd.DataFrame(audit["group_contribution_by_year"])
            self.assertEqual(set(by_year["year"]), {2020, 2021})
            self.assertTrue((Path(tmp) / "trade_group_contribution_audit.json").exists())
            self.assertTrue((Path(tmp) / "group_contribution_summary.csv").exists())
            self.assertTrue((Path(tmp) / "round390_group_contribution_summary.json").exists())


if __name__ == "__main__":
    unittest.main()
