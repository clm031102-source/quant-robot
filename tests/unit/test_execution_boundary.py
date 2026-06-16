import unittest

from quant_robot.execution.boundary import (
    build_execution_boundary_status,
    build_manual_approval_packet,
    refuse_live_execution,
)


class ExecutionBoundaryTests(unittest.TestCase):
    def test_boundary_defaults_to_read_only_with_kill_switch_enabled(self):
        status = build_execution_boundary_status()

        self.assertFalse(status["live_order_allowed"])
        self.assertEqual(status["broker_connection"], "disabled")
        self.assertEqual(status["account_reads"], "disabled")
        self.assertEqual(status["order_placement"], "disabled")
        self.assertTrue(status["kill_switch_enabled"])

    def test_manual_approval_packet_is_not_executable(self):
        packet = build_manual_approval_packet(
            candidate={"case_id": "CN_ETF_liquidity_10_top1_cost5_reb5"},
            reviewer="operator",
        )

        self.assertEqual(packet["candidate"]["case_id"], "CN_ETF_liquidity_10_top1_cost5_reb5")
        self.assertTrue(packet["requires_manual_approval"])
        self.assertFalse(packet["executable"])
        self.assertFalse(packet["boundary"]["live_order_allowed"])

    def test_live_execution_is_refused(self):
        with self.assertRaisesRegex(PermissionError, "disabled"):
            refuse_live_execution({"asset_id": "CN_ETF_XSHG_510300", "quantity": 100})


if __name__ == "__main__":
    unittest.main()
