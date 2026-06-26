import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_turnover_continuous_capacity_repair_prescreen import (
    run_turnover_continuous_capacity_repair_prescreen_cli,
)
from tests.unit.test_turnover_continuous_capacity_repair_prescreen import _synthetic_bars_and_daily_basic


class TurnoverContinuousCapacityRepairPrescreenCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_results_and_ic_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            factor_root = Path(tmp) / "daily_basic"
            output = Path(tmp) / "output"
            bars, daily_basic = _synthetic_bars_and_daily_basic()
            DatasetStore(root).write_frame(
                bars,
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            DatasetStore(factor_root).write_frame(
                daily_basic,
                "processed/factor_inputs",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_turnover_continuous_capacity_repair_prescreen_cli(
                bars_roots=[root],
                factor_input_root=factor_root,
                output_dir=output,
                analysis_end_date="2025-12-31",
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
                min_signal_date_amount=10_000_000,
            )

            self.assertEqual(result["summary"]["candidate_count"], 6)
            self.assertTrue((output / "turnover_continuous_capacity_repair_prescreen.json").exists())
            self.assertTrue((output / "turnover_continuous_capacity_repair_prescreen.md").exists())
            self.assertTrue((output / "turnover_continuous_capacity_repair_prescreen_results.csv").exists())
            self.assertTrue(
                (output / "turnover_continuous_capacity_repair_prescreen_ic_observations.csv").exists()
            )
            payload = json.loads(
                (output / "turnover_continuous_capacity_repair_prescreen.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["summary"]["candidate_count"], result["summary"]["candidate_count"])
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
