import json
import unittest
from pathlib import Path

from quant_robot.research.family_scheduler import build_research_family_schedule


class CnEtfVolatilitySchedulerCloseoutTests(unittest.TestCase):
    def test_fund_structure_preregistration_opens_only_one_prescreen(self) -> None:
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
        self.assertEqual(structure["source_readiness_status"], "ready_for_preregistration")
        self.assertFalse(structure["preregistration_required"])
        self.assertFalse(structure["factor_batch_before_preregistration_allowed"])
        self.assertTrue(structure["single_prescreen_allowed"])
        self.assertEqual(
            structure["preregistration_status"],
            "preregistered_single_prescreen",
        )
        self.assertEqual(structure["source_audit"]["share_rows"], 645645)
        self.assertEqual(structure["source_audit"]["share_assets"], 1023)
        self.assertEqual(structure["source_audit"]["analysis_sessions"], 1085)
        self.assertAlmostEqual(
            structure["source_audit"]["nav_intersection_coverage"],
            0.994795901772646,
        )
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
        self.assertEqual(dynamic_peer["status"], "stop_lossed")
        self.assertEqual(dynamic_peer["budget_share"], 0.0)
        self.assertEqual(
            dynamic_peer["source_readiness_status"],
            "ready_for_peer_source_preregistration",
        )
        self.assertTrue(dynamic_peer["preregistration_required"])
        self.assertFalse(dynamic_peer["factor_batch_before_preregistration_allowed"])
        self.assertEqual(
            dynamic_peer["preregistration_status"],
            "prescreen_completed_rejected",
        )
        self.assertFalse(dynamic_peer["single_prescreen_allowed"])
        self.assertFalse(dynamic_peer["portfolio_grid_allowed"])
        self.assertFalse(dynamic_peer["walk_forward_allowed"])
        self.assertFalse(dynamic_peer["final_holdout_allowed"])
        self.assertFalse(dynamic_peer["primary_allocation_allowed"])
        self.assertEqual(
            dynamic_peer["prescreen_audit"]["result_sha256"],
            "3cadcd4755947e1837894c25c87f7455a17bc603f416a551b9b12aed55b4c813",
        )
        self.assertFalse(dynamic_peer["prescreen_audit"]["primary_passed"])
        self.assertEqual(dynamic_peer["prescreen_audit"]["primary_horizon"], 5)
        self.assertAlmostEqual(
            dynamic_peer["prescreen_audit"]["primary_mean_rank_ic"],
            0.004539414303968358,
        )
        self.assertAlmostEqual(
            dynamic_peer["prescreen_audit"]["primary_net_spread_10bps"],
            -0.0006844061631389568,
        )
        self.assertFalse(dynamic_peer["prescreen_audit"]["diagnostic_passed"])
        self.assertEqual(dynamic_peer["preregistration_audit"]["execution_count"], 1)
        self.assertEqual(dynamic_peer["source_audit"]["mapping_rows"], 20301)
        self.assertEqual(dynamic_peer["source_audit"]["qualifying_dates"], 904)
        self.assertAlmostEqual(
            dynamic_peer["source_audit"]["qualifying_date_coverage"],
            0.8331797235023042,
        )
        decision = config["last_decision"]
        self.assertEqual(
            decision["source_stage"],
            "cn_etf_fund_structure_crowding_preregistration",
        )
        self.assertEqual(
            decision["decision"],
            "prescreen_preregistered_single_batch_only",
        )
        self.assertEqual(
            decision["source_config_sha256"],
            "04cb2acc675762f04c109798949d2b174fb1c9c72a9d91497423837f366a0ba3",
        )
        self.assertEqual(
            decision["source_result_sha256"],
            "3ccb5ba4d04ff24b7b5ef81c2984f1571a0a23cd41f077c7b20ae688879f3a13",
        )
        self.assertEqual(
            decision["factor_name"],
            "etf_residual_share_creation_crowding_reversal_20",
        )
        self.assertEqual(decision["execution_count"], 0)
        self.assertTrue(decision["factor_batch_allowed"])
        self.assertTrue(decision["single_prescreen_allowed"])
        self.assertFalse(decision["preregistration_required"])
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
            config["prior_fund_structure_source_ready_decision"]["share_rows"],
            645645,
        )
        self.assertEqual(
            config["prior_dynamic_peer_closeout_decision"]["decision"],
            "prescreen_rejected_family_rotation_review_only",
        )


if __name__ == "__main__":
    unittest.main()
