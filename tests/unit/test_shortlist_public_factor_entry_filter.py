from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.shortlist_public_factor_entry_filter import (
    build_public_factor_entry_filter_audit,
    build_public_factor_entry_tilt_audit,
    parse_public_factor_filter_spec,
    parse_public_factor_tilt_spec,
    write_public_factor_entry_filter_audit,
)


class ShortlistPublicFactorEntryFilterTest(unittest.TestCase):
    def test_public_filter_excludes_pre_flagged_dragon_trades_before_projection(self) -> None:
        template = pd.DataFrame({"date": ["2024-02-01"], "period_return": [0.04]})
        trades = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002", "CN_XSHE_000003"],
                "signal_date": ["2024-01-15", "2024-01-15", "2024-01-15"],
                "entry_date": ["2024-01-16", "2024-01-16", "2024-01-16"],
                "exit_date": ["2024-02-01", "2024-02-01", "2024-02-01"],
                "entry_cash_proxy_weighted_return": [-0.03, -0.02, 0.01],
            }
        )
        dragon = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001"],
                "date": ["2024-01-12"],
                "available_date": ["2024-01-13"],
                "top_list_event_count": [1],
                "top_list_net_amount_sum": [100.0],
                "top_list_abs_pct_change_max": [10.0],
            }
        )
        public = pd.DataFrame(
            {
                "date": ["2024-01-15", "2024-01-15", "2024-01-15"],
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002", "CN_XSHE_000003"],
                "public_factor_name": ["adx"] * 3,
                "factor_value": [0.0, 1.0, 2.0],
            }
        )

        audit = build_public_factor_entry_filter_audit(
            template_period_returns=template,
            trades_source=trades,
            public_factor_source=public,
            candidates=(parse_public_factor_filter_spec("adx_bottom=adx:bottom:0.50"),),
            pre_exclude_candidates=("dragon_hot_chase_20d",),
            dragon_tiger_source=dragon,
            periods_per_year=52.0,
            holding_period=4,
        )

        row = audit["rows"][0]
        period_rows = audit["period_return_frames"]["cash_public_adx_bottom"]
        self.assertEqual(audit["summary"]["pre_excluded_trade_count"], 1)
        self.assertEqual(row["flagged_trade_count"], 1)
        self.assertAlmostEqual(row["matched_flagged_contribution"], -0.02)
        self.assertAlmostEqual(period_rows[0]["period_return"], 0.06)

    def test_writer_exports_public_filter_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            template = pd.DataFrame({"date": ["2024-02-01"], "period_return": [0.01]})
            trades = pd.DataFrame(
                {
                    "asset_id": ["CN_XSHE_000002"],
                    "signal_date": ["2024-01-15"],
                    "entry_date": ["2024-01-16"],
                    "exit_date": ["2024-02-01"],
                    "entry_cash_proxy_weighted_return": [-0.02],
                }
            )
            public = pd.DataFrame(
                {
                    "date": ["2024-01-15"],
                    "asset_id": ["CN_XSHE_000002"],
                    "public_factor_name": ["adx"],
                    "factor_value": [1.0],
                }
            )
            audit = build_public_factor_entry_filter_audit(
                template_period_returns=template,
                trades_source=trades,
                public_factor_source=public,
                candidates=(parse_public_factor_filter_spec("adx_top=adx:top:0.20"),),
                periods_per_year=52.0,
                holding_period=4,
            )

            write_public_factor_entry_filter_audit(tmp, audit)

            self.assertTrue((Path(tmp) / "public_factor_entry_filter_audit.json").exists())
            self.assertTrue((Path(tmp) / "public_factor_entry_filter_rows.csv").exists())
            self.assertTrue((Path(tmp) / "cash_public_adx_top_official_template_period_returns.csv").exists())

    def test_public_tilt_adds_multiplier_exposure_to_flagged_entries(self) -> None:
        template = pd.DataFrame({"date": ["2024-02-01"], "period_return": [0.04]})
        trades = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002", "CN_XSHE_000003"],
                "signal_date": ["2024-01-15", "2024-01-15", "2024-01-15"],
                "entry_date": ["2024-01-16", "2024-01-16", "2024-01-16"],
                "exit_date": ["2024-02-01", "2024-02-01", "2024-02-01"],
                "entry_cash_proxy_weighted_return": [0.03, 0.02, -0.01],
            }
        )
        public = pd.DataFrame(
            {
                "date": ["2024-01-15", "2024-01-15", "2024-01-15"],
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002", "CN_XSHE_000003"],
                "public_factor_name": ["qlib"] * 3,
                "factor_value": [3.0, 2.0, 1.0],
            }
        )

        audit = build_public_factor_entry_tilt_audit(
            template_period_returns=template,
            trades_source=trades,
            public_factor_source=public,
            candidates=(parse_public_factor_tilt_spec("qlib_top=qlib:top:0.50:1.50"),),
            periods_per_year=52.0,
            holding_period=4,
        )

        row = audit["rows"][0]
        period_rows = audit["period_return_frames"]["tilt_public_qlib_top"]
        self.assertEqual(row["flagged_trade_count"], 2)
        self.assertAlmostEqual(row["matched_flagged_contribution"], 0.05)
        self.assertAlmostEqual(row["exposure_multiplier"], 1.5)
        self.assertAlmostEqual(period_rows[0]["period_return"], 0.065)


if __name__ == "__main__":
    unittest.main()
