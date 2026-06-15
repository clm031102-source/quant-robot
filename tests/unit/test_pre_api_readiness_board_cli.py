import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_pre_api_readiness_board import run_pre_api_readiness_board


class PreApiReadinessBoardCliTests(unittest.TestCase):
    def test_run_pre_api_readiness_board_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            review_path = root / "promotion_review_packet.json"
            review_path.write_text(
                json.dumps(
                    {
                        "selected_candidate": {"case_id": "case_a", "promotion_status": "paper_ready"},
                        "manual_review_gate": {"allowed": False, "reasons": ["manual_live_review_not_enabled"]},
                        "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
                    }
                ),
                encoding="utf-8",
            )
            data_quality_path = root / "data_quality_gap_audit.json"
            data_quality_path.write_text(json.dumps({"summary": {"missing_date_rows": 0}}), encoding="utf-8")
            data_gap_resolution_path = root / "data_gap_resolution_ledger.json"
            data_gap_resolution_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "gap_rows": 1,
                            "blocking_gap_rows": 1,
                            "blocks_api_boundary": True,
                            "needs_review": 1,
                        }
                    }
                ),
                encoding="utf-8",
            )
            provider_path = root / "provider_evidence_pack.json"
            provider_path.write_text(json.dumps({"summary": {"providers": 1, "ready_providers": 1, "parquet_ready": True}}), encoding="utf-8")
            provider_remediation_path = root / "provider_remediation_matrix.json"
            provider_remediation_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "remediation_items": 2,
                            "dependency_items": 1,
                            "credential_items": 1,
                            "adapter_items": 0,
                            "storage_items": 0,
                            "blocks_api_boundary": True,
                        }
                    }
                ),
                encoding="utf-8",
            )
            paper_path = root / "paper_observation_pack.json"
            paper_path.write_text(json.dumps({"summary": {"observed_candidates": 1, "completed_candidates": 1}}), encoding="utf-8")
            duplicate_path = root / "duplicate_canonical_registry.json"
            duplicate_path.write_text(json.dumps({"summary": {"duplicate_members": 0, "clusters": 0}}), encoding="utf-8")
            rehearsal_path = root / "manual_review_rehearsal.json"
            rehearsal_path.write_text(
                json.dumps(
                    {
                        "gate_status": "blocked",
                        "blockers": ["manual_live_review_not_enabled"],
                        "dry_run": {"would_cross_live_boundary": False, "order_placement": "disabled"},
                    }
                ),
                encoding="utf-8",
            )
            refresh_path = root / "evidence_refresh_plan.json"
            refresh_path.write_text(json.dumps({"refresh_status": "action_required", "ordered_actions": []}), encoding="utf-8")
            output_dir = root / "pre_api_readiness_board"

            board = run_pre_api_readiness_board(
                review_packet=review_path,
                data_quality=data_quality_path,
                data_gap_resolution=data_gap_resolution_path,
                provider_evidence=provider_path,
                provider_remediation=provider_remediation_path,
                paper_observation=paper_path,
                duplicate_registry=duplicate_path,
                manual_rehearsal=rehearsal_path,
                evidence_refresh=refresh_path,
                output_dir=output_dir,
            )

            self.assertEqual(board["stage"], "phase_4_0_pre_api_readiness_board")
            self.assertTrue((output_dir / "pre_api_readiness_board.json").exists())
            self.assertTrue((output_dir / "pre_api_readiness_board.md").exists())
            self.assertTrue((output_dir / "pre_api_readiness_items.csv").exists())
            self.assertTrue((output_dir / "pre_api_blockers.csv").exists())
            self.assertTrue((output_dir / "pre_api_next_actions.csv").exists())
            payload = json.loads((output_dir / "pre_api_readiness_board.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["boundary"]["order_placement"], "disabled")
            tracks = {item["track_id"]: item for item in payload["readiness_items"]}
            self.assertEqual(tracks["data_gap_resolution"]["status"], "block")
            self.assertEqual(tracks["provider_remediation"]["status"], "block")
            self.assertIn("remediation_items=2", tracks["provider_remediation"]["evidence"])


if __name__ == "__main__":
    unittest.main()
