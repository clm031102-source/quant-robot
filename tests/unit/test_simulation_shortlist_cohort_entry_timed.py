from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

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


if __name__ == "__main__":
    unittest.main()
