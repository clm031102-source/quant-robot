import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_public_tradeable_indicator_composite_preregistration import (
    run_public_tradeable_indicator_composite_preregistration_cli,
)


class PublicTradeableIndicatorCompositePreregistrationCliTests(unittest.TestCase):
    def test_cli_writes_preregistration_outputs_and_candidate_plan_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)

            result = run_public_tradeable_indicator_composite_preregistration_cli(output_dir=output)

            self.assertEqual(result["stage"], "public_tradeable_indicator_composite_preregistration")
            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output / "public_tradeable_indicator_composite_preregistration.json").exists())
            self.assertTrue((output / "public_tradeable_indicator_composite_preregistration.md").exists())
            self.assertTrue((output / "public_tradeable_indicator_composite_candidates.csv").exists())
            self.assertTrue((output / "factor_mining_candidate_plan_gate.json").exists())
            gate = json.loads((output / "factor_mining_candidate_plan_gate.json").read_text(encoding="utf-8"))
            self.assertEqual(gate["status"], "research_ready")
            self.assertTrue(gate["decision"]["candidate_plan_gate_cleared"])
            self.assertFalse(gate["decision"]["portfolio_grid_allowed"])


if __name__ == "__main__":
    unittest.main()
