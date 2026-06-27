from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd


class ShortlistIncrementalReturnRobustnessCliTest(unittest.TestCase):
    def test_cli_writes_incremental_robustness_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "base.csv"
            candidate = root / "candidate.csv"
            output = root / "out"
            dates = pd.date_range("2020-01-31", periods=12, freq="ME")
            pd.DataFrame({"date": dates, "period_return": [0.01, -0.01] * 6}).to_csv(base, index=False)
            pd.DataFrame({"date": dates, "period_return": [0.02, 0.00] * 6}).to_csv(
                candidate,
                index=False,
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_shortlist_incremental_return_robustness.py",
                    "--base-return-source",
                    str(base),
                    "--candidate-return-source",
                    f"better={candidate}",
                    "--periods-per-year",
                    "12",
                    "--holding-period",
                    "1",
                    "--cpcv-groups",
                    "3",
                    "--cpcv-test-group-count",
                    "1",
                    "--bootstrap-iterations",
                    "5",
                    "--output-dir",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(completed.stdout)
            self.assertEqual(payload["summary"]["candidate_count"], 1)
            self.assertEqual(payload["top"][0]["candidate_name"], "better")
            self.assertTrue((output / "shortlist_incremental_return_robustness.json").exists())
            self.assertTrue((output / "shortlist_incremental_return_summary.csv").exists())


if __name__ == "__main__":
    unittest.main()
