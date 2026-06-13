import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.run_promotion_review import run_promotion_review


class PromotionReviewCliTests(unittest.TestCase):
    def test_run_promotion_review_writes_packet_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ops_path = root / "promotion_ops.json"
            output_dir = root / "review"
            ops_path.write_text(
                json.dumps(
                    {
                        "stage": "phase_2_8_promotion_operations",
                        "generated_at": "2026-06-01T00:00:00+00:00",
                        "source_report": "data/reports/promotion_gate_cn_etf_candidate_search/promotion_report.json",
                        "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
                        "summary": {"candidates": 1, "blocked": 0, "research_only": 0, "paper_ready": 1, "manual_live_review": 0, "duplicates": 0},
                        "live_review_allowed": False,
                        "live_review_blockers": ["manual_live_review_not_enabled"],
                        "top_candidate": {
                            "rank": 1,
                            "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                            "market": "CN_ETF",
                            "factor_name": "liquidity_10",
                            "promotion_status": "paper_ready",
                            "score": 42.9,
                            "risk_profile_id": "balanced_fast_guard",
                            "paper_matched": True,
                            "paper_sharpe": 0.52,
                            "paper_max_drawdown": -0.21,
                            "test_sharpe": 0.78,
                            "test_relative_return": 0.05,
                            "test_trades": 76,
                            "blocking_reasons": [],
                            "warnings": [],
                        },
                        "candidates": [],
                        "duplicate_clusters": [],
                        "evidence": {"provider_status_present": True, "quality_report_present": True, "providers_ready": True, "missing_date_rows": 0},
                        "next_actions": [{"action": "extend_paper_observation", "reason": "paper-ready candidates need more local evidence before any API boundary"}],
                    }
                ),
                encoding="utf-8",
            )

            packet = run_promotion_review(ops_path, output_dir)

            self.assertEqual(packet["selected_candidate"]["case_id"], "CN_ETF_liquidity_10_top1_cost5_reb5")
            self.assertTrue((output_dir / "promotion_review_packet.json").exists())
            self.assertTrue((output_dir / "promotion_review_packet.md").exists())
            self.assertTrue((output_dir / "promotion_review_checklist.csv").exists())
            markdown = (output_dir / "promotion_review_packet.md").read_text(encoding="utf-8")
            self.assertIn("CN_ETF_liquidity_10_top1_cost5_reb5", markdown)
            payload = json.loads((output_dir / "promotion_review_packet.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["stage"], "phase_2_9_promotion_review_packet")

    def test_script_can_run_directly_from_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ops_path = root / "promotion_ops.json"
            output_dir = root / "review"
            ops_path.write_text(
                json.dumps(
                    {
                        "stage": "phase_2_8_promotion_operations",
                        "source_report": "promotion_report.json",
                        "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
                        "summary": {"candidates": 0, "blocked": 0, "research_only": 0, "paper_ready": 0, "manual_live_review": 0, "duplicates": 0},
                        "live_review_allowed": False,
                        "live_review_blockers": ["promotion_report_missing"],
                        "top_candidate": None,
                        "candidates": [],
                        "duplicate_clusters": [],
                        "evidence": {"providers_ready": False},
                        "next_actions": [{"action": "rerun_promotion_gate", "reason": "promotion report is missing"}],
                    }
                ),
                encoding="utf-8",
            )
            env = {**os.environ, "PYTHONPATH": "src"}

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_promotion_review.py",
                    "--promotion-ops",
                    str(ops_path),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=Path(__file__).resolve().parents[2],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((output_dir / "promotion_review_packet.json").exists())


if __name__ == "__main__":
    unittest.main()
