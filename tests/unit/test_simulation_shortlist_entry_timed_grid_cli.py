from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd


class SimulationShortlistEntryTimedGridCliTest(unittest.TestCase):
    def test_cli_writes_grid_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "sources"
            source_dir.mkdir()
            pd.DataFrame(
                {
                    "date": ["2020-02-01", "2020-03-01"],
                    "entry_date": ["2020-01-01", "2020-02-01"],
                    "period_return": [0.01, 0.02],
                }
            ).to_csv(source_dir / "demo_official_template_period_returns.csv", index=False)
            output = root / "out"

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_simulation_shortlist_entry_timed_grid.py",
                    "--source-dir",
                    str(source_dir),
                    "--output-dir",
                    str(output),
                    "--target-annual-vol",
                    "9.99",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("entry_timed_demo", completed.stdout)
            self.assertTrue((output / "simulation_shortlist_entry_timed_grid.json").exists())


if __name__ == "__main__":
    unittest.main()
