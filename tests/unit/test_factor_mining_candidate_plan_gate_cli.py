import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.factor_mining_candidate_plan_gate import (
    default_cn_stock_pre_mining_control_plan,
    default_cn_stock_promotion_policy,
)
from scripts.run_factor_mining_candidate_plan_gate import run_factor_mining_candidate_plan_gate


class FactorMiningCandidatePlanGateCliTests(unittest.TestCase):
    def test_cli_writes_candidate_plan_gate_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = root / "candidate_plan.json"
            quality_gate_path = root / "quality_gate.json"
            output_dir = root / "candidate_gate"
            plan_path.write_text(json.dumps(_candidate_plan()), encoding="utf-8")
            quality_gate_path.write_text(
                json.dumps({"status": "classified", "decision": {"startup_gate_cleared": True, "promotion_gate_cleared": False}}),
                encoding="utf-8",
            )

            packet = run_factor_mining_candidate_plan_gate(
                candidate_plan=plan_path,
                quality_gate=quality_gate_path,
                gate_stage="discovery",
                output_dir=output_dir,
            )

            self.assertEqual(packet["status"], "research_ready")
            self.assertTrue((output_dir / "factor_mining_candidate_plan_gate.json").exists())
            self.assertTrue((output_dir / "factor_mining_candidate_plan_gate.md").exists())
            payload = json.loads((output_dir / "factor_mining_candidate_plan_gate.json").read_text(encoding="utf-8"))
            self.assertTrue(payload["decision"]["candidate_plan_gate_cleared"])
            markdown = (output_dir / "factor_mining_candidate_plan_gate.md").read_text(encoding="utf-8")
            self.assertIn("Factor Mining Candidate Plan Gate", markdown)
            self.assertIn("cn_stock_tradeability", markdown)


def _candidate_plan() -> dict:
    return {
        "stage": "example_preregistration",
        "research_control_plan": default_cn_stock_pre_mining_control_plan(),
        "promotion_policy": default_cn_stock_promotion_policy(),
        "candidates": [
            {
                "factor_name": "example_factor",
                "family": "example_family",
                "market": "CN",
                "asset_type": "stock",
                "registration_status": "pre_registered",
                "hypothesis_source": "public_reference:example",
                "economic_rationale": "Example economic rationale.",
                "portfolio_backtest_allowed": False,
                "promotion_allowed": False,
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
