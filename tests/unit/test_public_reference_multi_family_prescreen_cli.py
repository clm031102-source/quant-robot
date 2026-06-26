import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_public_reference_multi_family_prescreen import (
    run_public_reference_multi_family_prescreen_cli,
)
from quant_robot.storage.dataset_store import DatasetStore
from tests.unit.test_public_reference_multi_family_prescreen import (
    _synthetic_factor_inputs,
    _synthetic_moneyflow_inputs,
    _synthetic_public_reference_bars,
)


class PublicReferenceMultiFamilyPrescreenCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_results_and_ic_observations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "store"
            output = Path(tmp) / "out"
            bars = _synthetic_public_reference_bars()
            DatasetStore(root).write_frame(
                bars,
                "processed/bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            DatasetStore(root).write_frame(
                _synthetic_factor_inputs(bars),
                "processed/factor_inputs",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            DatasetStore(root).write_frame(
                _synthetic_moneyflow_inputs(bars),
                "processed/moneyflow_inputs",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_public_reference_multi_family_prescreen_cli(
                bars_roots=[root],
                factor_input_root=root,
                moneyflow_input_root=root,
                output_dir=output,
                analysis_end_date="2025-12-31",
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
                min_signal_date_amount=1_000_000,
            )

            self.assertEqual(result["stage"], "public_reference_multi_family_prescreen")
            self.assertTrue((output / "public_reference_multi_family_prescreen.json").exists())
            self.assertTrue((output / "public_reference_multi_family_prescreen.md").exists())
            self.assertTrue((output / "public_reference_multi_family_prescreen_results.csv").exists())
            self.assertTrue((output / "public_reference_multi_family_prescreen_ic_observations.csv").exists())
            payload = json.loads(
                (output / "public_reference_multi_family_prescreen.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["summary"]["candidate_count"], 20)
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
