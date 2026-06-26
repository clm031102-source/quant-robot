import tempfile
import unittest
from pathlib import Path

from scripts.run_price_volume_shock_reversal_preregistration import (
    run_price_volume_shock_reversal_preregistration_cli,
)


class PriceVolumeShockReversalPreregistrationCliTests(unittest.TestCase):
    def test_cli_writes_round157_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            result = run_price_volume_shock_reversal_preregistration_cli(output_dir=output)

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(
                result["summary"]["next_required_gate"],
                "round158_price_volume_shock_reversal_neutral_prescreen",
            )
            self.assertTrue((output / "price_volume_shock_reversal_preregistration.json").exists())
            self.assertTrue((output / "price_volume_shock_reversal_preregistration.md").exists())
            self.assertTrue((output / "price_volume_shock_reversal_candidates.csv").exists())

    def test_cli_raises_when_candidate_or_family_floor_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                run_price_volume_shock_reversal_preregistration_cli(
                    output_dir=tmp,
                    min_candidates=99,
                    min_families=4,
                )


if __name__ == "__main__":
    unittest.main()
