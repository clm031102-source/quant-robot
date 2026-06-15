import unittest

from quant_robot.ops.observation_sufficiency import build_observation_sufficiency_pack


class ObservationSufficiencyTests(unittest.TestCase):
    def test_minimum_fills_block_recommends_extending_observation_window(self):
        post_refresh = {
            "stage": "phase_5_8_post_refresh_replay",
            "status": "replay_blocked",
            "recent_data_refresh": {
                "target_window": {"start_date": "2026-05-23", "end_date": "2026-06-14"},
                "output_dir": "data/processed/tushare_etf_recent_fixture",
            },
            "decision": {"blockers": ["minimum_fills_observed"]},
            "profile_observation_output_dir": "data/reports/post_refresh_replay_fixture/profile_observation",
        }
        observation = {
            "stage": "phase_5_6_profile_observation_ledger",
            "run_date": "2026-06-14",
            "decision": {"stop_reasons": ["minimum_fills_observed"]},
            "observation_window": {"start_date": "2026-05-28", "end_date": "2026-06-13"},
            "stop_rules": [
                {"rule_id": "minimum_fills_observed", "status": "stop", "observed_value": 2, "threshold": 20},
            ],
            "ledger": [{"fills": 2, "risk_tier": "aggressive_growth"}],
        }

        pack = build_observation_sufficiency_pack(post_refresh, profile_observation_pack=observation)

        self.assertEqual(pack["stage"], "phase_5_9_observation_sufficiency")
        self.assertEqual(pack["status"], "needs_more_observation_data")
        self.assertEqual(pack["fills"]["observed_fills"], 2)
        self.assertEqual(pack["fills"]["required_fills"], 20)
        self.assertEqual(pack["fills"]["fill_deficit"], 18)
        self.assertGreaterEqual(pack["recommendation"]["estimated_total_observation_days"], 170)
        self.assertEqual(pack["recommendation"]["priority"], "extend_recent_data_window")
        self.assertFalse(pack["recommendation"]["threshold_relaxation_allowed"])
        self.assertEqual(pack["next_actions"][0]["action"], "extend_recent_refresh_window")

    def test_sufficient_observation_keeps_threshold_policy_intact(self):
        post_refresh = {
            "stage": "phase_5_8_post_refresh_replay",
            "status": "completed",
            "decision": {"blockers": []},
            "recent_data_refresh": {"target_window": {"end_date": "2026-06-14"}},
        }
        observation = {
            "stage": "phase_5_6_profile_observation_ledger",
            "run_date": "2026-06-14",
            "decision": {"paper_observation_allowed": True, "stop_reasons": []},
            "observation_window": {"start_date": "2026-01-01", "end_date": "2026-06-14"},
            "stop_rules": [
                {"rule_id": "minimum_fills_observed", "status": "pass", "observed_value": 30, "threshold": 20},
            ],
        }

        pack = build_observation_sufficiency_pack(post_refresh, profile_observation_pack=observation)

        self.assertEqual(pack["status"], "sufficient")
        self.assertTrue(pack["decision"]["observation_sufficiency_cleared"])
        self.assertEqual(pack["recommendation"]["priority"], "continue_paper_observation")
        self.assertFalse(pack["recommendation"]["threshold_relaxation_allowed"])


if __name__ == "__main__":
    unittest.main()
