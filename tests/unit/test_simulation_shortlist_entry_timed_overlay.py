from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.simulation_shortlist_entry_timed_overlay import (
    build_simulation_shortlist_entry_timed_overlay,
    write_simulation_shortlist_entry_timed_overlay,
)


class SimulationShortlistEntryTimedOverlayTest(unittest.TestCase):
    def test_self_risk_uses_only_returns_closed_before_decision_date(self) -> None:
        raw_events = pd.DataFrame(
            {
                "date": ["2024-01-10", "2024-01-20", "2024-01-25"],
                "entry_date": ["2024-01-01", "2024-01-05", "2024-01-11"],
                "period_return": [-0.10, 0.10, 0.10],
            }
        )

        result = build_simulation_shortlist_entry_timed_overlay(
            raw_events,
            candidate_name="demo_entry_timed",
            date_column="date",
            decision_date_column="entry_date",
            target_annual_vol=9.99,
            lookback_events=84,
            min_exposure=0.25,
            max_exposure=1.0,
        )

        rows = pd.DataFrame(result["event_rows"]).sort_values("date")
        self.assertEqual(rows["self_risk_exposure"].tolist(), [1.0, 1.0, 0.5])
        self.assertAlmostEqual(rows.iloc[1]["period_return"], 0.10)
        self.assertAlmostEqual(rows.iloc[2]["period_return"], 0.05)
        self.assertTrue(result["paper_readiness"]["paper_ready"])

    def test_writer_exports_entry_timed_overlay_artifacts(self) -> None:
        result = {
            "stage": "simulation_shortlist_entry_timed_overlay",
            "summary": {"candidate_name": "demo"},
            "paper_readiness": {"paper_ready": True, "blockers": []},
            "metrics": {"annualized_return": 0.1},
            "event_rows": [{"date": "2024-01-10", "period_return": 0.01}],
        }

        with TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_simulation_shortlist_entry_timed_overlay(output, result)

            self.assertTrue((output / "simulation_shortlist_entry_timed_overlay.json").exists())
            self.assertTrue((output / "simulation_shortlist_entry_timed_events.csv").exists())

    def test_metrics_aggregate_duplicate_exit_dates_before_scoring(self) -> None:
        raw_events = pd.DataFrame(
            {
                "date": ["2024-01-10", "2024-01-10", "2024-02-10"],
                "entry_date": ["2024-01-01", "2024-01-02", "2024-02-01"],
                "period_return": [0.01, 0.02, 0.03],
            }
        )

        result = build_simulation_shortlist_entry_timed_overlay(
            raw_events,
            candidate_name="duplicate_exit_dates",
            date_column="date",
            decision_date_column="entry_date",
            target_annual_vol=9.99,
            self_risk_threshold=-999.0,
        )

        self.assertEqual(len(result["event_rows"]), 3)
        self.assertEqual(result["metrics"]["period_count"], 2)


if __name__ == "__main__":
    unittest.main()
