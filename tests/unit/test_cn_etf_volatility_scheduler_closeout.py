import json
import unittest
from pathlib import Path

from quant_robot.research.family_scheduler import build_research_family_schedule


class CnEtfVolatilitySchedulerCloseoutTests(unittest.TestCase):
    def test_margin_source_ready_opens_only_preregistration(self) -> None:
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
        self.assertEqual(structure["status"], "stop_lossed")
        self.assertEqual(structure["source_readiness_status"], "ready_for_preregistration")
        self.assertFalse(structure["preregistration_required"])
        self.assertFalse(structure["factor_batch_before_preregistration_allowed"])
        self.assertFalse(structure["single_prescreen_allowed"])
        self.assertFalse(structure["primary_allocation_allowed"])
        self.assertEqual(
            structure["preregistration_status"],
            "prescreen_completed_rejected",
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
        option = families["cn_etf_option_sentiment"]
        self.assertEqual(option["status"], "exploratory")
        self.assertEqual(option["budget_share"], 0.0)
        self.assertEqual(option["source_readiness_status"], "blocked")
        self.assertEqual(option["source_audit"]["underlying_count"], 9)
        self.assertEqual(option["source_audit"]["probe_count"], 5)
        self.assertFalse(option["factor_batch_before_readiness_allowed"])
        self.assertFalse(option["primary_allocation_allowed"])
        margin = families["cn_etf_margin_positioning"]
        self.assertEqual(margin["status"], "exploratory")
        self.assertEqual(margin["budget_share"], 0.0)
        self.assertEqual(
            margin["source_readiness_status"],
            "ready_for_margin_positioning_preregistration",
        )
        self.assertTrue(margin["preregistration_required"])
        self.assertFalse(margin["factor_batch_before_preregistration_allowed"])
        self.assertFalse(margin["primary_allocation_allowed"])
        self.assertEqual(margin["source_audit"]["rows"], 199793)
        self.assertEqual(margin["source_audit"]["assets"], 410)
        decision = config["last_decision"]
        self.assertEqual(
            decision["source_stage"],
            "cn_etf_margin_positioning_source_readiness",
        )
        self.assertEqual(
            decision["decision"],
            "source_ready_preregistration_required_no_factor_batch",
        )
        self.assertEqual(
            decision["source_config_sha256"],
            "0b0760536cd779e90bc9b4af607ef6ce0441f9f948369006dedcbbbb47c30c22",
        )
        self.assertEqual(
            decision["source_result_sha256"],
            "8c61c7b147046bfd6c4a33f832e8c77bcd732d51b52c98b0aa9be5a6e0a3f2d5",
        )
        self.assertFalse(decision["factor_batch_allowed"])
        self.assertTrue(decision["preregistration_required"])
        self.assertEqual(decision["rows"], 199793)
        self.assertEqual(decision["assets"], 410)
        self.assertEqual(decision["analysis_sessions"], 1087)
        self.assertEqual(decision["qualifying_dates"], 1085)
        for boundary in (
            "factor_generation_allowed",
            "forward_return_read",
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
        option_decision = config["prior_option_source_blocked_decision"]
        self.assertEqual(
            option_decision["source_stage"],
            "cn_etf_option_sentiment_source_readiness",
        )
        self.assertEqual(option_decision["underlying_count"], 9)
        closeout = config["prior_fund_structure_closeout_decision"]
        self.assertEqual(
            closeout["source_stage"],
            "cn_etf_fund_structure_crowding_prescreen",
        )
        self.assertEqual(closeout["execution_count"], 1)
        self.assertFalse(closeout["primary_passed"])
        self.assertTrue(closeout["diagnostic_passed"])
        self.assertAlmostEqual(
            closeout["primary_net_spread_10bps"],
            0.0010780130212781924,
        )
        self.assertEqual(
            config["prior_fund_structure_source_ready_decision"]["share_rows"],
            645645,
        )
        self.assertEqual(
            config["prior_fund_structure_preregistration_decision"]["execution_count"],
            0,
        )
        self.assertEqual(
            config["prior_dynamic_peer_closeout_decision"]["decision"],
            "prescreen_rejected_family_rotation_review_only",
        )


if __name__ == "__main__":
    unittest.main()
