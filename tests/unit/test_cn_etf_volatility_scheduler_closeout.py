import json
import unittest
from pathlib import Path

from quant_robot.research.family_scheduler import build_research_family_schedule


class CnEtfVolatilitySchedulerCloseoutTests(unittest.TestCase):
    def test_dynamic_peer_preregistration_allows_only_one_scoped_prescreen(self) -> None:
        config = json.loads(
            Path("configs/research_family_scheduler_cn_etf.json").read_text(encoding="utf-8")
        )

        schedule = build_research_family_schedule(config)
        families = {row["family_id"]: row for row in schedule["families"]}

        self.assertEqual(schedule["summary"]["scheduler_status"], "blocked")
        self.assertEqual(schedule["summary"]["active_primary_families"], 0)
        self.assertAlmostEqual(schedule["summary"]["primary_budget_share"], 0.0)
        self.assertIn("insufficient_active_research_families", schedule["blockers"])
        volatility = families["cn_etf_volatility_regime"]
        self.assertEqual(volatility["status"], "stop_lossed")
        self.assertEqual(volatility["budget_share"], 0.0)
        self.assertFalse(volatility["primary_allocation_allowed"])
        self.assertFalse(volatility["sign_flip_rescue_allowed"])
        self.assertFalse(volatility["window_tuning_allowed"])
        self.assertIn("residual_volatility_retry", volatility["forbidden_actions"])
        flow = families["cn_etf_flow_breadth_aggregation"]
        structure = families["cn_etf_fund_structure"]
        self.assertEqual(flow["budget_share"], 0.0)
        self.assertEqual(structure["budget_share"], 0.0)
        self.assertEqual(flow["source_readiness_status"], "blocked")
        self.assertEqual(structure["source_readiness_status"], "blocked")
        peer = families["cn_etf_peer_relative_value"]
        self.assertEqual(peer["status"], "exploratory")
        self.assertEqual(peer["budget_share"], 0.0)
        self.assertEqual(peer["metadata_readiness_status"], "blocked")
        self.assertFalse(peer["metadata_readiness_review_required"])
        self.assertFalse(peer["factor_batch_before_readiness_allowed"])
        peer_actions = [
            row for row in schedule["next_actions"] if row.get("family_id") == "cn_etf_peer_relative_value"
        ]
        self.assertEqual(peer_actions, [])
        self.assertNotIn(
            "cn_etf_peer_relative_value",
            {
                row.get("family_id")
                for row in schedule["next_actions"]
                if row.get("action") == "run_active_family_batch"
            },
        )
        dynamic_peer = families["cn_etf_dynamic_comovement_peer_dislocation"]
        self.assertEqual(dynamic_peer["status"], "exploratory")
        self.assertEqual(dynamic_peer["budget_share"], 0.0)
        self.assertEqual(
            dynamic_peer["source_readiness_status"],
            "ready_for_peer_source_preregistration",
        )
        self.assertTrue(dynamic_peer["preregistration_required"])
        self.assertFalse(dynamic_peer["factor_batch_before_preregistration_allowed"])
        self.assertEqual(
            dynamic_peer["preregistration_status"],
            "preregistered_single_prescreen",
        )
        self.assertTrue(dynamic_peer["single_prescreen_allowed"])
        self.assertFalse(dynamic_peer["portfolio_grid_allowed"])
        self.assertFalse(dynamic_peer["walk_forward_allowed"])
        self.assertFalse(dynamic_peer["final_holdout_allowed"])
        self.assertFalse(dynamic_peer["primary_allocation_allowed"])
        self.assertEqual(dynamic_peer["source_audit"]["mapping_rows"], 20301)
        self.assertEqual(dynamic_peer["source_audit"]["qualifying_dates"], 904)
        self.assertAlmostEqual(
            dynamic_peer["source_audit"]["qualifying_date_coverage"],
            0.8331797235023042,
        )
        decision = config["last_decision"]
        self.assertEqual(
            decision["source_stage"],
            "cn_etf_dynamic_peer_dislocation_preregistration",
        )
        self.assertEqual(
            decision["decision"],
            "prescreen_preregistered_single_batch_only",
        )
        self.assertEqual(
            decision["factor_name"],
            "etf_dynamic_peer_residual_dislocation_reversal_5_60",
        )
        self.assertEqual(
            decision["preregistration_config_sha256"],
            "4811e1497bbfe9688e006dcb7764381c7ea977ddfde79790248f0223996233c6",
        )
        self.assertEqual(
            decision["preregistration_result_sha256"],
            "2038a32fa9b250a33a76bdca08c204a349a1cdec959fc3c10dbe4b6a4f6440f5",
        )
        self.assertEqual(
            decision["authorization_sha256"],
            "d5bea41ac87cd54b3c98adca3f815bf67d8d3b6f9a77798287dce9ed4635d659",
        )
        self.assertEqual(decision["hypothesis_count"], 2)
        self.assertEqual(decision["single_prescreen_run_limit"], 1)
        self.assertEqual(decision["execution_count"], 0)
        self.assertTrue(decision["execution_ledger_required"])
        self.assertTrue(decision["factor_batch_allowed"])
        self.assertTrue(decision["single_prescreen_allowed"])
        for boundary in (
            "portfolio_grid_allowed",
            "walk_forward_allowed",
            "final_holdout_allowed",
            "promotion_allowed",
            "paper_signal_allowed",
            "broker_connection_allowed",
            "account_read_allowed",
            "order_placement_allowed",
            "live_boundary_allowed",
        ):
            self.assertFalse(decision[boundary])
        self.assertEqual(decision["unallocated_budget_share"], 1.0)
        self.assertEqual(
            config["previous_decision"]["decision"],
            "source_ready_preregistration_required_no_factor_batch",
        )


if __name__ == "__main__":
    unittest.main()
