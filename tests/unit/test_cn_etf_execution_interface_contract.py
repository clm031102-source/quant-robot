import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.cn_etf_execution_interface_contract import (
    build_cn_etf_execution_interface_contract_readiness,
)
from scripts.run_cn_etf_execution_interface_contract_readiness import (
    run_cn_etf_execution_interface_contract_readiness_cli,
)


CONFIG_PATH = "configs/cn_etf_execution_interface_contract_20260729.json"


class CnEtfExecutionInterfaceContractTests(unittest.TestCase):
    def test_schema_is_ready_while_every_external_action_remains_disabled(self):
        config = json.loads(open(CONFIG_PATH, encoding="utf-8").read())

        result = build_cn_etf_execution_interface_contract_readiness(config)

        self.assertEqual(result["status"], "schema_ready_execution_disabled")
        self.assertEqual(result["blockers"], [])
        self.assertTrue(result["schema_validation_allowed"])
        self.assertFalse(result["broker_connection_allowed"])
        self.assertFalse(result["account_read_allowed"])
        self.assertFalse(result["order_placement_allowed"])
        self.assertFalse(result["live_boundary_allowed"])
        self.assertEqual(
            result["risk_contract"]["capital_cny"],
            {"minimum": 1000, "maximum": 3000},
        )
        self.assertEqual(result["risk_contract"]["max_single_position_cny"], 1000)
        self.assertEqual(result["paper_gates"]["minimum_days"], 20)
        self.assertEqual(result["paper_gates"]["minimum_fills"], 30)
        self.assertEqual(result["paper_gates"]["minimum_market_regimes"], 2)

    def test_any_enabled_external_boundary_blocks_the_contract(self):
        config = json.loads(open(CONFIG_PATH, encoding="utf-8").read())
        for boundary in (
            "broker_connection_allowed",
            "account_read_allowed",
            "order_placement_allowed",
            "live_boundary_allowed",
        ):
            with self.subTest(boundary=boundary):
                changed = json.loads(json.dumps(config))
                changed["boundaries"][boundary] = True

                result = build_cn_etf_execution_interface_contract_readiness(changed)

                self.assertEqual(result["status"], "blocked")
                self.assertIn(f"boundary_enabled:{boundary}", result["blockers"])

    def test_missing_idempotency_and_kill_switch_fields_block_the_contract(self):
        config = json.loads(open(CONFIG_PATH, encoding="utf-8").read())
        config["order_intent_schema"]["required_fields"].remove("idempotency_key")
        config["risk_controls"]["kill_switch_required"] = False

        result = build_cn_etf_execution_interface_contract_readiness(config)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("order_intent_schema_mismatch", result["blockers"])
        self.assertIn("kill_switch_not_required", result["blockers"])

    def test_weakened_instrument_or_order_controls_block_the_contract(self):
        config = json.loads(open(CONFIG_PATH, encoding="utf-8").read())
        config["market_contract"]["instrument_metadata_required"].remove(
            "trade_status"
        )
        config["order_intent_schema"]["allowed_order_types"].append("MARKET")
        config["order_intent_schema"]["default_time_in_force"] = "GTC"

        result = build_cn_etf_execution_interface_contract_readiness(config)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("instrument_metadata_contract_mismatch", result["blockers"])
        self.assertIn("order_control_contract_mismatch", result["blockers"])

    def test_cli_writes_only_a_local_disabled_readiness_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cn_etf_execution_interface_contract_readiness_cli(
                config_path=CONFIG_PATH,
                output_dir=Path(tmp) / "output",
            )

            self.assertEqual(result["status"], "schema_ready_execution_disabled")
            self.assertFalse(result["broker_connection_allowed"])
            self.assertFalse(result["account_read_allowed"])
            self.assertFalse(result["order_placement_allowed"])
            self.assertTrue(Path(result["artifacts"]["json"]).is_file())
            self.assertTrue(Path(result["artifacts"]["markdown"]).is_file())


if __name__ == "__main__":
    unittest.main()
