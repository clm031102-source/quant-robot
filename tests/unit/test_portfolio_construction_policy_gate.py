import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.portfolio_construction_policy_gate import (
    build_portfolio_construction_policy_gate,
    default_cn_stock_portfolio_policy,
    render_portfolio_construction_policy_gate_markdown,
    write_portfolio_construction_policy_gate,
)


class PortfolioConstructionPolicyGateTests(unittest.TestCase):
    def test_default_policy_passes_with_all_user_required_controls_and_metrics(self) -> None:
        result = build_portfolio_construction_policy_gate(default_cn_stock_portfolio_policy())

        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["summary"]["missing_required_controls"], [])
        self.assertEqual(result["summary"]["invalid_policy_items"], [])
        for control in [
            "risk_budget_position_sizing",
            "volatility_targeting",
            "industry_weight_constraints",
            "turnover_constraints",
            "stop_loss_or_de_risk_rules",
        ]:
            self.assertEqual(result["control_status"][control], "implemented")
        for metric in [
            "total_return",
            "annual_return",
            "sharpe",
            "cost_adjusted_sharpe",
            "max_drawdown",
            "win_rate",
            "turnover",
            "capacity_usage",
        ]:
            self.assertIn(metric, result["required_metric_pack"])
        self.assertAlmostEqual(result["policy"]["drawdown_controls"]["max_drawdown_soft_tolerance"], 0.30)

    def test_blocks_missing_industry_constraints_and_invalid_drawdown_policy(self) -> None:
        policy = default_cn_stock_portfolio_policy()
        policy.pop("industry_constraints")
        policy["drawdown_controls"]["max_drawdown_soft_tolerance"] = 0.75

        result = build_portfolio_construction_policy_gate(policy)

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("industry_weight_constraints", result["summary"]["missing_required_controls"])
        self.assertIn("max_drawdown_soft_tolerance_out_of_range", result["summary"]["invalid_policy_items"])
        self.assertEqual(result["control_status"]["industry_weight_constraints"], "missing")
        self.assertEqual(result["control_status"]["stop_loss_or_de_risk_rules"], "invalid")

    def test_blocks_turnover_policy_without_cost_degradation_limit(self) -> None:
        policy = default_cn_stock_portfolio_policy()
        policy["turnover_controls"].pop("max_cost_degradation_pct")

        result = build_portfolio_construction_policy_gate(policy)

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("turnover_constraints", result["summary"]["missing_required_controls"])
        self.assertEqual(result["control_status"]["turnover_constraints"], "missing")

    def test_write_outputs(self) -> None:
        result = build_portfolio_construction_policy_gate(default_cn_stock_portfolio_policy())

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_portfolio_construction_policy_gate(output_dir, result)

            self.assertTrue((output_dir / "portfolio_construction_policy_gate.json").exists())
            self.assertTrue((output_dir / "portfolio_construction_policy_gate.md").exists())
            markdown = render_portfolio_construction_policy_gate_markdown(result)
            self.assertIn("Portfolio Construction Policy Gate", markdown)
            self.assertIn("Passes: True", markdown)


if __name__ == "__main__":
    unittest.main()
