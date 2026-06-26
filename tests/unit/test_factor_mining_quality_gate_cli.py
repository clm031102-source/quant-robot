import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_factor_mining_quality_gate import run_factor_mining_quality_gate
from quant_robot.ops.factor_mining_quality_gate import required_control_ids


class FactorMiningQualityGateCliTests(unittest.TestCase):
    def test_cli_writes_json_and_markdown_for_classified_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "quality_gate_config.json"
            output_dir = root / "quality_gate_output"
            config_path.write_text(
                json.dumps(
                    {
                        "scope_id": "cn_stock_factor_mining_round142",
                        "market": "CN",
                        "asset_type": "stock",
                        "control_status": {control_id: "planned" for control_id in required_control_ids()},
                        "control_next_actions": {
                            control_id: f"finish {control_id}" for control_id in required_control_ids()
                        },
                    }
                ),
                encoding="utf-8",
            )

            packet = run_factor_mining_quality_gate(config_path=config_path, output_dir=output_dir)

            self.assertEqual(packet["status"], "classified")
            self.assertTrue(packet["decision"]["startup_gate_cleared"])
            self.assertFalse(packet["decision"]["promotion_gate_cleared"])
            self.assertTrue((output_dir / "factor_mining_quality_gate.json").exists())
            self.assertTrue((output_dir / "factor_mining_quality_gate.md").exists())
            markdown = (output_dir / "factor_mining_quality_gate.md").read_text(encoding="utf-8")
            self.assertIn("CN Stock Factor Mining Quality Gate", markdown)
            self.assertIn("cn_stock_tradeability", markdown)
            self.assertIn("strict_statistics", markdown)

    def test_default_quality_gate_config_is_runnable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet = run_factor_mining_quality_gate(output_dir=Path(tmp))

        self.assertEqual(packet["summary"]["scope_id"], "cn_stock_factor_mining_round142")
        self.assertEqual(packet["status"], "promotion_ready")
        self.assertTrue(packet["decision"]["startup_gate_cleared"])
        self.assertTrue(packet["decision"]["promotion_gate_cleared"])
        self.assertEqual(packet["summary"]["missing_controls"], 0)
        self.assertEqual(packet["summary"]["missing_evidence_controls"], 0)
        self.assertEqual(packet["summary"]["missing_next_action_controls"], 0)
        self.assertEqual(packet["summary"]["partial_controls"], 0)
        self.assertEqual(packet["summary"]["planned_controls"], 0)
        self.assertEqual(packet["summary"]["not_applicable_controls"], 1)
        self.assertEqual(packet["control_status"]["cn_etf_dedicated_signal_pack_for_etf_rotation"], "not_applicable")
        self.assertTrue(packet["research_execution_policy"]["direct_factor_generation_allowed"])
        self.assertEqual(packet["research_execution_policy"]["direct_mining_blockers"], [])

    def test_default_quality_gate_records_round205_regime_and_round206_event_controls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet = run_factor_mining_quality_gate(output_dir=Path(tmp))

        statuses = packet["control_status"]
        evidence = packet["control_evidence"]
        self.assertEqual(statuses["policy_liquidity_regime"], "implemented")
        self.assertEqual(statuses["credit_cycle_proxy"], "implemented")
        self.assertEqual(statuses["northbound_margin_turnover_temperature"], "implemented")
        self.assertEqual(statuses["earnings_forecast_events"], "implemented")
        self.assertEqual(statuses["dividend_ex_right_events"], "implemented")
        self.assertEqual(statuses["buyback_holder_change_unlock_events"], "implemented")
        self.assertEqual(statuses["cn_etf_dedicated_signal_pack_for_etf_rotation"], "not_applicable")
        self.assertIn("Round205", evidence["policy_liquidity_regime"])
        self.assertIn("SHIBOR", evidence["policy_liquidity_regime"])
        self.assertIn("Standalone policy-liquidity alpha claims are disallowed", evidence["policy_liquidity_regime"])
        self.assertIn("Round205", evidence["credit_cycle_proxy"])
        self.assertIn("regime-control layer", evidence["credit_cycle_proxy"])
        self.assertIn("not alpha promotion", evidence["credit_cycle_proxy"])
        self.assertIn("Round205", evidence["northbound_margin_turnover_temperature"])
        self.assertIn("Prior positive northbound accumulation alpha remains rejected", evidence["northbound_margin_turnover_temperature"])
        self.assertIn("Round206", evidence["earnings_forecast_events"])
        self.assertIn("hibernated event-control", evidence["earnings_forecast_events"])
        self.assertIn("controlled_retest_only", evidence["dividend_ex_right_events"])
        self.assertIn("coverage_blocked", evidence["buyback_holder_change_unlock_events"])
        self.assertEqual(packet["research_execution_policy"]["direct_mining_blockers"], [])
        self.assertTrue(packet["research_execution_policy"]["direct_factor_generation_allowed"])
        self.assertTrue(packet["decision"]["promotion_gate_cleared"])


if __name__ == "__main__":
    unittest.main()
