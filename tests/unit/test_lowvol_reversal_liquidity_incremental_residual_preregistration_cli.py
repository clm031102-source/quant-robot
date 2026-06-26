import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_lowvol_reversal_liquidity_incremental_residual_preregistration import (
    run_lowvol_reversal_liquidity_incremental_residual_preregistration_cli,
)


class LowvolReversalLiquidityIncrementalResidualPreregistrationCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_candidate_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"

            result = run_lowvol_reversal_liquidity_incremental_residual_preregistration_cli(
                output_dir=output,
                min_candidates=8,
            )

            self.assertEqual(result["stage"], "lowvol_reversal_liquidity_incremental_residual_preregistration")
            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output / "lowvol_reversal_liquidity_incremental_residual_preregistration.json").exists())
            self.assertTrue((output / "lowvol_reversal_liquidity_incremental_residual_preregistration.md").exists())
            self.assertTrue((output / "lowvol_reversal_liquidity_incremental_residual_candidates.csv").exists())
            payload = json.loads(
                (output / "lowvol_reversal_liquidity_incremental_residual_preregistration.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                payload["summary"]["next_required_gate"],
                "round120_lowvol_reversal_liquidity_incremental_residual_prescreen",
            )
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
