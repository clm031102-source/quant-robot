from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

import pandas as pd

from quant_robot.ops.shortlist_trade_attribute_cash_filter import (
    build_trade_attribute_cash_filter_audit,
    parse_attribute_filter_spec,
    write_trade_attribute_cash_filter_audit,
)


class ShortlistTradeAttributeCashFilterTest(unittest.TestCase):
    def test_attribute_filter_projects_flagged_contribution(self) -> None:
        template = pd.DataFrame(
            {
                "date": pd.to_datetime(["2020-01-10", "2020-01-17"]),
                "period_return": [0.03, 0.01],
            }
        )
        trades = pd.DataFrame(
            {
                "exit_date": pd.to_datetime(["2020-01-10", "2020-01-10", "2020-01-17"]),
                "entry_cash_proxy_weighted_return": [0.01, -0.02, 0.005],
                "stock_market": ["main", "star", "star"],
            }
        )

        audit = build_trade_attribute_cash_filter_audit(
            template_period_returns=template,
            trades_source=trades,
            candidates=(parse_attribute_filter_spec("star=stock_market:eq:star"),),
            periods_per_year=52.0,
            holding_period=4,
        )

        row = audit["rows"][0]
        self.assertEqual(row["flagged_trade_count"], 2)
        self.assertAlmostEqual(row["matched_flagged_contribution"], -0.015)
        frame = pd.DataFrame(audit["period_return_frames"]["cash_star"])
        self.assertAlmostEqual(frame.loc[0, "period_return"], 0.05)
        self.assertAlmostEqual(frame.loc[1, "period_return"], 0.005)

    def test_missing_operator_flags_blank_values(self) -> None:
        template = pd.DataFrame({"date": pd.to_datetime(["2020-01-10"]), "period_return": [0.01]})
        trades = pd.DataFrame(
            {
                "exit_date": pd.to_datetime(["2020-01-10", "2020-01-10"]),
                "entry_cash_proxy_weighted_return": [0.003, 0.004],
                "industry": [None, "tech"],
            }
        )

        audit = build_trade_attribute_cash_filter_audit(
            template_period_returns=template,
            trades_source=trades,
            candidates=(parse_attribute_filter_spec("missing_industry=industry:missing"),),
            periods_per_year=52.0,
            holding_period=4,
        )

        self.assertEqual(audit["rows"][0]["flagged_trade_count"], 1)

    def test_numeric_operator_projects_flagged_contribution(self) -> None:
        template = pd.DataFrame(
            {
                "date": pd.to_datetime(["2020-01-10", "2020-01-17"]),
                "period_return": [0.02, 0.01],
            }
        )
        trades = pd.DataFrame(
            {
                "exit_date": pd.to_datetime(["2020-01-10", "2020-01-10", "2020-01-17"]),
                "entry_cash_proxy_weighted_return": [-0.01, 0.004, -0.006],
                "turnover_rate_f": [6.0, 3.0, 8.0],
            }
        )

        audit = build_trade_attribute_cash_filter_audit(
            template_period_returns=template,
            trades_source=trades,
            candidates=(parse_attribute_filter_spec("high_turnover=turnover_rate_f:gt:5"),),
            periods_per_year=52.0,
            holding_period=4,
        )

        row = audit["rows"][0]
        self.assertEqual(row["flagged_trade_count"], 2)
        self.assertAlmostEqual(row["matched_flagged_contribution"], -0.016)
        frame = pd.DataFrame(audit["period_return_frames"]["cash_high_turnover"])
        self.assertAlmostEqual(frame.loc[0, "period_return"], 0.03)
        self.assertAlmostEqual(frame.loc[1, "period_return"], 0.016)

    def test_numeric_between_operator_flags_inclusive_range(self) -> None:
        template = pd.DataFrame({"date": pd.to_datetime(["2020-01-10"]), "period_return": [0.01]})
        trades = pd.DataFrame(
            {
                "exit_date": pd.to_datetime(["2020-01-10", "2020-01-10", "2020-01-10"]),
                "entry_cash_proxy_weighted_return": [0.002, -0.003, -0.004],
                "pb": [1.0, 3.0, 5.0],
            }
        )

        audit = build_trade_attribute_cash_filter_audit(
            template_period_returns=template,
            trades_source=trades,
            candidates=(parse_attribute_filter_spec("mid_pb=pb:between:2,5"),),
            periods_per_year=52.0,
            holding_period=4,
        )

        row = audit["rows"][0]
        self.assertEqual(row["flagged_trade_count"], 2)
        self.assertAlmostEqual(row["matched_flagged_contribution"], -0.007)

    def test_write_outputs_rows_and_period_returns(self) -> None:
        with TemporaryDirectory() as tmp:
            template = pd.DataFrame({"date": pd.to_datetime(["2020-01-10"]), "period_return": [0.01]})
            trades = pd.DataFrame(
                {
                    "exit_date": pd.to_datetime(["2020-01-10"]),
                    "entry_cash_proxy_weighted_return": [0.003],
                    "industry": ["tech"],
                }
            )
            audit = build_trade_attribute_cash_filter_audit(
                template_period_returns=template,
                trades_source=trades,
                candidates=(parse_attribute_filter_spec("tech=industry:eq:tech"),),
                periods_per_year=52.0,
                holding_period=4,
            )

            write_trade_attribute_cash_filter_audit(tmp, audit)

            self.assertTrue((Path(tmp) / "trade_attribute_cash_filter_rows.csv").exists())
            self.assertTrue((Path(tmp) / "cash_tech_official_template_period_returns.csv").exists())


if __name__ == "__main__":
    unittest.main()
