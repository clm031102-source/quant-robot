from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from scripts.run_simulation_shortlist_entry_timed_overlay import (
    run_simulation_shortlist_entry_timed_overlay_cli,
)


class SimulationShortlistEntryTimedOverlayCliTest(unittest.TestCase):
    def test_cli_writes_entry_timed_overlay_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "events.csv"
            output = root / "out"
            pd.DataFrame(
                {
                    "date": ["2024-01-10"],
                    "entry_date": ["2024-01-02"],
                    "period_return": [0.01],
                }
            ).to_csv(source, index=False)

            result = run_simulation_shortlist_entry_timed_overlay_cli(
                period_events=source,
                candidate_name="demo",
                output_dir=output,
            )

            self.assertEqual(result["summary"]["event_count"], 1)
            self.assertTrue((output / "simulation_shortlist_entry_timed_overlay.json").exists())
            self.assertTrue((output / "simulation_shortlist_entry_timed_events.csv").exists())


if __name__ == "__main__":
    unittest.main()
