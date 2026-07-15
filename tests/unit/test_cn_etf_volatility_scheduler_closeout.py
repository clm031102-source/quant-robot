import json
import unittest
from pathlib import Path

from quant_robot.research.family_scheduler import build_research_family_schedule


class CnEtfVolatilitySchedulerCloseoutTests(unittest.TestCase):
    def test_zero_lead_contract_closes_volatility_and_activates_peer_relative_value(self) -> None:
        config = json.loads(
            Path("configs/research_family_scheduler_cn_etf.json").read_text(encoding="utf-8")
        )

        schedule = build_research_family_schedule(config)
        families = {row["family_id"]: row for row in schedule["families"]}

        self.assertEqual(schedule["summary"]["scheduler_status"], "ready")
        self.assertEqual(schedule["summary"]["active_primary_families"], 3)
        self.assertAlmostEqual(schedule["summary"]["primary_budget_share"], 1.0)
        volatility = families["cn_etf_volatility_regime"]
        self.assertEqual(volatility["status"], "stop_lossed")
        self.assertEqual(volatility["budget_share"], 0.0)
        self.assertFalse(volatility["primary_allocation_allowed"])
        self.assertFalse(volatility["sign_flip_rescue_allowed"])
        self.assertFalse(volatility["window_tuning_allowed"])
        self.assertIn("residual_volatility_retry", volatility["forbidden_actions"])
        self.assertEqual(families["cn_etf_flow_breadth_aggregation"]["budget_share"], 0.35)
        self.assertEqual(families["cn_etf_fund_structure"]["budget_share"], 0.35)
        peer = families["cn_etf_peer_relative_value"]
        self.assertEqual(peer["status"], "exploratory")
        self.assertEqual(peer["budget_share"], 0.30)
        self.assertTrue(peer["metadata_readiness_review_required"])
        self.assertFalse(peer["factor_batch_before_readiness_allowed"])
        peer_actions = [
            row for row in schedule["next_actions"] if row.get("family_id") == "cn_etf_peer_relative_value"
        ]
        self.assertEqual(len(peer_actions), 1)
        self.assertEqual(peer_actions[0]["action"], "run_metadata_readiness_review")
        self.assertNotIn(
            "cn_etf_peer_relative_value",
            {
                row.get("family_id")
                for row in schedule["next_actions"]
                if row.get("action") == "run_active_family_batch"
            },
        )
        decision = config["last_decision"]
        self.assertEqual(decision["source_stage"], "cn_etf_market_residual_volatility_prescreen")
        self.assertEqual(decision["research_lead_count"], 0)
        self.assertEqual(decision["closed_family"], "cn_etf_volatility_regime")
        self.assertEqual(decision["activated_family"], "cn_etf_peer_relative_value")


if __name__ == "__main__":
    unittest.main()
