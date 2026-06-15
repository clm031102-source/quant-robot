import unittest

from quant_robot.ops.residual_blocker_focus import build_residual_blocker_focus_pack


class ResidualBlockerFocusTests(unittest.TestCase):
    def test_focus_pack_prioritizes_residuals_and_links_work_items(self):
        projection = {
            "stage": "phase_4_12_pre_api_readiness_projection_pack",
            "safety": "Research only. Projection artifacts only; No broker connection, no account reads, no order placement, no live trading.",
            "boundary": {"would_cross_live_boundary": False, "broker_connection": "disabled", "order_placement": "disabled"},
            "projection_items": [
                {
                    "track_id": "data_quality",
                    "label": "Data quality",
                    "current_status": "block",
                    "projected_status": "block",
                    "current_evidence": "missing_date_rows=6",
                    "projected_evidence": "missing_date_rows=6",
                },
                {
                    "track_id": "data_gap_resolution",
                    "label": "Data gap resolution",
                    "current_status": "block",
                    "projected_status": "block",
                    "current_evidence": "blocking_gap_rows=6",
                    "projected_evidence": "blocking_gap_rows=4",
                },
                {
                    "track_id": "provider_readiness",
                    "label": "Provider readiness",
                    "current_status": "block",
                    "projected_status": "block",
                    "current_evidence": "ready_providers=0/4",
                    "projected_evidence": "ready_providers=0/4",
                },
                {
                    "track_id": "provider_remediation",
                    "label": "Provider remediation",
                    "current_status": "block",
                    "projected_status": "block",
                    "current_evidence": "blocking_remediation_items=7",
                    "projected_evidence": "blocking_remediation_items=3",
                },
                {
                    "track_id": "manual_review_gate",
                    "label": "Manual review gate",
                    "current_status": "block",
                    "projected_status": "block",
                    "current_evidence": "missing_dates_present, providers_not_ready_for_live_review",
                    "projected_evidence": "missing_dates_present, providers_not_ready_for_live_review",
                },
            ],
            "residual_rows": [
                {
                    "track_id": "data_gap_resolution",
                    "remaining_blockers": 4,
                    "projected_status": "block",
                    "source_stage": "phase_4_6_data_gap_resolution_rehearsal",
                    "local_only": True,
                },
                {
                    "track_id": "provider_remediation",
                    "remaining_blockers": 3,
                    "projected_status": "block",
                    "source_stage": "phase_4_11_provider_remediation_review_rehearsal",
                    "local_only": True,
                },
            ],
        }
        worklist = {
            "stage": "phase_4_1_blocker_resolution_worklist",
            "boundary": {"would_cross_live_boundary": False, "broker_connection": "disabled", "order_placement": "disabled"},
            "work_items": [
                {
                    "work_item_id": "WI-001",
                    "track_id": "data_quality",
                    "blocker_id": "data_quality_missing_dates",
                    "primary_command": "python scripts\\run_data_quality_audit.py",
                },
                {
                    "work_item_id": "WI-002",
                    "track_id": "data_gap_resolution",
                    "blocker_id": "data_gap_resolution_blocking_gaps",
                    "primary_command": "python scripts\\run_data_gap_resolution.py",
                },
                {
                    "work_item_id": "WI-003",
                    "track_id": "provider_readiness",
                    "blocker_id": "provider_readiness_not_ready",
                    "primary_command": "python scripts\\run_provider_evidence.py",
                },
                {
                    "work_item_id": "WI-004",
                    "track_id": "provider_remediation",
                    "blocker_id": "provider_remediation_items_open",
                    "primary_command": "python scripts\\run_provider_remediation.py",
                },
                {
                    "work_item_id": "WI-005",
                    "track_id": "manual_review_gate",
                    "blocker_id": "missing_dates_present",
                    "primary_command": "python scripts\\run_manual_review_rehearsal.py",
                },
                {
                    "work_item_id": "WI-006",
                    "track_id": "manual_review_gate",
                    "blocker_id": "providers_not_ready_for_live_review",
                    "primary_command": "python scripts\\run_manual_review_rehearsal.py",
                },
            ],
            "action_queue": [
                {"priority": 1, "track_id": "data_quality", "command": "python scripts\\run_data_quality_audit.py", "reason": "audit gaps"},
                {"priority": 2, "track_id": "data_gap_resolution", "command": "python scripts\\run_data_gap_resolution.py", "reason": "resolve gaps"},
                {"priority": 5, "track_id": "provider_readiness", "command": "python scripts\\run_provider_evidence.py", "reason": "provider evidence"},
                {"priority": 6, "track_id": "provider_remediation", "command": "python scripts\\run_provider_remediation.py", "reason": "provider remediation"},
                {"priority": 7, "track_id": "manual_review_gate", "command": "python scripts\\run_manual_review_rehearsal.py", "reason": "gate rehearsal"},
            ],
        }

        pack = build_residual_blocker_focus_pack(projection, worklist)

        self.assertEqual(pack["stage"], "phase_4_13_residual_blocker_focus_pack")
        self.assertEqual(pack["summary"]["root_focus_items"], 2)
        self.assertEqual(pack["summary"]["residual_blockers"], 7)
        self.assertEqual(pack["summary"]["downstream_waits"], 1)
        self.assertEqual(pack["summary"]["action_queue"], 4)
        self.assertFalse(pack["boundary"]["would_cross_live_boundary"])
        focus = {row["track_id"]: row for row in pack["focus_items"]}
        self.assertEqual(focus["data_gap_resolution"]["priority_rank"], 1)
        self.assertEqual(focus["data_gap_resolution"]["remaining_blockers"], 4)
        self.assertIn("WI-001", focus["data_gap_resolution"]["linked_work_item_ids"])
        self.assertIn("data_quality_missing_dates", focus["data_gap_resolution"]["blocker_ids"])
        self.assertEqual(focus["provider_remediation"]["priority_rank"], 2)
        self.assertIn("WI-003", focus["provider_remediation"]["linked_work_item_ids"])
        wait = pack["downstream_waits"][0]
        self.assertEqual(wait["track_id"], "manual_review_gate")
        self.assertIn("data_gap_resolution", wait["blocked_by_tracks"])
        self.assertIn("provider_remediation", wait["blocked_by_tracks"])
        self.assertIn("No broker", pack["safety"])
        self.assertIn("Residual Blocker Focus Pack", pack["markdown"])


if __name__ == "__main__":
    unittest.main()
