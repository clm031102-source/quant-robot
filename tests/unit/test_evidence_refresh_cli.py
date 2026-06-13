import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_evidence_refresh import run_evidence_refresh


class EvidenceRefreshCliTests(unittest.TestCase):
    def test_run_evidence_refresh_writes_plan_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            review_packet = root / "promotion_review_packet.json"
            output_dir = root / "evidence_refresh"
            review_packet.write_text(
                json.dumps(
                    {
                        "stage": "phase_2_9_promotion_review_packet",
                        "review_status": "blocked",
                        "selected_candidate": {"case_id": "CN_ETF_liquidity_10_top1_cost5_reb5", "market": "CN_ETF"},
                        "manual_review_gate": {"status": "blocked", "allowed": False, "reasons": ["providers_not_ready_for_live_review"]},
                        "checklist": [
                            {"check_id": "provider_readiness", "status": "block", "evidence": "providers_not_ready_for_live_review"},
                            {"check_id": "data_quality", "status": "pass", "evidence": "missing_date_rows=0"},
                            {"check_id": "paper_observation", "status": "pass", "evidence": "matched=True"},
                            {"check_id": "duplicate_cluster", "status": "pass", "evidence": "no duplicate cluster"},
                        ],
                        "duplicate_clusters": [],
                        "evidence": {"providers_ready": False, "missing_date_rows": 0, "duplicate_bars": 0, "zero_volume_rows": 0},
                        "next_actions": [],
                        "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
                    }
                ),
                encoding="utf-8",
            )

            plan = run_evidence_refresh(review_packet, output_dir)

            self.assertEqual(plan["stage"], "phase_3_0_evidence_refresh")
            self.assertTrue((output_dir / "evidence_refresh_plan.json").exists())
            self.assertTrue((output_dir / "evidence_refresh_plan.md").exists())
            self.assertTrue((output_dir / "evidence_refresh_actions.csv").exists())
            payload = json.loads((output_dir / "evidence_refresh_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["refresh_status"], "action_required")


if __name__ == "__main__":
    unittest.main()
