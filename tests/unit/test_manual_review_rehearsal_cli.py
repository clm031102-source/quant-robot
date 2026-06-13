import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_manual_review_rehearsal import run_manual_review_rehearsal


class ManualReviewRehearsalCliTests(unittest.TestCase):
    def test_run_manual_review_rehearsal_writes_gate_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            review_path = root / "promotion_review_packet.json"
            review_path.write_text(
                json.dumps(
                    {
                        "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
                        "manual_review_gate": {"allowed": False, "reasons": ["manual_live_review_not_enabled"]},
                        "selected_candidate": {"case_id": "case_a", "promotion_status": "paper_ready"},
                    }
                ),
                encoding="utf-8",
            )
            data_quality_path = root / "data_quality_gap_audit.json"
            data_quality_path.write_text(json.dumps({"summary": {"missing_date_rows": 0}}), encoding="utf-8")
            provider_path = root / "provider_evidence_pack.json"
            provider_path.write_text(json.dumps({"summary": {"providers": 1, "ready_providers": 1, "parquet_ready": True}}), encoding="utf-8")
            paper_path = root / "paper_observation_pack.json"
            paper_path.write_text(json.dumps({"summary": {"observed_candidates": 1}}), encoding="utf-8")
            duplicate_path = root / "duplicate_canonical_registry.json"
            duplicate_path.write_text(json.dumps({"summary": {"duplicate_members": 0, "clusters": 0}}), encoding="utf-8")
            output_dir = root / "manual_review_rehearsal"

            rehearsal = run_manual_review_rehearsal(
                review_packet=review_path,
                data_quality=data_quality_path,
                provider_evidence=provider_path,
                paper_observation=paper_path,
                duplicate_registry=duplicate_path,
                output_dir=output_dir,
            )

            self.assertEqual(rehearsal["stage"], "phase_3_5_manual_review_gate_rehearsal")
            self.assertTrue((output_dir / "manual_review_rehearsal.json").exists())
            self.assertTrue((output_dir / "manual_review_rehearsal.md").exists())
            self.assertTrue((output_dir / "manual_review_requirements.csv").exists())
            payload = json.loads((output_dir / "manual_review_rehearsal.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["dry_run"]["order_placement"], "disabled")


if __name__ == "__main__":
    unittest.main()
