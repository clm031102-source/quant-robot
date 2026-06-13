import unittest

from quant_robot.ops.readiness_projection import build_readiness_projection_pack


class ReadinessProjectionTests(unittest.TestCase):
    def test_projection_pack_combines_board_and_rehearsal_reductions(self):
        board = {
            "stage": "phase_4_0_pre_api_readiness_board",
            "overall_status": "blocked",
            "summary": {"blockers": 4, "blocked": 2, "warnings": 0, "passed": 1},
            "boundary": {"would_cross_live_boundary": False, "broker_connection": "disabled", "order_placement": "disabled"},
            "readiness_items": [
                {"track_id": "data_gap_resolution", "label": "Data gap resolution", "status": "block", "evidence": "blocking_gap_rows=6"},
                {"track_id": "provider_remediation", "label": "Provider remediation", "status": "block", "evidence": "blocking_remediation_items=7"},
                {"track_id": "paper_observation", "label": "Paper observation", "status": "pass", "evidence": "observed=1"},
            ],
        }
        data_gap_rehearsal = {
            "stage": "phase_4_6_data_gap_resolution_rehearsal",
            "summary": {"source_blocking_gap_rows": 6, "rehearsed_blocking_gap_rows": 4, "blocker_delta": 2},
            "readiness_projection": {"track_id": "data_gap_resolution", "status": "block", "evidence": "blocking_gap_rows=4"},
        }
        provider_rehearsal = {
            "stage": "phase_4_11_provider_remediation_review_rehearsal",
            "summary": {
                "source_blocking_remediation_items": 7,
                "rehearsed_blocking_remediation_items": 3,
                "blocker_delta": 4,
            },
            "readiness_projection": {
                "track_id": "provider_remediation",
                "status": "block",
                "evidence": "blocking_remediation_items=3",
            },
        }

        pack = build_readiness_projection_pack(board, data_gap_rehearsal, provider_rehearsal)

        self.assertEqual(pack["stage"], "phase_4_12_pre_api_readiness_projection_pack")
        self.assertEqual(pack["summary"]["current_blockers"], 4)
        self.assertEqual(pack["summary"]["total_rehearsal_delta"], 6)
        self.assertEqual(pack["summary"]["projected_blocked_items"], 2)
        self.assertFalse(pack["boundary"]["would_cross_live_boundary"])
        deltas = {row["track_id"]: row for row in pack["delta_rows"]}
        self.assertEqual(deltas["data_gap_resolution"]["blocker_delta"], 2)
        self.assertEqual(deltas["provider_remediation"]["blocker_delta"], 4)
        residuals = {row["track_id"]: row for row in pack["residual_rows"]}
        self.assertEqual(residuals["data_gap_resolution"]["remaining_blockers"], 4)
        self.assertEqual(residuals["provider_remediation"]["remaining_blockers"], 3)
        items = {row["track_id"]: row for row in pack["projection_items"]}
        self.assertEqual(items["provider_remediation"]["projected_evidence"], "blocking_remediation_items=3")
        self.assertIn("No broker", pack["safety"])
        self.assertIn("total rehearsal delta", pack["markdown"])


if __name__ == "__main__":
    unittest.main()
