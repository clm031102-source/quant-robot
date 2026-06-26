import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.portfolio_construction_policy_gate import default_cn_stock_portfolio_policy
from scripts.run_portfolio_construction_policy_gate import run_portfolio_construction_policy_gate_cli


class PortfolioConstructionPolicyGateCliTests(unittest.TestCase):
    def test_cli_writes_policy_gate_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "policy.json"
            output = root / "output"
            config.write_text(json.dumps(default_cn_stock_portfolio_policy()), encoding="utf-8")

            result = run_portfolio_construction_policy_gate_cli(config_path=config, output_dir=output)

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output / "portfolio_construction_policy_gate.json").exists())
            payload = json.loads((output / "portfolio_construction_policy_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(payload["promotion_policy"]["profitability_claim_allowed_without_policy_gate"])

    def test_cli_raises_when_policy_is_blocked_without_allow_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "policy.json"
            policy = default_cn_stock_portfolio_policy()
            policy.pop("risk_budget")
            config.write_text(json.dumps(policy), encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "Portfolio construction policy gate is not ready"):
                run_portfolio_construction_policy_gate_cli(config_path=config, output_dir=root / "output")


if __name__ == "__main__":
    unittest.main()
