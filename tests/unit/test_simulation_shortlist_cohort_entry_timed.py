from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.shortlist_trade_attribute_cash_filter import AttributeFilterSpec
from quant_robot.ops.simulation_shortlist_cohort_entry_timed import (
    build_simulation_shortlist_cohort_entry_timed,
    write_simulation_shortlist_cohort_entry_timed,
)


class SimulationShortlistCohortEntryTimedTest(unittest.TestCase):
    def test_builds_cohort_rows_before_entry_timed_overlay(self) -> None:
        trades = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002"],
                "signal_date": ["2024-01-01", "2024-01-01"],
                "entry_date": ["2024-01-02", "2024-01-02"],
                "exit_date": ["2024-01-10", "2024-01-10"],
                "target_weight": [0.5, 0.5],
                "entry_cash_proxy_weighted_return": [0.01, 0.02],
            }
        )
        dragon = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_999999"],
                "date": ["2023-12-29"],
                "available_date": ["2024-01-02"],
                "top_list_event_count": [0],
                "top_list_net_amount_sum": [0.0],
                "top_list_abs_pct_change_max": [0.0],
            }
        )
        public = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-01"],
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002"],
                "public_factor_name": ["alpha", "alpha"],
                "factor_value": [1.0, 2.0],
            }
        )

        result = build_simulation_shortlist_cohort_entry_timed(
            trades_source=trades,
            dragon_tiger_source=dragon,
            public_factor_source=public,
            public_factor_name="alpha",
            public_factor_side="top",
            public_factor_quantile=1.0,
            public_factor_exposure_multiplier=1.0,
            candidate_name="demo",
            target_annual_vol=9.99,
            self_risk_threshold=-999.0,
        )

        self.assertTrue(result["paper_readiness"]["paper_ready"])
        self.assertEqual(result["summary"]["cohort_count"], 1)
        self.assertEqual(result["summary"]["unique_exit_date_count"], 1)
        self.assertAlmostEqual(result["cohort_rows"][0]["period_return"], 0.03)
        self.assertAlmostEqual(result["event_rows"][0]["period_return"], 0.03)
        self.assertEqual(len(result["trade_rows"]), 2)
        self.assertAlmostEqual(
            sum(float(row["final_return_contribution"]) for row in result["trade_rows"]),
            result["event_rows"][0]["period_return"],
        )
        self.assertAlmostEqual(result["trade_rows"][0]["final_exposure"], 1.0)
        self.assertAlmostEqual(result["trade_rows"][0]["final_target_weight"], 0.5)

    def test_public_factor_tilt_risk_cap_uses_entry_known_numeric_field(self) -> None:
        trades = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002"],
                "signal_date": ["2024-01-01", "2024-01-01"],
                "entry_date": ["2024-01-02", "2024-01-02"],
                "exit_date": ["2024-01-10", "2024-01-10"],
                "target_weight": [0.5, 0.5],
                "entry_cash_proxy_weighted_return": [0.01, 0.01],
                "turnover_rate_f": [5.0, 1.0],
            }
        )
        dragon = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_999999"],
                "date": ["2023-12-29"],
                "available_date": ["2024-01-02"],
                "top_list_event_count": [0],
                "top_list_net_amount_sum": [0.0],
                "top_list_abs_pct_change_max": [0.0],
            }
        )
        public = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-01"],
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002"],
                "public_factor_name": ["alpha", "alpha"],
                "factor_value": [1.0, 2.0],
            }
        )

        result = build_simulation_shortlist_cohort_entry_timed(
            trades_source=trades,
            dragon_tiger_source=dragon,
            public_factor_source=public,
            public_factor_name="alpha",
            public_factor_side="top",
            public_factor_quantile=1.0,
            public_factor_exposure_multiplier=2.0,
            public_factor_tilt_risk_cap_column="turnover_rate_f",
            public_factor_tilt_risk_cap_operator="gt",
            public_factor_tilt_risk_cap_value=3.0,
            public_factor_tilt_risk_cap_multiplier=1.0,
            candidate_name="risk_cap_demo",
            target_annual_vol=9.99,
            self_risk_threshold=-999.0,
        )

        self.assertEqual(result["summary"]["public_tilt_risk_capped_trade_count"], 1)
        rows = {row["asset_id"]: row for row in result["trade_rows"]}
        self.assertAlmostEqual(rows["CN_XSHE_000001"]["entry_tilt_multiplier"], 1.0)
        self.assertAlmostEqual(rows["CN_XSHE_000002"]["entry_tilt_multiplier"], 2.0)
        self.assertAlmostEqual(result["cohort_rows"][0]["period_return"], 0.03)

    def test_entry_attribute_cash_rule_zeroes_matching_trades_before_cohort_overlay(self) -> None:
        trades = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002"],
                "signal_date": ["2024-01-01", "2024-01-01"],
                "entry_date": ["2024-01-02", "2024-01-02"],
                "exit_date": ["2024-01-10", "2024-01-10"],
                "target_weight": [0.5, 0.5],
                "entry_cash_proxy_weighted_return": [0.01, 0.02],
                "entry_blocked_reasons": ["limit_down_like;limit_down_official", ""],
            }
        )
        dragon = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_999999"],
                "date": ["2023-12-29"],
                "available_date": ["2024-01-02"],
                "top_list_event_count": [0],
                "top_list_net_amount_sum": [0.0],
                "top_list_abs_pct_change_max": [0.0],
            }
        )
        public = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-01"],
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002"],
                "public_factor_name": ["alpha", "alpha"],
                "factor_value": [1.0, 2.0],
            }
        )

        result = build_simulation_shortlist_cohort_entry_timed(
            trades_source=trades,
            dragon_tiger_source=dragon,
            public_factor_source=public,
            public_factor_name="alpha",
            public_factor_side="top",
            public_factor_quantile=1.0,
            public_factor_exposure_multiplier=1.0,
            candidate_name="entry_limit_down_formal_demo",
            entry_attribute_cash_rules=(
                AttributeFilterSpec(
                    name="entry_limit_down",
                    column="entry_blocked_reasons",
                    operator="eq",
                    values=("limit_down_like;limit_down_official",),
                ),
            ),
            target_annual_vol=9.99,
            self_risk_threshold=-999.0,
        )

        self.assertEqual(result["summary"]["entry_attribute_cash_trade_count"], 1)
        self.assertEqual(result["summary"]["entry_attribute_cash_rule_counts"]["entry_limit_down"], 1)
        rows = {row["asset_id"]: row for row in result["trade_rows"]}
        self.assertTrue(rows["CN_XSHE_000001"]["entry_attribute_cash_filter"])
        self.assertAlmostEqual(rows["CN_XSHE_000001"]["entry_tilt_multiplier"], 0.0)
        self.assertAlmostEqual(rows["CN_XSHE_000001"]["pre_overlay_return_contribution"], 0.0)
        self.assertAlmostEqual(rows["CN_XSHE_000002"]["entry_tilt_multiplier"], 1.0)
        self.assertAlmostEqual(result["cohort_rows"][0]["period_return"], 0.02)

    def test_can_disable_dragon_cash_and_use_existing_pre_overlay_weight_column(self) -> None:
        trades = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002"],
                "signal_date": ["2024-01-01", "2024-01-01"],
                "entry_date": ["2024-01-02", "2024-01-02"],
                "exit_date": ["2024-01-10", "2024-01-10"],
                "pre_overlay_target_weight": [0.4, 0.6],
                "pre_overlay_return_contribution": [0.01, 0.02],
                "final_exposure": [0.5, 0.5],
                "final_target_weight": [0.2, 0.3],
                "final_return_contribution": [0.005, 0.01],
            }
        )
        dragon = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001"],
                "date": ["2023-12-29"],
                "available_date": ["2024-01-02"],
                "top_list_event_count": [1],
                "top_list_net_amount_sum": [1.0],
                "top_list_abs_pct_change_max": [10.0],
            }
        )
        public = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-01"],
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002"],
                "public_factor_name": ["alpha", "alpha"],
                "factor_value": [2.0, 1.0],
            }
        )

        result = build_simulation_shortlist_cohort_entry_timed(
            trades_source=trades,
            dragon_tiger_source=dragon,
            public_factor_source=public,
            public_factor_name="alpha",
            public_factor_side="top",
            public_factor_quantile=0.25,
            public_factor_exposure_multiplier=2.0,
            candidate_name="incremental_overlay_demo",
            trade_return_column="pre_overlay_return_contribution",
            weight_column="pre_overlay_target_weight",
            apply_dragon_cash_filter=False,
            target_annual_vol=9.99,
            self_risk_threshold=-999.0,
        )

        self.assertEqual(result["summary"]["dragon_cash_trade_count"], 0)
        rows = {row["asset_id"]: row for row in result["trade_rows"]}
        self.assertAlmostEqual(rows["CN_XSHE_000001"]["entry_tilt_multiplier"], 2.0)
        self.assertAlmostEqual(rows["CN_XSHE_000002"]["entry_tilt_multiplier"], 1.0)
        self.assertAlmostEqual(result["cohort_rows"][0]["period_return"], 0.04)
        self.assertAlmostEqual(result["cohort_rows"][0]["gross_weight"], 1.4)

    def test_writer_exports_summary_cohorts_and_events(self) -> None:
        result = {
            "stage": "simulation_shortlist_cohort_entry_timed",
            "summary": {"candidate_name": "demo"},
            "paper_readiness": {"paper_ready": True, "blockers": []},
            "metrics": {"annualized_return": 0.1},
            "cohort_rows": [{"date": "2024-01-10", "period_return": 0.01}],
            "event_rows": [{"date": "2024-01-10", "period_return": 0.01}],
        }
        with TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_simulation_shortlist_cohort_entry_timed(output, result)

            self.assertTrue((output / "simulation_shortlist_cohort_entry_timed.json").exists())
            self.assertTrue((output / "cohort_source_period_returns.csv").exists())
            self.assertTrue((output / "simulation_shortlist_entry_timed_events.csv").exists())
            self.assertTrue((output / "cohort_trade_rows.csv").exists())


if __name__ == "__main__":
    unittest.main()
