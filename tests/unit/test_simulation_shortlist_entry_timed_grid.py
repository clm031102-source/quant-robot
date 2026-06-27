from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.simulation_shortlist_entry_timed_grid import (
    build_simulation_shortlist_entry_timed_grid,
    discover_entry_timed_period_event_sources,
    write_simulation_shortlist_entry_timed_grid,
)


class SimulationShortlistEntryTimedGridTest(unittest.TestCase):
    def test_grid_ranks_entry_timed_candidates_and_writes_events(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            strong = root / "strong_official_template_period_returns.csv"
            weak = root / "weak_official_template_period_returns.csv"
            self._write_events(strong, [0.01] * 36)
            self._write_events(weak, [-0.005] * 36)

            sources = discover_entry_timed_period_event_sources(root)
            result = build_simulation_shortlist_entry_timed_grid(
                sources,
                candidate_prefix="demo",
                target_annual_vol=9.99,
                max_drawdown_limit=-0.30,
            )

            self.assertEqual(result["summary"]["candidate_count"], 2)
            self.assertEqual(result["rows"][0]["candidate_name"], "demo_strong")
            self.assertTrue(result["rows"][0]["paper_ready"])
            self.assertIn("non_positive_total_return", result["rows"][1]["blockers"])

            output = root / "out"
            summary = write_simulation_shortlist_entry_timed_grid(output, result)
            first_event_path = Path(summary["rows"][0]["event_output_path"])
            self.assertTrue((output / "simulation_shortlist_entry_timed_grid.json").exists())
            self.assertTrue((output / "simulation_shortlist_entry_timed_grid_rows.csv").exists())
            self.assertTrue(first_event_path.exists())

    @staticmethod
    def _write_events(path: Path, returns: list[float]) -> None:
        pd.DataFrame(
            {
                "date": pd.date_range("2018-02-01", periods=len(returns), freq="30D"),
                "entry_date": pd.date_range("2018-01-01", periods=len(returns), freq="30D"),
                "period_return": returns,
            }
        ).to_csv(path, index=False)


if __name__ == "__main__":
    unittest.main()
