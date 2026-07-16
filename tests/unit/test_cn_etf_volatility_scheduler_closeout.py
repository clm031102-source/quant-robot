import json
import unittest
from pathlib import Path

from quant_robot.research.family_scheduler import build_research_family_schedule


class CnEtfVolatilitySchedulerCloseoutTests(unittest.TestCase):
    def test_dynamic_peer_readiness_allows_only_preregistration(self) -> None:
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
            "cn_etf_dynamic_comovement_peer_readiness",
        )
        self.assertEqual(
            decision["decision"],
            "source_ready_preregistration_required_no_factor_batch",
        )
        self.assertEqual(
            decision["source_status"],
            "ready_for_peer_source_preregistration",
        )
        self.assertFalse(decision["factor_batch_allowed"])
        self.assertEqual(decision["unallocated_budget_share"], 1.0)


if __name__ == "__main__":
    unittest.main()
