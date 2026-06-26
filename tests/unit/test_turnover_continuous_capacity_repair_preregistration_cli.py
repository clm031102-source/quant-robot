import tempfile
import unittest
from pathlib import Path

from scripts.run_turnover_continuous_capacity_repair_preregistration import (
    run_turnover_continuous_capacity_repair_preregistration_cli,
)


class TurnoverContinuousCapacityRepairPreregistrationCliTests(unittest.TestCase):
    def test_cli_runner_writes_round123_preregistration_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "round123"

            result = run_turnover_continuous_capacity_repair_preregistration_cli(
                output_dir=output_dir,
                min_candidates=6,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(
                result["summary"]["next_required_gate"],
                "capacity_repair_ic_quantile_turnover_prescreen",
            )
            self.assertTrue((output_dir / "turnover_continuous_capacity_repair_preregistration.json").exists())
            self.assertTrue((output_dir / "turnover_continuous_capacity_repair_preregistration.md").exists())
            self.assertTrue((output_dir / "turnover_continuous_capacity_repair_candidates.csv").exists())


if __name__ == "__main__":
    unittest.main()
