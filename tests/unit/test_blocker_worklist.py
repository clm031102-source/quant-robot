import unittest

from quant_robot.ops.blocker_worklist import build_blocker_worklist


class BlockerWorklistTests(unittest.TestCase):
    def test_worklist_turns_readiness_board_into_open_local_work_items(self):
        board = {
            "stage": "phase_4_0_pre_api_readiness_board",
            "overall_status": "blocked",
            "selected_candidate": {"case_id": "case_a"},
            "boundary": {"would_cross_live_boundary": False, "broker_connection": "disabled", "order_placement": "disabled"},
            "blocker_register": [
                {
                    "blocker_id": "data_quality_missing_dates",
                    "track_id": "data_quality",
                    "severity": "block",
                    "evidence": "missing_date_rows=6",
                    "recommended_command": "python scripts\\run_data_quality_audit.py",
                },
                {
                    "blocker_id": "provider_readiness_not_ready",
                    "track_id": "provider_readiness",
                    "severity": "block",
                    "evidence": "ready_providers=0/4",
                    "recommended_command": "python scripts\\run_provider_evidence.py",
                },
            ],
            "next_local_actions": [
                {"priority": 1, "track_id": "data_quality", "command": "python scripts\\run_data_quality_audit.py", "reason": "audit gaps"},
                {"priority": 2, "track_id": "provider_readiness", "command": "python scripts\\run_provider_evidence.py", "reason": "audit providers"},
            ],
        }

        worklist = build_blocker_worklist(board)

        self.assertEqual(worklist["stage"], "phase_4_1_blocker_resolution_worklist")
        self.assertEqual(worklist["summary"]["open_work_items"], 2)
        self.assertFalse(worklist["boundary"]["would_cross_live_boundary"])
        self.assertEqual(worklist["work_items"][0]["work_status"], "open")
        self.assertEqual(worklist["work_items"][0]["blocker_id"], "data_quality_missing_dates")
        self.assertEqual(worklist["work_items"][0]["primary_command"], "python scripts\\run_data_quality_audit.py")
        self.assertEqual(worklist["action_queue"][0]["command"], "python scripts\\run_data_quality_audit.py")
        self.assertIn("data_quality_missing_dates", worklist["markdown"])
        self.assertIn("No broker", worklist["safety"])


if __name__ == "__main__":
    unittest.main()
