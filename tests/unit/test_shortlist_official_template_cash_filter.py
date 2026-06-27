from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from quant_robot.ops.shortlist_official_template_cash_filter import (
    build_official_template_cash_filter_audit,
    write_official_template_cash_filter_audit,
)


class ShortlistOfficialTemplateCashFilterTest(unittest.TestCase):
    def test_projects_flagged_trade_contribution_onto_official_template(self) -> None:
        template = pd.DataFrame(
            {
                "date": ["2024-02-01", "2024-02-08"],
                "period_return": [0.01, 0.02],
            }
        )
        trades = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002"],
                "entry_date": ["2024-01-15", "2024-01-15"],
                "exit_date": ["2024-02-01", "2024-02-15"],
                "entry_cash_proxy_weighted_return": [-0.03, -0.04],
            }
        )
        dragon = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002"],
                "date": ["2024-01-10", "2024-01-10"],
                "available_date": ["2024-01-11", "2024-01-11"],
                "top_list_event_count": [1, 1],
                "top_list_net_amount_sum": [100.0, 200.0],
                "top_list_abs_pct_change_max": [10.0, 9.8],
            }
        )

        audit = build_official_template_cash_filter_audit(
            template_period_returns=template,
            trades_source=trades,
            dragon_tiger_source=dragon,
            candidates=("dragon_hot_chase_20d",),
            periods_per_year=52.0,
            holding_period=4,
            max_unmatched_abs_contribution=0.001,
        )

        row = audit["rows"][0]
        self.assertEqual(row["flagged_trade_count"], 2)
        self.assertEqual(row["matched_flagged_trade_count"], 1)
        self.assertEqual(row["unmatched_flagged_trade_count"], 1)
        self.assertAlmostEqual(row["matched_flagged_contribution"], -0.03)
        self.assertAlmostEqual(row["unmatched_flagged_contribution"], -0.04)
        self.assertIn("unmatched_flagged_contribution_above_limit", row["blockers"])
        period_rows = audit["period_return_frames"]["cash_dragon_hot_chase_20d"]
        self.assertAlmostEqual(period_rows[0]["period_return"], 0.04)
        self.assertEqual(len(period_rows), 2)

    def test_writer_exports_audit_and_period_returns(self) -> None:
        template = pd.DataFrame({"date": ["2024-02-01"], "period_return": [0.01]})
        trades = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001"],
                "entry_date": ["2024-01-15"],
                "exit_date": ["2024-02-01"],
                "entry_cash_proxy_weighted_return": [-0.03],
            }
        )
        dragon = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001"],
                "date": ["2024-01-10"],
                "available_date": ["2024-01-11"],
                "top_list_event_count": [1],
                "top_list_net_amount_sum": [100.0],
                "top_list_abs_pct_change_max": [10.0],
            }
        )
        audit = build_official_template_cash_filter_audit(
            template_period_returns=template,
            trades_source=trades,
            dragon_tiger_source=dragon,
            candidates=("dragon_hot_chase_20d",),
            periods_per_year=52.0,
            holding_period=4,
        )

        with TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_official_template_cash_filter_audit(output, audit)

            self.assertTrue((output / "official_template_cash_filter_audit.json").exists())
            self.assertTrue((output / "official_template_cash_filter_rows.csv").exists())
            self.assertTrue((output / "cash_dragon_hot_chase_20d_official_template_period_returns.csv").exists())


if __name__ == "__main__":
    unittest.main()
