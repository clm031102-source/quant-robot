import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_promotion_ops import run_promotion_ops


class PromotionOpsCliTests(unittest.TestCase):
    def test_run_promotion_ops_writes_console_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            promotion_report = root / "promotion_report.json"
            provider_status = root / "provider_status.json"
            quality_report = root / "quality_report.json"
            paper_observation = root / "paper_observation_pack.json"
            output_dir = root / "ops"
            promotion_report.write_text(
                json.dumps(
                    {
                        "summary": {"candidates": 1, "blocked": 0, "research_only": 0, "paper_ready": 1, "manual_live_review": 0, "duplicates": 0},
                        "candidates": [
                            {
                                "promotion_rank": 1,
                                "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                                "market": "CN_ETF",
                                "factor_name": "liquidity_10",
                                "promotion_status": "paper_ready",
                                "score": 42.9,
                                "blocking_reasons": [],
                                "warnings": ["providers_not_ready_for_live_review"],
                                "walk_forward": {"test_sharpe": 0.78, "test_relative_return": 0.05, "test_trades": 76},
                                "paper": {"matched": True, "risk_profile_id": "balanced_fast_guard", "sharpe": 0.52, "max_drawdown": -0.21},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            provider_status.write_text(json.dumps({"providers": {"tushare": {"ready": False}}}), encoding="utf-8")
            quality_report.write_text(json.dumps({"duplicate_bars": 0, "missing_date_rows": 0, "zero_volume_rows": 0}), encoding="utf-8")
            paper_observation.write_text(json.dumps({"summary": {"observed_candidates": 1, "completed_candidates": 1}}), encoding="utf-8")

            result = run_promotion_ops(
                promotion_report,
                provider_status,
                quality_report,
                output_dir,
                paper_observation=paper_observation,
            )

            self.assertEqual(result["summary"]["paper_ready"], 1)
            self.assertTrue(result["evidence"]["paper_observation_complete"])
            self.assertFalse(any(action["action"] == "extend_paper_observation" for action in result["next_actions"]))
            self.assertTrue((output_dir / "promotion_ops.json").exists())
            self.assertTrue((output_dir / "promotion_ops_candidates.csv").exists())
            payload = json.loads((output_dir / "promotion_ops.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["top_candidate"]["case_id"], "CN_ETF_liquidity_10_top1_cost5_reb5")


if __name__ == "__main__":
    unittest.main()
