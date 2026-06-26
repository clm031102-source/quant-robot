import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_market_residual_risk_premia_preregistration import (
    run_market_residual_risk_premia_preregistration_cli,
)


class MarketResidualRiskPremiaPreregistrationCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_candidate_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"

            result = run_market_residual_risk_premia_preregistration_cli(
                output_dir=output,
                min_candidates=8,
            )

            self.assertEqual(result["stage"], "market_residual_risk_premia_preregistration")
            self.assertGreaterEqual(result["summary"]["candidate_count"], 8)
            self.assertTrue((output / "market_residual_risk_premia_preregistration.json").exists())
            self.assertTrue((output / "market_residual_risk_premia_preregistration.md").exists())
            self.assertTrue((output / "market_residual_risk_premia_candidates.csv").exists())
            payload = json.loads(
                (output / "market_residual_risk_premia_preregistration.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["summary"]["candidate_count"], result["summary"]["candidate_count"])
            self.assertEqual(
                payload["family_rotation_context"]["next_direction"],
                "round111_market_residual_risk_premia_prescreen",
            )
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
